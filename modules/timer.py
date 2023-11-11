import asyncio
from typing import TYPE_CHECKING

from basebot import TelegramBotModuleBase
from bot_framework.framework import command_callback_wrapper

if TYPE_CHECKING:
    from telegram import Update

    from bot_framework.context import RichCallbackContext


class Timer(TelegramBotModuleBase):
    def do_init(self) -> None:
        pass

    @command_callback_wrapper
    async def timer(self, update: "Update", context: "RichCallbackContext") -> bool:
        assert update.message is not None
        assert update.message.text is not None
        await asyncio.sleep(5)
        await update.message.reply_text("time up!")
        return True
