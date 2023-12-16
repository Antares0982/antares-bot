import asyncio
from typing import TYPE_CHECKING, Set

from bot_framework.framework import command_callback_wrapper
from bot_framework.module_base import TelegramBotModuleBase


if TYPE_CHECKING:
    from telegram import Update

    from bot_framework.context import RichCallbackContext
    from bot_framework.framework import CallbackBase


class Timer(TelegramBotModuleBase):
    def mark_handlers(self):
        return {self.timer}

    @command_callback_wrapper
    async def timer(self, update: "Update", context: "RichCallbackContext") -> bool:
        assert update.message is not None
        assert update.message.text is not None

        # async def _timer_callback(context2: "RichCallbackContext"):
        #     ct = self.get_context()
        #     print(id(ct))
        #     print(id(context2))
        #     await context.bot.send_message(context.chat_id, "Time up!")
        self.job_queue.run_once(self._timer_callback, 5)
        return True

    async def _timer_callback(self, context2: "RichCallbackContext"):
        ct = self.get_context()
        print(id(ct))
        print(id(context2))
        # await context2.bot.send_message(context2.chat_id, "Time up!")
        return True
