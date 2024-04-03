import time
from typing import TYPE_CHECKING

from antares_bot.framework import command_callback_wrapper
from antares_bot.module_base import TelegramBotModuleBase
from antares_bot.context_manager import callback_job_wrapper


if TYPE_CHECKING:
    from telegram import Update

    from antares_bot.context import RichCallbackContext


class Timer(TelegramBotModuleBase):
    def mark_handlers(self):
        return [self.timer]

    @command_callback_wrapper
    async def timer(self, update: "Update", context: "RichCallbackContext") -> bool:
        assert update.message is not None
        assert update.message.text is not None

        @callback_job_wrapper
        async def cb(_):
            await self.reply("Time up!")
        self.job_queue.run_once(cb, 5, name=f"{time.time()}")
        return True
