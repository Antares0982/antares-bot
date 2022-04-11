# 修改本文件来实现具体功能,修改example2.py实现第二个功能
from telegram import CallbackQuery
from telegram.ext import CallbackContext

from basebot import baseBot
from utils import *


class exampleBot1(baseBot):
    def __init__(self) -> None:
        if not hasattr(self, "updater"):
            baseBot.__init__(self)
        ...

    def cond(self) -> bool:
        ...

    def dosth(self):
        ...

    @commandCallbackMethod
    def command(self, update: Update, context: CallbackContext):
        self.dosth()

    # examples
    def textHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        if not self.cond():
            return handlePassed
        self.dosth()
        return handleBlocked()

    def button_dispatch1(self, query: CallbackQuery, args: List[str]) -> bool:
        ...

    def button_dispatch2(self, query: CallbackQuery, args: List[str]) -> bool:
        ...

    @buttonQueryHandleMethod
    def buttonHandler(self, *args, **kwargs):
        ...
        return {
            'callback1': ('workingmethod1', exampleBot1.button_dispatch1),
            'callback2': ('workingmethod2', exampleBot1.button_dispatch2)
        }

    def photoHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        ...
        return handlePassed

    def channelHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        ...
        return handlePassed

    def editedChannelHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        ...
        return handlePassed
