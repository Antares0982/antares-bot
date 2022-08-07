import traceback

from telegram import Update
from telegram.error import NetworkError, TimedOut
from telegram.ext import CallbackContext
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot_framework.botbase import BotBase


class BotErrorHandle(object):
    def errorHandler(self: "BotBase", update: object, context: CallbackContext):
        err = context.error
        if err.__class__ in [NetworkError, OSError, TimedOut]:
            raise err

        self.reply(
            chat_id=self.cfg.admin_id,
            text=f"哎呀，出现了未知的错误呢……\n{err.__class__}\n\
                {err}\ntraceback:{traceback.format_exc()}",
        )

    def unknowncommand(self: "BotBase", update: Update, context: CallbackContext):
        self = self.renewStatus(update)
        if not self.isfromme(update):
            self.reply("没有这个指令")
        else:
            self.reply("似乎没有这个指令呢……")
