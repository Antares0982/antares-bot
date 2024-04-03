import asyncio
from types import TracebackType
from typing import Any, Dict, List, Optional, cast

import aiosqlite

from antares_bot.bot_logging import get_logger


_LOGGER = get_logger(__name__)


class DatabaseManager(object):
    def __init__(self, dbpath: str) -> None:
        self.database = dbpath
        self.conn: Optional[aiosqlite.Connection] = None
        self.lock = asyncio.Lock()

    async def connect(self) -> None:
        await self.close()
        self.conn = await aiosqlite.connect(self.database)

    async def close(self) -> None:
        if self.conn is not None:
            try:
                await self.conn.close()
            except Exception:
                ...
            self.conn = None

    def get_cur_connection(self) -> aiosqlite.Connection:
        return cast(aiosqlite.Connection, self.conn)

    async def get_primary_key(self, table: str) -> str:
        c = await self.get_cur_connection().cursor()
        await c.execute(f"PRAGMA table_info({table});")
        for r in await c.fetchall():
            if r[-1] > 0:
                return r[1]
        return ""

    async def select_nolock(
        self, table: str, where: Optional[Dict[str, Any]] = None, need: Optional[List[str]] = None
    ):
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

        _LOGGER.debug("parse command %s with args: %s", command, parseArgs)

        c = await self.get_cur_connection().cursor()

        await c.execute(command, parseArgs)

        return await c.fetchall()

    async def insert_nolock(self, table: str, datadict: dict):
        c = await self.get_cur_connection().cursor()
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

        _LOGGER.debug("parse command %s with args: %s", command, parseArgs)

        await c.execute(command, parseArgs)
        await self.get_cur_connection().commit()

    async def update_nolock(self, table: str, datadict: dict, pkey: str):
        c = await self.get_cur_connection().cursor()

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
            _LOGGER.debug("nothing to set, no need to update database")
            return

        command += f" WHERE {pkey}="
        if type(datadict[pkey]) is str:
            command += f"?;"
            parseArgs.append(datadict[pkey])
        else:
            command += str(datadict[pkey]) + ";"

        _LOGGER.debug("parse command %s with args: %s", command, parseArgs)

        await c.execute(command, parseArgs)
        await self.get_cur_connection().commit()

    async def delete_nolock(self, table: str, where: Optional[Dict[str, Any]] = None):
        c = await self.get_cur_connection().cursor()
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

        _LOGGER.debug("parse command %s with args: %s", cmd, parseArgs)

        await c.execute(cmd, parseArgs)
        await self.get_cur_connection().commit()

    async def has_seen(self, table: str, pk: str, pkeyval):
        return bool(await self.select_nolock(table, {pk: pkeyval}))

    async def insert_into(self, table: str, datadict: dict):
        async with self:
            pk = await self.get_primary_key(table)
            upd = False
            if pk != "":
                if pk not in datadict:
                    raise ValueError("Data inserted should have primary key")
                if await self.has_seen(table, pk, datadict[pk]):
                    _LOGGER.debug("already seen this primary key: %s, update target", str(datadict[pk]))
                    upd = True

            if upd:
                await self.update_nolock(table, datadict, pk)
            else:
                await self.insert_nolock(table, datadict)

    async def insert_many(self, table: str, manydata: List[dict], no_pkey_check: bool = False):
        async with self:
            pk = await self.get_primary_key(table)
            for data in manydata:
                upd = False
                if not no_pkey_check and pk != "":
                    if pk not in data:
                        raise ValueError("There must be primary key in data")
                    if await self.has_seen(table, pk, data[pk]):
                        upd = True
                if upd:
                    await self.update_nolock(table, data, pk)
                else:
                    await self.insert_nolock(table, data)

    async def select(
        self,
        table: str,
        where: Optional[Dict[str, Any]] = None,
        need: Optional[List[str]] = None,
    ):
        async with self:
            ans = await self.select_nolock(table, where, need)
            return ans

    async def execute(self, cmd: List[str]):
        """execute a list of commands."""
        async with self:
            for c in cmd:
                await (await self.get_cur_connection().cursor()).execute(c)
            await self.get_cur_connection().commit()

    async def delete(self, table, where: Optional[Dict[str, Any]] = None):
        async with self:
            await self.delete_nolock(table, where)

    async def clean(self, table: str):
        async with self:
            await self.delete_nolock(table)

    async def __aenter__(self):
        await self.lock.acquire()
        await self.connect()
        return True

    async def __aexit__(self, exception_type, exception_value, exception_traceback: Optional["TracebackType"]):
        if exception_type is not None:
            try:
                import traceback
                tb = '\n'.join(traceback.format_tb(exception_traceback))
                _LOGGER.error(f"Error when operating database. {exception_type} {exception_value}\ntraceback:\n{tb}")
            except Exception:
                ...
        await self.close()
        self.lock.release()
        if exception_type is not None:
            raise exception_type from exception_value
        return True
