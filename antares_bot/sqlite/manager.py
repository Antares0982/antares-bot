import asyncio
from types import TracebackType
from typing import Any, Literal, Optional, cast

import aiosqlite

from antares_bot.bot_logging import get_logger
from antares_bot.sqlite.creater import TableDeclarer


SqlRowDict = dict[str, Any]
_LOGGER = get_logger(__name__)


INSERT_COMMAND_FORMAT = """INSERT INTO {table} ({columns})
VALUES
{many_values}
"""
INSERT_COMMAND_PART2_FORMAT = """
ON CONFLICT({pks}) DO UPDATE SET {upsert_args}
"""
SELECT_COMMAND_FORMAT = """SELECT {columns} FROM {table}"""
UPDATE_COMMAND_FORMAT = """UPDATE {table} SET {set}"""
DELETE_COMMAND_FORMAT = "DELETE FROM {table}"
WHERE_PART_FORMAT = """ WHERE {where}"""


class DataBasesManager:
    INST: "DataBasesManager" = None  # type: ignore

    @classmethod
    def get_inst(cls):
        if cls.INST is None:
            cls.INST = cls()
        return cls.INST

    def __init__(self) -> None:
        self._registered_databases: dict[str, Database] = {}

    async def shutdown(self):
        databases = self._registered_databases
        self._registered_databases = {}
        task = asyncio.gather(*(db.close() for db in databases.values()))
        await task
        _LOGGER.info("Closed %d databases", len(databases))

    def register_database(self, name: str, db: "Database"):
        self._registered_databases[name] = db

    def remove_database(self, name: str):
        self._registered_databases.pop(name, None)


class TableProxy(TableDeclarer):
    def __init__(self, db: "Database", table_name: str) -> None:
        super().__init__()
        self.db = db
        self.table_name = table_name
        self.primary_keys: list[str] = []

    def declare_col(self, column_name: str, column_type: str, is_primary: bool = False, is_not_null: bool = False, is_unique: bool = False, default: Any = None):
        super().declare_col(column_name, column_type, is_primary, is_not_null, is_unique, default)
        if is_primary:
            self.primary_keys.append(column_name)

    def _get_parsed_where(self, pk_data: tuple | Any):
        if isinstance(pk_data, tuple):
            if len(pk_data) != len(self.primary_keys):
                raise ValueError("Primary key length not match")
            where = {k: v for k, v in zip(self.primary_keys, pk_data)}
        else:
            where = {self.primary_keys[0]: pk_data}
        return where

    async def _aget_internal(self, select_interface, where):
        rows = await select_interface(self.table_name, where=where)
        rows_list = [dict(row) for row in rows]
        if len(rows_list) > 1:
            raise RuntimeError("More than one row found")
        found = bool(rows_list)
        return found, rows_list[0] if found else None

    async def aget(self, pk_data: tuple | Any):
        where = self._get_parsed_where(pk_data)
        return (await self._aget_internal(self.db.select, where))[1]

    async def agetitem(self, pk_data: tuple | Any):
        where = self._get_parsed_where(pk_data)
        found, value = await self._aget_internal(self.db.select, where)
        if not found:
            raise AttributeError(f"Table {self.table_name} has no item with primary key {pk_data}")
        return value

    def __getitem__(self, pk_data: tuple | Any):
        return self.agetitem(pk_data)

    async def aget_nolock(self, pk_data: tuple | Any):
        where = self._get_parsed_where(pk_data)
        _, value = await self._aget_internal(self.db.select_nolock, where)
        return value

    async def agetitem_nolock(self, pk_data: tuple | Any):
        where = self._get_parsed_where(pk_data)
        found, value = await self._aget_internal(self.db.select_nolock, where)
        if not found:
            raise AttributeError(f"Table {self.table_name} has no item with primary key {pk_data}")
        return value

    def _get_parsed_data_dicts(self, pk_data: tuple | Any, value: SqlRowDict):
        insert_value = value.copy()
        if isinstance(pk_data, tuple):
            for k, v in zip(self.primary_keys, pk_data):
                insert_value[k] = v
        else:
            insert_value[self.primary_keys[0]] = pk_data
        return insert_value

    async def _aset_internal(self, insert_interface, insert_value: SqlRowDict):
        return await insert_interface(self.table_name, insert_value)

    async def aset(self, pk_data: tuple | Any, value: SqlRowDict):
        insert_value = self._get_parsed_data_dicts(pk_data, value)
        return await self._aset_internal(self.db.insert, insert_value)

    async def aset_nolock(self, pk_data: tuple | Any, value: SqlRowDict):
        insert_value = self._get_parsed_data_dicts(pk_data, value)
        return await self._aset_internal(self.db.insert_nolock, insert_value)


