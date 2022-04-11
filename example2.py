from telegram import CallbackQuery
from telegram.ext import CallbackContext

from basebot import baseBot
from utils import *


class exampleBot2(baseBot):
    def __init__(self) -> None:
        if not hasattr(self, "updater"):
            baseBot.__init__(self)
        ...

    def textHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        ...
        return handlePassed

    def button_dispatch3(self, query: CallbackQuery, args: List[str]) -> bool:
        ...

    def button_dispatch4(self, query: CallbackQuery, args: List[str]) -> bool:
        ...

    @buttonQueryHandleMethod
    def buttonHandler(self, *args, **kwargs):
        ...
        return {
            'callback3': ('workingmethod3', self.button_dispatch3),
            'callback4': ('workingmethod4', self.button_dispatch4)
        }

    def photoHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        ...
        return handlePassed
