import asyncio
import os
import tempfile
from io import StringIO
from typing import TYPE_CHECKING, List, Union

import objgraph  # type: ignore

import bot_cfg
from bot_cfg import MASTER_ID
from bot_framework.framework import command_callback_wrapper
from bot_framework.module_base import TelegramBotModuleBase
from bot_framework.permission_check import CheckLevel


if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import BaseHandler

    from bot_framework.context import RichCallbackContext
    from bot_framework.framework import CallbackBase


class ObjGraph(TelegramBotModuleBase):
    def do_init(self) -> None:
        need_trace = getattr(bot_cfg, "TRACE_AT_START", False)
        if not need_trace:
            return
        s = StringIO()
        objgraph.show_most_common_types(limit=50, file=s)
        objgraph.show_growth()  # ignore return value
        ss = s.getvalue()

        async def _f(context: "RichCallbackContext"):
            await self.send_to(MASTER_ID, ss)
        self.job_queue.run_once(_f, 10)

    def mark_handlers(self) -> List[Union["CallbackBase", "BaseHandler"]]:
        return [self.memory_graph, self.backrefs, self.tracemalloc]

    @command_callback_wrapper
    async def memory_graph(self, update: "Update", context: "RichCallbackContext"):
        self.check(level=CheckLevel.MASTER)
        s1 = StringIO()
        s2 = StringIO()
        objgraph.show_most_common_types(limit=50, file=s1)
        objgraph.show_growth(limit=50, file=s2)
        await self.reply("show_most_common_types:\n" + s1.getvalue())
        await self.reply("show_growth:\n" + s2.getvalue())

    @command_callback_wrapper
    async def backrefs(self, update: "Update", context: "RichCallbackContext"):
        self.check(level=CheckLevel.MASTER)

        if not context.args:
            await self.error_info("Usage: /backrefs <ObjType>")
            return
        temp_dir = tempfile.gettempdir()
        objs = objgraph.by_type(context.args[0])
        if len(objs) == 0:
            await self.error_info("No objects found")
            return
        loop = asyncio.get_running_loop()
        loop.create_task(self.reply(f"found {len(objs)} objects in memory"))
        file_name = os.path.join(temp_dir, "backrefs.svg")
        objgraph.show_backrefs(objs, max_depth=5, filename=file_name)
        del objs
        await self.reply_document(file_name)
        os.remove(file_name)

    @command_callback_wrapper
    async def tracemalloc(self, update: "Update", context: "RichCallbackContext"):
        self.check(level=CheckLevel.MASTER)
        assert context.args is not None
        is_stop = len(context.args) > 0 and context.args[0] == "stop"
        import tracemalloc
        if is_stop:
            tracemalloc.stop()
            await self.reply("tracemalloc stopped")
            return
        if tracemalloc.is_tracing():
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            loop = asyncio.get_running_loop()
            loop.create_task(self.reply(f"There is {len(top_stats)} tracemalloc stats"))
            top_stats = top_stats[:200]
            stats_str = '\n'.join(str(stat) for stat in top_stats)
            await self.reply(stats_str)
            return
        else:
            tracemalloc.start()
            await self.reply("tracemalloc started")
            return
