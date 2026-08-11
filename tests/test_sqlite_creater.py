import sqlite3

import pytest

from antares_bot.sqlite.creater import (
    INT,
    TEXT,
    DbDeclarer,
    NoColumnException,
    NoDbPathException,
    NoTableException,
    TableDeclarer,
)


def _declare(table_name="t", **kwargs):
    return TableDeclarer().set_table_name(table_name)


# ------------------------------------------------------------ get_creation_cmd


def test_single_primary_key_is_inlined():
    t = _declare().declare_col("id", INT, is_primary=True).declare_col("name", TEXT)
    cmd = t.get_creation_cmd()
    assert "id INT PRIMARY KEY" in cmd
    assert "PRIMARY KEY (" not in cmd


def test_composite_primary_key_is_declared_at_the_end():
    t = (
        _declare()
        .declare_col("a", INT, is_primary=True)
        .declare_col("b", INT, is_primary=True)
        .declare_col("c", TEXT)
    )
    cmd = t.get_creation_cmd()
    assert "PRIMARY KEY (a,b)" in cmd
    assert "a INT PRIMARY KEY" not in cmd


def test_column_constraints():
    t = (
        _declare()
        .declare_col("a", TEXT, is_not_null=True)
        .declare_col("b", INT, is_unique=True)
    )
    cmd = t.get_creation_cmd()
    assert "a TEXT NOT NULL" in cmd
    assert "b INT UNIQUE" in cmd


def test_text_defaults_are_quoted_and_others_are_not():
    t = _declare().declare_col("a", TEXT, default="hi").declare_col("b", INT, default=5)
    cmd = t.get_creation_cmd()
    assert "a TEXT DEFAULT 'hi'" in cmd
    assert "b INT DEFAULT 5" in cmd


def test_creation_cmd_requires_a_table_name():
    t = TableDeclarer().declare_col("a", INT)
    with pytest.raises(NoTableException):
        t.get_creation_cmd()


def test_creation_cmd_requires_columns():
    with pytest.raises(NoColumnException):
        _declare().get_creation_cmd()


@pytest.mark.parametrize(
    "build",
    [
        lambda t: t.declare_col("id", INT, is_primary=True).declare_col("n", TEXT),
        lambda t: (
            t.declare_col("a", INT, is_primary=True)
            .declare_col("b", INT, is_primary=True)
            .declare_col("c", TEXT, default="x")
        ),
        lambda t: t.declare_col("a", TEXT, is_not_null=True, is_unique=True),
    ],
)
def test_generated_sql_is_valid(build):
    cmd = build(_declare()).get_creation_cmd()
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute(cmd)  # raises if the SQL is malformed
    finally:
        conn.close()


# ---------------------------------------------------------- TableDataCreator


def test_data_creator_rejects_unknown_columns():
    creator = _declare().declare_col("a", INT).get_data_creator()
    with pytest.raises(ValueError):
        creator.set("nope", 1)
    with pytest.raises(ValueError):
        creator.set_dict({"nope": 1})


def test_data_creator_collects_values():
    creator = _declare().declare_col("a", INT).declare_col("b", TEXT).get_data_creator()
    creator.set("a", 1).set_dict({"b": "x"})
    assert creator.create() == {"a": 1, "b": "x"}


def test_data_creator_requires_not_null_columns():
    creator = _declare().declare_col("a", INT, is_not_null=True).get_data_creator()
    with pytest.raises(RuntimeError):
        creator.create()


def test_data_creator_accepts_a_not_null_column_with_a_default():
    creator = (
        _declare().declare_col("a", INT, is_not_null=True, default=3).get_data_creator()
    )
    assert creator.create() == {}


# ------------------------------------------------------------------ DbDeclarer


def _db(tmp_path, name="test.db"):
    return str(tmp_path / "sub" / name)


async def test_create_builds_the_tables(tmp_path):
    d = DbDeclarer().declare(_db(tmp_path))
    d.declare_table("users").declare_col("id", INT, is_primary=True).declare_col(
        "name", TEXT
    )
    await d.create()

    conn = sqlite3.connect(d.db_path)
    try:
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
    finally:
        conn.close()
    assert "users" in names


async def test_create_drops_an_existing_table(tmp_path):
    d = DbDeclarer().declare(_db(tmp_path))
    d.declare_table("users").declare_col("id", INT, is_primary=True)
    await d.create()

    conn = sqlite3.connect(d.db_path)
    conn.execute("INSERT INTO users (id) VALUES (1)")
    conn.commit()
    conn.close()

    await d.create()  # re-create: the row must be gone
    conn = sqlite3.connect(d.db_path)
    try:
        assert conn.execute("SELECT count(*) FROM users").fetchone()[0] == 0
    finally:
        conn.close()


async def test_create_requires_a_path():
    d = DbDeclarer()
    d.declare_table("t").declare_col("a", INT)
    with pytest.raises(NoDbPathException):
        await d.create()


async def test_create_requires_a_table(tmp_path):
    with pytest.raises(NoTableException):
        await DbDeclarer().declare(_db(tmp_path)).create()


async def test_validate_adds_a_missing_table(tmp_path):
    d = DbDeclarer().declare(_db(tmp_path))
    d.declare_table("users").declare_col("id", INT, is_primary=True)
    await d.create()

    # declare a second table and validate an existing database
    d.declare_table("extra").declare_col("k", TEXT, is_primary=True)
    await d.validate()

    conn = sqlite3.connect(d.db_path)
    try:
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
    finally:
        conn.close()
    assert {"users", "extra"} <= names


async def test_validate_keeps_existing_data(tmp_path):
    d = DbDeclarer().declare(_db(tmp_path))
    d.declare_table("users").declare_col("id", INT, is_primary=True)
    await d.create()
    conn = sqlite3.connect(d.db_path)
    conn.execute("INSERT INTO users (id) VALUES (1)")
    conn.commit()
    conn.close()

    await d.validate()

    conn = sqlite3.connect(d.db_path)
    try:
        assert conn.execute("SELECT count(*) FROM users").fetchone()[0] == 1
    finally:
        conn.close()


async def test_create_or_validate_creates_when_absent(tmp_path):
    d = DbDeclarer().declare(_db(tmp_path))
    d.declare_table("users").declare_col("id", INT, is_primary=True)
    await d.create_or_validate()
    conn = sqlite3.connect(d.db_path)
    try:
        assert conn.execute("SELECT count(*) FROM users").fetchone()[0] == 0
    finally:
        conn.close()


async def test_create_or_validate_validates_when_present(tmp_path):
    d = DbDeclarer().declare(_db(tmp_path))
    d.declare_table("users").declare_col("id", INT, is_primary=True)
    await d.create()
    conn = sqlite3.connect(d.db_path)
    conn.execute("INSERT INTO users (id) VALUES (1)")
    conn.commit()
    conn.close()

    await d.create_or_validate()  # must not drop

    conn = sqlite3.connect(d.db_path)
    try:
        assert conn.execute("SELECT count(*) FROM users").fetchone()[0] == 1
    finally:
        conn.close()
