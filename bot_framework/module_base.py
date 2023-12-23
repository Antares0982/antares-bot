from typing import TYPE_CHECKING, Any, Iterable, List, Optional, Self, Set, Union, cast, Tuple

from bot_framework import language
from bot_framework.bot_base import TelegramBotBase
from bot_framework.framework import command_callback_wrapper


if TYPE_CHECKING:
    from telegram import CallbackQuery, InlineKeyboardMarkup, Update
    from telegram.ext import BaseHandler

    from bot_framework.framework import CallbackBase
    from bot_inst import TelegramBot


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

    def make_btn_callback(self, key: str, data: Iterable) -> Tuple[List[str], List[str]]:
        """
        return a list of callback data strings, which can be used to retrieve data later.
        Need to call `cache_cb_keys` to cache the keys after the message is sent.
        """
        raw_keys = []
        keys = []
        for dt in data:
            key_raw = self.parent.callback_manager.set_data(dt)
            raw_keys.append(key_raw)
            keys.append(f"{key}:{key_raw}")
        return raw_keys, keys

    def _get_cb_data_key(self, query: "CallbackQuery"):
        assert query.data is not None
        return query.data.split(':')[1]

    def get_btn_callback_data(self, update: "Update", pop: bool = False):
        query = update.callback_query
        assert query is not None
        k = self._get_cb_data_key(query)
        return self.parent.callback_manager.pop_data(k) if pop else self.parent.callback_manager.peek_data(k)

    @property
    def cancel(self):
        def cancel(x, y):
            self.reply(language.CANCELLED)
        return command_callback_wrapper(cancel)

    @property
    def job_queue(self):
        return self.parent.job_queue

    def _manual_handle_exception(self, e: Exception):
        pass  # TODO

    def cache_cb_keys(self, chat_id: int, msg_id: int, cb_keys: List[str]) -> None:
        self.parent.callback_key_dict[(chat_id, msg_id)] = cb_keys

    def clean_cb_keys(self, chat_id: int, msg_id: int) -> None:
        cb_keys = self.parent.callback_key_dict.pop((chat_id, msg_id), [])
        for key in cb_keys:
            self.parent.callback_manager.pop_data(key)

    async def query_remove_btn(self, query: "CallbackQuery", text: str = "", remove_message: bool = False, reply_markup: Optional["InlineKeyboardMarkup"] = None):
        assert query.message
        self.clean_cb_keys(query.message.chat_id, query.message.message_id)
        if remove_message:
            return await query.message.delete()
        #
        return await query.message.edit_text(text, reply_markup=reply_markup)