class Database(object):
    def __init__(self, dbpath: str) -> None:
        self.db_path = dbpath
        self.conn: aiosqlite.Connection | None = None
        self.lock = asyncio.Lock()
        self.table_info: dict[str, TableProxy] | None = None  # table name -> [(column name, type), ...]
        self.dirty_mark = False
        self._cursor = None
        self._last_command_and_args: tuple[str, Any] | None = None

    async def connect(self) -> None:
        await self.close()
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        DataBasesManager.get_inst().register_database(self.db_path, self)
        await self.update_table_info()

    async def close(self) -> None:
        DataBasesManager.get_inst().remove_database(self.db_path)
        if self.conn is not None:
            try:
                await self.conn.close()
            except Exception:
                ...
            self.conn = None

    def get_cur_connection(self) -> aiosqlite.Connection:
        return cast(aiosqlite.Connection, self.conn)

    @property
    def cursor(self) -> aiosqlite.Cursor:
        return cast(aiosqlite.Cursor, self._cursor)

    async def update_table_info(self) -> None:
        # self.cursor maybe None here
        c = await self.get_cur_connection().cursor()
        tables_info = await (await c.execute("select name from sqlite_master where type='table';")).fetchall()
        tables_key: list[str] = [t[0] for t in tables_info]
        self.table_info = dict()
        for table_name in tables_key:
            table_info = await (await c.execute(f"PRAGMA table_info({table_name});")).fetchall()
            tb_declare = TableProxy(self, table_name)
            self.table_info[table_name] = tb_declare
            for row in table_info:
                tb_declare.declare_col(
                    row['name'],
                    row['type'],
                    is_primary=row['pk'] > 0,
                    is_not_null=row['notnull'] > 0,
                    default=row['dflt_value'],
                )

    def get_primary_key_names(self, table: str) -> list[str]:
        assert self.table_info is not None
        return self.table_info[table].primary_keys

    @staticmethod
    def _key_eq_value_format(k, v, parse_arg: list):
        parse_arg.append(v)
        return f"{k}=?"

    async def select_nolock(
        self, table: str, where: SqlRowDict | None = None, need: list[str] | None = None
    ):
        command = SELECT_COMMAND_FORMAT.format(
            table=table,
            columns=",".join(need) if need else "*"
        )
        parse_args: list = []
        if where:
            command += WHERE_PART_FORMAT.format(where=" AND ".join(
                self._key_eq_value_format(k, v, parse_args) for k, v in where.items()
            ))
        command += ";"

        _LOGGER.debug("execute command %s with args: %s", command, parse_args)
        self._last_command_and_args = (command, parse_args)

        await self.cursor.execute(command, parse_args)
        return await self.cursor.fetchall()

    async def insert_nolock(self, table: str, data_dicts: list[SqlRowDict] | SqlRowDict):
        if not isinstance(data_dicts, list):
            data_dicts = [data_dicts]
        if len(data_dicts) == 0:
            return

        # do column name check
        columns = list(data_dicts[0].keys())
        columns_set = set(columns)
        for i in range(1, len(data_dicts)):
            if set(data_dicts[i].keys()) != columns_set:
                raise ValueError("Column name not match")

        pks = self.get_primary_key_names(table)

        one_value = "(" + ",".join(["?" for _ in columns]) + ")"
        many_values = ",\n".join([one_value for _ in data_dicts])

        insert_command = INSERT_COMMAND_FORMAT.format(
            table=table,
            columns=",".join(columns),
            many_values=many_values,
        )
        if 0 < len(pks) < len(columns):
            upsert_args = ','.join([f"{col}=excluded.{col}" for col in columns if col not in pks])
            insert_command += INSERT_COMMAND_PART2_FORMAT.format(
                pks=",".join(pks),
                upsert_args=upsert_args,
            )
        insert_command += ";"

        parse_args:list[Any] = []
        for data_dict in data_dicts:
            parse_args.extend(data_dict[col] for col in columns)

        _LOGGER.debug("execute command %s with args: %s", insert_command, parse_args)
        self._last_command_and_args = (insert_command, parse_args)

        await self.cursor.execute(insert_command, parse_args)
        self.dirty_mark = True

    async def update_nolock(self, table: str, datadict: SqlRowDict, where: SqlRowDict | Literal["*"] | None = None):
        if where:
            where_data: SqlRowDict | None = None if where == "*" else where
        else:
            pks = self.get_primary_key_names(table)
            where_data = dict()
            for k in pks:
                where_data[k] = datadict.pop(k)
        if len(datadict) == 0:
            _LOGGER.debug("nothing to set, no need to update database")
            return

        parse_args: list = []
        command = UPDATE_COMMAND_FORMAT.format(
            table=table,
            set=",".join(self._key_eq_value_format(k, v, parse_args) for k, v in datadict.items()),
        )

        if where_data is not None:
            command += WHERE_PART_FORMAT.format(where=" AND ".join(
                self._key_eq_value_format(k, v, parse_args) for k, v in where_data.items()
            ))

        command += ";"

        _LOGGER.debug("parse command %s with args: %s", command, parse_args)
        self._last_command_and_args = (command, parse_args)

        await self.cursor.execute(command, parse_args)
        self.dirty_mark = True

    async def delete_nolock(self, table: str, where: SqlRowDict | Literal["*"]):
        command = DELETE_COMMAND_FORMAT.format(table=table)
        parse_args: list = []

        if where != "*":
            command += WHERE_PART_FORMAT.format(where=" AND ".join([
                self._key_eq_value_format(k, v, parse_args) for k, v in where.items()
            ]))

        command += ";"

        _LOGGER.debug("parse command %s with args: %s", command, parse_args)
        self._last_command_and_args = (command, parse_args)

        await self.cursor.execute(command, parse_args)
        self.dirty_mark = True

    async def select(
        self,
        table: str,
        where: SqlRowDict | None = None,
        need: list[str] | None = None
    ):
        async with self:
            return await self.select_nolock(table, where, need)

    async def insert(self, table: str, data_dicts: list[SqlRowDict] | SqlRowDict):
        async with self:
            await self.insert_nolock(table, data_dicts)

    async def update(self, table: str, datadict: SqlRowDict, where: SqlRowDict | Literal['*'] | None = None):
        async with self:
            await self.update_nolock(table, datadict, where)

    async def delete(self, table, where: SqlRowDict | Literal['*']):
        async with self:
            await self.delete_nolock(table, where)

    async def execute(self, cmd: list[str], need_commit: bool = True):
        """execute a list of commands."""
        async with self:
            for c in cmd:
                await self.cursor.execute(c)
            # await self.get_cur_connection().commit()
            self.dirty_mark = need_commit

    async def __aenter__(self):
        if self.conn is None:
            raise RuntimeError("Database not connected")
        await self.lock.acquire()
        self._cursor = await self.get_cur_connection().cursor()
        self._last_command_and_args = None
        return True

    async def __aexit__(self, exception_type, exception_value, exception_traceback: Optional["TracebackType"]):
        if exception_type is not None:
            if self._last_command_and_args is not None:
                last_command, last_args = self._last_command_and_args
                _LOGGER.error("Error occurred when executing command %s with args: %s", last_command, last_args)
        if self.dirty_mark:
            try:
                await self.get_cur_connection().commit()
            except Exception as e:
                from antares_bot.utils import exception_manual_handle
                await exception_manual_handle(_LOGGER, e)
            self.dirty_mark = False
        self._cursor = None
        self.lock.release()
        self._last_command_and_args = None
        return False

    def __getitem__(self, table: str) -> TableProxy:
        assert self.table_info
        return self.table_info[table]
