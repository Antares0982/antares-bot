import os
from typing import Any, Dict

import aiosqlite

from antares_bot.bot_logging import get_logger


_LOGGER = get_logger(__name__)

INT = "INT"
TEXT = "TEXT"
REAL = "REAL"
BLOB = "BLOB"
NUMERIC = "NUMERIC"


class NoTableException(Exception):
    pass


class NoDbPathException(Exception):
    pass


class NoColumnException(Exception):
    pass


class DbCreationException(Exception):
    pass


class ColumnDeclarer(object):
    def __init__(self, column_name: str, column_type: str, is_primary: bool = False, is_not_null: bool = False, is_unique: bool = False, default: Any = None) -> None:
        self.column_name = column_name
        self.column_type = column_type
        self.is_primary = is_primary
        self.is_not_null = is_not_null
        self.is_unique = is_unique
        self.default = default


class TableDeclarer(object):
    def __init__(self) -> None:
        self.table_name = ""
        self.columns: Dict[str, ColumnDeclarer] = dict()
        self.pkey_count = 0

    def set_table_name(self, table_name):
        self.table_name = table_name
        return self

    def declare_col(self, column_name: str, column_type: str, is_primary: bool = False, is_not_null: bool = False, is_unique: bool = False, default: Any = None):
        if is_primary:
            self.pkey_count += 1
        self.columns[column_name] = ColumnDeclarer(column_name, column_type, is_primary, is_not_null, is_unique, default)
        return self

    def get_creation_cmd(self):
        """
        Returns the SQL string for creating the table based on the specified table name and columns.

        Raises:
            NoTableException: If the table name is not declared.
            NoColumnException: If no columns are declared for the table.

        Returns:
            str: The SQL string for creating the table.
        """
        if self.table_name == "":
            raise NoTableException("Table name not declared")
        if len(self.columns) == 0:
            raise NoColumnException("No column declared: {}".format(self.table_name))
        execute_str = "CREATE TABLE {} (".format(self.table_name)
        for column in self.columns.values():
            execute_str += "\n{} {} ".format(column.column_name, column.column_type)
            if column.is_primary and self.pkey_count == 1:
                execute_str += "PRIMARY KEY "
            if column.is_not_null:
                execute_str += "NOT NULL "
            if column.is_unique:
                execute_str += "UNIQUE "
            if column.default is not None:
                if column.column_type == TEXT:
                    execute_str += "DEFAULT '{}' ".format(column.default)
                else:
                    execute_str += "DEFAULT {} ".format(column.default)
            execute_str += ","
        if self.pkey_count > 1:
            execute_str = execute_str + "\nPRIMARY KEY ("
            for column in self.columns.values():
                if column.is_primary:
                    execute_str += column.column_name + ","
            execute_str = execute_str[:-1] + "));"
        else:
            execute_str = execute_str[:-1] + ");"
        return execute_str

    def get_data_creator(self):
        return TableDataCreator(self)


class TableDataCreator(object):
    def __init__(self, table: TableDeclarer):
        self.table = table
        self.data: Dict[str, Any] = dict()

    def set(self, column: str, value: Any):
        if column not in self.table.columns:
            raise ValueError("column {} not declared".format(column))
        self.data[column] = value
        return self

    def set_dict(self, data: Dict[str, Any]):
        for k in data:
            if k not in self.table.columns:
                raise ValueError("column {} not declared".format(k))
        self.data.update(data)
        return self

    def create(self):
        for col in self.table.columns.values():
            if col.column_name not in self.data:
                if col.is_not_null and col.default is None:
                    raise RuntimeError("column {} is not nullable".format(col.column_name))
        return self.data


class DbDeclarer(object):
    def __init__(self) -> None:
        self.db_path = ""
        self.tables: Dict[str, TableDeclarer] = dict()

    def declare(self, db_path: str):
        self.db_path = db_path
        return self

    def declare_table(self, table_name: str):
        t = TableDeclarer()
        self.tables[table_name] = t.set_table_name(table_name)
        return t

    async def create_or_validate(self):
        if os.path.exists(self.db_path):
            await self.validate()
        else:
            await self.create()

    async def create(self):
        if self.db_path == "":
            raise NoDbPathException("Database path not declared")
        dir_name = os.path.dirname(self.db_path)
        os.makedirs(dir_name, exist_ok=True)
        if len(self.tables) == 0:
            raise NoTableException("No table declared: {}".format(self.db_path))
        try:
            conn = await aiosqlite.connect(self.db_path)
            c = await conn.cursor()
            # drop table if exists
            for table_name in self.tables:
                command = "DROP TABLE IF EXISTS {}".format(table_name)
                _LOGGER.warning(command)
                await c.execute(command)
            for table in self.tables.values():
                command = table.get_creation_cmd()
                _LOGGER.warning(command)
                await c.execute(command)
            await conn.commit()
            await conn.close()
        except Exception as e:
            raise DbCreationException from e

    async def validate(self):
        # check if table exists
        conn = await aiosqlite.connect(self.db_path)
        c = await conn.cursor()
        for table in self.tables.values():
            command = "SELECT name FROM sqlite_master WHERE type='table' AND name='{}'".format(table.table_name)
            _LOGGER.debug(command)
            await c.execute(command)
            if not await c.fetchone():
                _LOGGER.warning("Table %s not exists", table.table_name)
                command = table.get_creation_cmd()
                _LOGGER.warning(command)
                await c.execute(command)
        await conn.commit()
        await conn.close()
