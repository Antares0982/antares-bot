import asyncio
import os
import tempfile
from io import StringIO
from typing import TYPE_CHECKING, List, Union

import objgraph  # type: ignore

from antares_bot.bot_default_cfg import AntaresBotConfig
from antares_bot.framework import command_callback_wrapper
from antares_bot.module_base import TelegramBotModuleBase
from antares_bot.permission_check import CheckLevel
from antares_bot.utils import read_user_cfg


if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import BaseHandler

    from antares_bot.context import RichCallbackContext
    from antares_bot.framework import CallbackBase


class ObjGraph(TelegramBotModuleBase):
    def do_init(self) -> None:
        if not read_user_cfg(AntaresBotConfig, "OBJGRAPH_TRACE_AT_START"):
            return
        s = StringIO()
        objgraph.show_most_common_types(limit=50, file=s)
        objgraph.show_growth()  # ignore return value
        ss = s.getvalue()

        async def _f(context: "RichCallbackContext"):
            await self.send_to(self.get_master_id(), ss)
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
        """
        `/backrefs <ObjType>`: Draw a graph of the objects that reference the objects of given type.
        """
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
