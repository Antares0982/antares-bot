from telegram.ext import CallbackContext

from basebot import baseBot
from utils import *


class exampleBot2(baseBot):
    def __init__(self) -> None:
        if not hasattr(self, "updater"):
            baseBot.__init__(self)
        ...

    def textHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        self.renewStatus(update)
        ...
        return handlePassed()

    def buttonHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        self.renewStatus(update)
        ...
        return handlePassed()

    def photoHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        self.renewStatus(update)
        ...
        return handlePassed()
