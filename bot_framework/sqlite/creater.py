import sqlite3
from typing import Any, List

from bot_framework.bot_logging import get_logger


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
        self.columns: List[ColumnDeclarer] = []
        self.pkey_count = 0

    def set_table_name(self, table_name):
        self.table_name = table_name
        return self

    def declare_col(self, column_name: str, column_type: str, is_primary: bool = False, is_not_null: bool = False, is_unique: bool = False, default: Any = None):
        if is_primary:
            self.pkey_count += 1
        self.columns.append(ColumnDeclarer(column_name, column_type, is_primary, is_not_null, is_unique, default))
        return self

    def get_execute_str(self):
        if self.table_name == "":
            raise NoTableException("Table name not declared")
        if len(self.columns) == 0:
            raise NoColumnException("No column declared: {}".format(self.table_name))
        execute_str = "CREATE TABLE {} (".format(self.table_name)
        for column in self.columns:
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
            for column in self.columns:
                if column.is_primary:
                    execute_str += column.column_name + ","
            execute_str = execute_str[:-1] + "));"
        else:
            execute_str = execute_str[:-1] + ");"
        return execute_str


class DbDeclarer(object):
    def __init__(self) -> None:
        self.db_path = ""
        self.tables: List[TableDeclarer] = []

    def declare(self, db_path: str):
        self.db_path = db_path
        return self

    def declare_table(self, table_name: str):
        t = TableDeclarer()
        self.tables.append(t.set_table_name(table_name))
        return t

    def create(self):
        if self.db_path == "":
            raise NoDbPathException("Database path not declared")
        if len(self.tables) == 0:
            raise NoTableException("No table declared: {}".format(self.db_path))
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            # drop table if exists
            for table in self.tables:
                command = "DROP TABLE IF EXISTS {}".format(table.table_name)
                _LOGGER.warn(command)
                c.execute(command)
            for table in self.tables:
                command = table.get_execute_str()
                _LOGGER.warn(command)
                c.execute(command)
            conn.commit()
            conn.close()
        except Exception as e:
            raise DbCreationException from e
