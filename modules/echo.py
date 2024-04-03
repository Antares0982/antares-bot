from typing import TYPE_CHECKING

from antares_bot.module_base import TelegramBotModuleBase
from antares_bot.framework import command_callback_wrapper

if TYPE_CHECKING:
    from telegram import Update

    from antares_bot.context import RichCallbackContext


class Echo(TelegramBotModuleBase):
    def mark_handlers(self):
        return [self.echo]

    @command_callback_wrapper
    async def echo(self, update: "Update", context: "RichCallbackContext") -> bool:
        assert update.message is not None
        assert update.message.text is not None
        text = update.message.text.strip()
        if text.startswith("/echo"):
            text = text[len("/echo"):].strip()
        if text:
            await self.reply(text)
        return True
