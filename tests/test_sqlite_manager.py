import sqlite3

import pytest

from antares_bot.sqlite.manager import DataBasesManager, Database, TableProxy


SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL DEFAULT 'anon',
    age INTEGER
);
CREATE TABLE pairs (
    a INTEGER,
    b INTEGER,
    payload TEXT,
    PRIMARY KEY (a, b)
);
CREATE TABLE nokey (
    x INTEGER
);
"""


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.db"
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    return str(path)


@pytest.fixture
async def db(db_path):
    DataBasesManager.INST = None
    database = Database(db_path)
    await database.connect()
    yield database
    await database.close()
    DataBasesManager.INST = None


def _rows(db_path, sql):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


# ------------------------------------------------------------- connect/close


async def test_connect_registers_with_the_manager(db, db_path):
    assert DataBasesManager.get_inst()._registered_databases[db_path] is db


async def test_connect_parses_the_schema(db):
    assert db.table_info is not None
    assert set(db.table_info) == {"users", "pairs", "nokey"}
    users = db["users"]
    assert isinstance(users, TableProxy)
    assert users.primary_keys == ["id"]
    assert set(users.columns) == {"id", "name", "age"}
    assert users.columns["name"].is_not_null is True
    assert users.columns["name"].default == "'anon'"
    assert db["pairs"].primary_keys == ["a", "b"]
    assert db["nokey"].primary_keys == []


async def test_get_primary_key_names(db):
    assert db.get_primary_key_names("pairs") == ["a", "b"]


async def test_close_unregisters_and_is_idempotent(db, db_path):
    await db.close()
    assert db_path not in DataBasesManager.get_inst()._registered_databases
    await db.close()  # must not raise
    assert db.conn is None


async def test_manager_shutdown_closes_everything(db, db_path):
    manager = DataBasesManager.get_inst()
    await manager.shutdown()
    assert manager._registered_databases == {}
    assert db.conn is None


async def test_operations_require_a_connection(db_path):
    database = Database(db_path)
    with pytest.raises(RuntimeError):
        await database.select("users")


# -------------------------------------------------------------------- insert


async def test_insert_a_single_row(db, db_path):
    await db.insert("users", {"id": 1, "name": "a", "age": 30})
    assert _rows(db_path, "SELECT id, name, age FROM users") == [(1, "a", 30)]


async def test_insert_many_rows(db, db_path):
    await db.insert(
        "users",
        [{"id": 1, "name": "a", "age": 1}, {"id": 2, "name": "b", "age": 2}],
    )
    assert len(_rows(db_path, "SELECT * FROM users")) == 2


async def test_insert_rejects_mismatched_columns(db):
    with pytest.raises(ValueError):
        await db.insert("users", [{"id": 1, "name": "a"}, {"id": 2, "age": 3}])


async def test_insert_of_nothing_is_a_noop(db, db_path):
    await db.insert("users", [])
    assert _rows(db_path, "SELECT * FROM users") == []


async def test_insert_upserts_on_a_primary_key_conflict(db, db_path):
    await db.insert("users", {"id": 1, "name": "a", "age": 1})
    await db.insert("users", {"id": 1, "name": "b", "age": 2})
    assert _rows(db_path, "SELECT id, name, age FROM users") == [(1, "b", 2)]


async def test_insert_upserts_on_a_composite_key(db, db_path):
    await db.insert("pairs", {"a": 1, "b": 2, "payload": "x"})
    await db.insert("pairs", {"a": 1, "b": 2, "payload": "y"})
    assert _rows(db_path, "SELECT payload FROM pairs") == [("y",)]


async def test_insert_without_a_primary_key_appends(db, db_path):
    await db.insert("nokey", {"x": 1})
    await db.insert("nokey", {"x": 1})
    assert len(_rows(db_path, "SELECT * FROM nokey")) == 2


async def test_insert_only_primary_key_columns_does_not_upsert(db, db_path):
    """With no non-key column there is nothing to SET, so no ON CONFLICT clause."""
    await db.insert("pairs", {"a": 1, "b": 2})
    with pytest.raises(Exception):
        await db.insert("pairs", {"a": 1, "b": 2})


# -------------------------------------------------------------------- select


async def test_select_everything(db):
    await db.insert("users", {"id": 1, "name": "a", "age": 1})
    rows = await db.select("users")
    assert [dict(r) for r in rows] == [{"id": 1, "name": "a", "age": 1}]


async def test_select_with_a_where_clause(db):
    await db.insert(
        "users", [{"id": 1, "name": "a", "age": 1}, {"id": 2, "name": "b", "age": 2}]
    )
    rows = await db.select("users", where={"name": "b"})
    assert [dict(r)["id"] for r in rows] == [2]


async def test_select_with_specific_columns(db):
    await db.insert("users", {"id": 1, "name": "a", "age": 1})
    rows = await db.select("users", need=["name"])
    assert dict(rows[0]) == {"name": "a"}


async def test_select_is_parameterised(db):
    """A quote in the value must not break out of the statement."""
    await db.insert("users", {"id": 1, "name": "o'brien", "age": 1})
    rows = await db.select("users", where={"name": "o'brien"})
    assert len(rows) == 1


# -------------------------------------------------------------------- update


async def test_update_derives_the_where_clause_from_the_primary_key(db, db_path):
    await db.insert("users", {"id": 1, "name": "a", "age": 1})
    await db.insert("users", {"id": 2, "name": "b", "age": 2})
    await db.update("users", {"id": 1, "name": "z"})
    assert _rows(db_path, "SELECT id, name FROM users ORDER BY id") == [
        (1, "z"),
        (2, "b"),
    ]


async def test_update_everything_with_a_star(db, db_path):
    await db.insert(
        "users", [{"id": 1, "name": "a", "age": 1}, {"id": 2, "name": "b", "age": 2}]
    )
    await db.update("users", {"name": "z"}, where="*")
    assert _rows(db_path, "SELECT name FROM users") == [("z",), ("z",)]


async def test_update_with_an_explicit_where(db, db_path):
    await db.insert(
        "users", [{"id": 1, "name": "a", "age": 5}, {"id": 2, "name": "b", "age": 5}]
    )
    await db.update("users", {"name": "z"}, where={"id": 2})
    assert _rows(db_path, "SELECT id, name FROM users ORDER BY id") == [
        (1, "a"),
        (2, "z"),
    ]


async def test_update_with_nothing_to_set_is_a_noop(db, db_path):
    await db.insert("users", {"id": 1, "name": "a", "age": 1})
    await db.update("users", {"id": 1})
    assert _rows(db_path, "SELECT name FROM users") == [("a",)]


# -------------------------------------------------------------------- delete


async def test_delete_with_a_where_clause(db, db_path):
    await db.insert(
        "users", [{"id": 1, "name": "a", "age": 1}, {"id": 2, "name": "b", "age": 2}]
    )
    await db.delete("users", {"id": 1})
    assert _rows(db_path, "SELECT id FROM users") == [(2,)]


async def test_delete_everything(db, db_path):
    await db.insert("users", {"id": 1, "name": "a", "age": 1})
    await db.delete("users", "*")
    assert _rows(db_path, "SELECT id FROM users") == []


# ------------------------------------------------------------------- execute


async def test_execute_runs_raw_commands(db, db_path):
    await db.execute(["INSERT INTO users (id, name) VALUES (9, 'raw')"])
    assert _rows(db_path, "SELECT id FROM users") == [(9,)]


# ------------------------------------------------------- lock / transaction


async def test_the_lock_is_released_after_an_error(db):
    with pytest.raises(Exception):
        async with db:
            await db.cursor.execute("SELECT * FROM no_such_table")
    assert not db.lock.locked()
    # the database is still usable
    await db.insert("users", {"id": 1, "name": "a", "age": 1})


async def test_the_last_command_is_recorded_for_diagnostics(db, caplog):
    with caplog.at_level("ERROR"):
        with pytest.raises(Exception):
            async with db:
                await db.select_nolock("no_such_table")
    assert "no_such_table" in caplog.text


async def test_dirty_mark_is_reset_after_a_commit(db):
    await db.insert("users", {"id": 1, "name": "a", "age": 1})
    assert db.dirty_mark is False


async def test_reads_do_not_mark_the_database_dirty(db):
    await db.select("users")
    assert db.dirty_mark is False


# ---------------------------------------------------------------- TableProxy


async def test_proxy_get_and_set_with_a_single_key(db):
    users = db["users"]
    await users.aset(1, {"name": "a", "age": 30})
    assert await users.aget(1) == {"id": 1, "name": "a", "age": 30}


async def test_proxy_get_missing_returns_none(db):
    assert await db["users"].aget(99) is None


async def test_proxy_getitem_missing_raises(db):
    with pytest.raises(AttributeError):
        await db["users"].agetitem(99)


async def test_proxy_getitem_returns_the_row(db):
    users = db["users"]
    await users.aset(1, {"name": "a", "age": 30})
    assert (await users[1])["name"] == "a"


async def test_proxy_with_a_composite_key(db):
    pairs = db["pairs"]
    await pairs.aset((1, 2), {"payload": "x"})
    assert await pairs.aget((1, 2)) == {"a": 1, "b": 2, "payload": "x"}


async def test_proxy_rejects_a_wrong_key_length(db):
    with pytest.raises(ValueError):
        await db["pairs"].aget((1,))


async def test_proxy_nolock_variants(db):
    users = db["users"]
    async with db:
        await users.aset_nolock(1, {"name": "a", "age": 1})
        assert (await users.aget_nolock(1))["name"] == "a"
        with pytest.raises(AttributeError):
            await users.agetitem_nolock(99)
        assert (await users.agetitem_nolock(1))["name"] == "a"


async def test_proxy_raises_when_more_than_one_row_matches(db):
    await db.insert("nokey", [{"x": 1}, {"x": 1}])
    proxy = db["nokey"]
    proxy.primary_keys = ["x"]  # pretend x is the key
    with pytest.raises(RuntimeError):
        await proxy.aget(1)
