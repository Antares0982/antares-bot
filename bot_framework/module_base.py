from typing import TYPE_CHECKING, Set, Union, cast, List, Iterable, Self, Any

from bot_framework import language
from bot_framework.bot_base import TelegramBotBase
from bot_framework.framework import command_callback_wrapper


if TYPE_CHECKING:
    from telegram.ext import BaseHandler

    from bot_framework.framework import CallbackBase
    from bot_inst import TelegramBot
    from telegram import Update, CallbackQuery


class TelegramBotModuleBase(TelegramBotBase):
    if TYPE_CHECKING:
        HANDLERS: Set[Union["CallbackBase", "BaseHandler"]]
        INST: Any

    def __init__(self, parent: "TelegramBot") -> None:
        self.parent = parent
        self._register_inst()

    def do_init(self) -> None:
        ...

    @classmethod
    def get_inst(cls) -> Self:
        return cast(Self, cls.INST)

    def _register_inst(self):
        self.__class__.INST = self

    def collect_handlers(self) -> None:
        cls = self.__class__
        handlers = getattr(cls, "HANDLERS", None)
        if handlers is not None:
            return
        cls.HANDLERS = self.mark_handlers()

    def mark_handlers(self) -> Set[Union["CallbackBase", "BaseHandler"]]:
        """Override to mark all handlers that will be collected."""
        return set()

    def make_btn_callback(self, key: str, data: Iterable) -> List[str]:
        return [f"{key}:{self.parent.callback_manager.set_data(dt)}" for dt in data]

    def _get_cb_data_key(self, query: "CallbackQuery"):
        assert query.data is not None
        return query.data.split(':')[1]

    def get_btn_callback_data(self, update: "Update"):
        query = update.callback_query
        assert query is not None
        return self.parent.callback_manager.get_data(self._get_cb_data_key(query))

    @property
    def cancel(self):
        def cancel(x, y):
            self.reply(language.CANCELLED)
        return command_callback_wrapper(cancel)

    def _manual_handle_exception(self, e:Exception):
        pass  # TODO
