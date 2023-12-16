from typing import TYPE_CHECKING, Set, Union

from bot_framework.module_base import TelegramBotModuleBase
from bot_framework.framework import command_callback_wrapper

if TYPE_CHECKING:
    from telegram import Update

    from bot_framework.context import RichCallbackContext
    from bot_framework.framework import CallbackBase


class Echo(TelegramBotModuleBase):
    def mark_handlers(self):
        return {self.echo}

    @command_callback_wrapper
    async def echo(self, update: "Update", context: "RichCallbackContext") -> bool:
        assert update.message is not None
        assert update.message.text is not None
        text = update.message.text.strip()
        if text.startswith("/echo"):
            text = text[len("/echo"):].strip()
        await self.reply(text)
        return True
