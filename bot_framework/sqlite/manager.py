import sqlite3
from typing import Any, Dict, List, Optional, cast

from types import TracebackType


class DatabaseManager(object):
    def __init__(self, dbpath: str) -> None:
        self.database = dbpath
        self.conn: Optional[sqlite3.Connection] = None
        # self.botinstance = botinstance
        # self.tables: List[str] = []
        # self.lock = threading.Lock()

    def connect(self) -> None:
        self.close()
        self.conn = sqlite3.connect(self.database)

    def close(self) -> None:
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                ...
            self.conn = None

    def _get_connection(self) -> sqlite3.Connection:
        return cast(sqlite3.Connection, self.conn)

    def _getPrimaryKey(self, table: str) -> str:
        c = self._get_connection().cursor()
        c.execute(f"PRAGMA table_info({table});")
        for r in c.fetchall():
            if r[-1] > 0:
                return r[1]
        return ""

    def _select(
        self, table: str, where: Optional[Dict[str, Any]] = None, need: Optional[List[str]] = None
    ) -> list:
        parseArgs: List[str] = []
        command = "SELECT "
        if need is None:
            command += "* FROM "
        else:
            command += ", ".join(need) + " FROM "

        command += table

        if where is not None:
            command += " WHERE "
            l = []
            for k, v in where.items():
                thispart = f"{k}="
                if type(v) is str:
                    thispart += "?"
                    parseArgs.append(v)
                elif v is None:
                    thispart += "NULL"
                else:
                    thispart += str(v)
                l.append(thispart)
            command += " AND ".join(l)

        command += ";"

        # self.botinstance.debuginfo(command)
        # if len(parseArgs) > 0:
        #     self.botinstance.debuginfo("parsing args: "+' '.join(parseArgs))

        c = self._get_connection().cursor()

        c.execute(command, parseArgs)

        return c.fetchall()

    def _insert(self, table: str, datadict: dict):
        c = self._get_connection().cursor()
        command = f"INSERT INTO {table}("
        command2 = f"VALUES("
        parseArgs: List[str] = []
        sep = ""
        for k, v in datadict.items():
            command += sep + str(k)
            if type(v) is str:
                command2 += f"{sep} ?"
                parseArgs.append(v)
            elif v is None:
                command2 += sep + " NULL"
            else:
                command2 += sep + " " + str(v)
            sep = ","
        command += ")"
        command2 += ");"

        command += command2

        # self.botinstance.debuginfo(command)
        # if len(parseArgs) > 0:
        #     self.botinstance.debuginfo("parsing args: "+' '.join(parseArgs))
        c.execute(command, parseArgs)
        self._get_connection().commit()

    def _update(self, table: str, datadict: dict, pkey: str):
        c = self._get_connection().cursor()

        command = f"UPDATE {table} SET "
        parseArgs: List[str] = []
        sep = ""
        setlength = 0

        for k, v in datadict.items():
            if str(k) == pkey:
                continue
            setlength += 1
            command += sep + str(k) + "="
            if type(v) is str:
                command += "?"
                parseArgs.append(v)
            elif v is None:
                command += "NULL"
            else:
                command += str(v)
            sep = ","

        if setlength == 0:
            # self.botinstance.debuginfo(
            #     "nothing to set, no need to update database")
            return

        command += f" WHERE {pkey}="
        if type(datadict[pkey]) is str:
            command += f"?;"
            parseArgs.append(datadict[pkey])
        else:
            command += str(datadict[pkey]) + ";"

        # self.botinstance.debuginfo(command)
        # if len(parseArgs) > 0:
        #     self.botinstance.debuginfo("parsing args: "+' '.join(parseArgs))

        c.execute(command, parseArgs)
        self._get_connection().commit()

    def _delete(self, table: str, where: Optional[Dict[str, Any]] = None):
        c = self._get_connection().cursor()
        cmd = f"DELETE FROM {table}"
        parseArgs: List[str] = []

        if where is not None:
            cmd += f" WHERE "
            l = []
            for k, v in where.items():
                thispart = f"{k}="
                if type(v) is str:
                    thispart += "?"
                    parseArgs.append(v)
                elif v is None:
                    thispart += "NULL"
                else:
                    thispart += str(v)
                l.append(thispart)
            cmd += " AND ".join(l)

        cmd += ";"

        # self.botinstance.debuginfo(cmd)
        # if len(parseArgs) > 0:
        #     self.botinstance.debuginfo("parsing args: "+' '.join(parseArgs))

        c.execute(cmd, parseArgs)
        self._get_connection().commit()

    def _seenThisPkey(self, table: str, pk: str, pkeyval):
        return bool(self._select(table, {pk: pkeyval}))

    def insertInto(self, table: str, datadict: dict):
        with self:
            pk = self._getPrimaryKey(table)
            upd = False
            if pk != "":
                if pk not in datadict:
                    raise ValueError("Data inserted should have primary key")
                if self._seenThisPkey(table, pk, datadict[pk]):
                    # self.botinstance.debuginfo("已经存储过该key，更新目标")
                    upd = True

            if upd:
                self._update(table, datadict, pk)
            else:
                self._insert(table, datadict)

    def insertMany(self, table: str, manydata: List[dict], no_pkey_check: bool = False):
        with self:
            pk = self._getPrimaryKey(table)
            for data in manydata:
                upd = False
                if not no_pkey_check and pk != "":
                    if pk not in data:
                        raise ValueError("插入表的数据必须要有主键")
                    if self._seenThisPkey(table, pk, data[pk]):
                        upd = True
                if upd:
                    self._update(table, data, pk)
                else:
                    self._insert(table, data)

    def select(
        self,
        table: str,
        where: Optional[Dict[str, Any]] = None,
        need: Optional[List[str]] = None,
    ) -> list:
        with self:
            ans = self._select(table, where, need)
            return ans

    def execute(self, cmd: List[str]):
        """execute a list of commands."""
        with self:
            for c in cmd:
                self._get_connection().cursor().execute(c)
            self._get_connection().commit()

    def delete(self, table, where: Optional[Dict[str, Any]] = None):
        with self:
            self._delete(table, where)

    def clean(self, table: str):
        with self:
            self._delete(table)

    def __enter__(self):
        # self.lock.acquire()
        self.connect()
        return True

    def __exit__(self, exception_type, exception_value, exception_traceback: Optional["TracebackType"]):
        # if exception_type is not None:
        # try:
        #     tb = '\n'.join(traceback.format_tb(exception_traceback))
        #     self.botinstance.reply(
        #         MYID,
        #         f"数据库操作出错，错误信息：{exception_type} {exception_value}\ntraceback:\n{tb}"
        #     )
        # except Exception:
        #     ...
        self.close()
        # self.lock.release()
        if exception_type is not None:
            raise exception_value
        return True
