from typing import TYPE_CHECKING

from basebot import TelegramBotModuleBase
from bot_framework.framework import command_callback_wrapper

if TYPE_CHECKING:
    from telegram import Update

    from bot_framework.context import RichCallbackContext


class Echo(TelegramBotModuleBase):
    def do_init(self) -> None:
        pass

    @command_callback_wrapper
    async def echo(self, update: "Update", context: "RichCallbackContext") -> bool:
        assert update.message is not None
        assert update.message.text is not None
        text = update.message.text.strip()
        if text.startswith("/echo"):
            text = text[len("/echo"):].strip()
        await update.message.reply_text(text)
        return True
