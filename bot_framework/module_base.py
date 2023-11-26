from typing import TYPE_CHECKING, Set, Union

from bot_framework.bot_base import TelegramBotBase
from bot_framework.framework import command_callback_wrapper
from bot_framework import language
if TYPE_CHECKING:
    from telegram.ext import BaseHandler

    from bot_framework.framework import CallbackBase
    from bot_inst import TelegramBot


class TelegramBotModuleBase(TelegramBotBase):
    if TYPE_CHECKING:
        HANDLERS: Set[Union["CallbackBase", "BaseHandler"]] = set()

    def __init__(self, parent: "TelegramBot") -> None:
        self.parent = parent

    def do_init(self) -> None:
        ...

    def collect_handlers(self) -> None:
        cls = self.__class__
        handlers = getattr(cls, "HANDLERS", None)
        if handlers is not None:
            return
        cls.HANDLERS = self.mark_handlers()

    def mark_handlers(self) -> Set[Union["CallbackBase", "BaseHandler"]]:
        """Override to mark all handlers that will be collected."""
        return set()

    # @classmethod
    # def register_new_handler(cls, command):
    #     if cls is TelegramBotModuleBase:
    #         raise RuntimeError("cannot register handler to base class")
    #     if not hasattr(cls, "HANDLERS"):
    #         cls.HANDLERS = set()
    #     cls.HANDLERS.add(command)

    @property
    def cancel(self):
            
        def cancel(x, y):
            self.reply(language.CANCELLED)
        return command_callback_wrapper(cancel)
