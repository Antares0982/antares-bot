# 修改本文件来实现具体功能,修改example2.py实现第二个功能
from telegram.ext import CallbackContext

from basebot import baseBot
from utils import *


class exampleBot1(baseBot):
    def __init__(self) -> None:
        if not hasattr(self, "updater"):
            baseBot.__init__(self)
        ...

    def cond() -> bool:
        ...

    def dosth():
        ...

    @commandCallbackMethod
    def command(self, update: Update, context: CallbackContext):
        self.dosth()

    # 范例
    def textHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        self.renewStatus(update)
        if not self.cond():
            return handlePassed()
        self.dosth()
        return handleBlocked()

    def buttonHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        self.renewStatus(update)
        ...
        return handlePassed()

    def photoHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        self.renewStatus(update)
        ...
        return handlePassed()
