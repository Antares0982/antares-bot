from typing import TYPE_CHECKING, Any, Iterable, List, Optional, Self, Set, Tuple, Union, cast

from bot_framework import language
from bot_framework.bot_base import TelegramBotBase
from bot_framework.error import InvalidQueryException
from bot_framework.framework import command_callback_wrapper
from bot_framework.patching.conversation_handler_ex import ConversationHandlerEx


if TYPE_CHECKING:
    from telegram import CallbackQuery, InlineKeyboardMarkup, Message
    from telegram.ext import BaseHandler

    from bot_framework.bot_inst import TelegramBot
    from bot_framework.callback_manager import PersistKeyboards
    from bot_framework.context import RichCallbackContext
    from bot_framework.framework import CallbackBase


class TelegramBotModuleBase(TelegramBotBase):
    if TYPE_CHECKING:
        INST: Any

    @classmethod
    def get_inst(cls) -> Self:
        return cast(Self, cls.INST)

    def __init__(self, parent: "TelegramBot") -> None:
        self.parent = parent
        self._register_inst()
        self._handlers: Optional[List[Union["CallbackBase", "BaseHandler"]]] = None

    def do_init(self) -> None:
        ...

    async def do_stop(self) -> None:
        ...

    def _register_inst(self):
        self.__class__.INST = self

    def collect_handlers(self):
        if self._handlers is None:
            self._handlers = self.mark_handlers()
        return self._handlers

    def mark_handlers(self) -> List[Union["CallbackBase", "BaseHandler"]]:
        """Override to mark all handlers that will be collected."""
        return []

    # -------------------------helper functions-------------------------
    # -------------------------DO NOT OVERRIDE--------------------------
    def make_btn_callback(self, key: str, data: Iterable) -> Tuple[List[str], List[str]]:
        """
        return a list of callback data strings, which can be used to retrieve data later.
        Need to call `cache_cb_keys_by_{}` to cache the keys after the message is sent.

        Return: cb_keys, cb_datas.
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

    def get_btn_callback_data(self, query: "CallbackQuery", pop: bool = False, check_valid=False):
        k = self._get_cb_data_key(query)
        ret = self.parent.callback_manager.pop_data(k) if pop else self.parent.callback_manager.peek_data(k)
        if ret is None and check_valid:
            self.on_invalid_query(query)
            raise InvalidQueryException
        return ret

    @property
    def cancel(self):
        async def cancel(x, y):
            await self.reply(language.CANCELLED)
            return ConversationHandlerEx.END
        return command_callback_wrapper(cancel)

    @property
    def job_queue(self):
        return self.parent.job_queue

    def _manual_handle_exception(self, e: Exception):
        pass  # TODO

    def cache_cb_keys_by_id(self, chat_id: int, msg_id: int, cb_keys: List[str]) -> None:
        self.parent.callback_key_dict[(chat_id, msg_id)] = cb_keys

    def cache_cb_keys_by_message(self, message: "Message", cb_keys: List[str]) -> None:
        self.cache_cb_keys_by_id(message.chat_id, message.message_id, cb_keys)

    def clean_cb_keys_by_id(self, chat_id: int, msg_id: int) -> None:
        cb_keys = self.parent.callback_key_dict.pop((chat_id, msg_id), [])
        for key in cb_keys:
            self.parent.callback_manager.pop_data(key)

    def clean_cb_keys(self, context: "RichCallbackContext") -> None:
        self.clean_cb_keys_by_id(context.chat_id, context.message_id)

    def clean_cb_keys_by_message(self, message: "Message") -> None:
        self.clean_cb_keys_by_id(message.chat_id, message.message_id)

    async def query_remove_btn(self, query: "CallbackQuery", text: str = "", remove_message: bool = False, reply_markup: Optional["InlineKeyboardMarkup"] = None):
        assert query.message
        self.clean_cb_keys_by_message(query.message)
        if remove_message:
            return await query.message.delete()
        #
        return await query.message.edit_text(text, reply_markup=reply_markup)

    async def on_invalid_query(self, query):
        """
        Call when the data in callback manager is removed.
        """
        await self.query_remove_btn(query, text="这个按钮无效了呢……", remove_message=False)

    def query_at_btn_index(self, query: "CallbackQuery") -> int:
        """
        Call when the query uses a keyboard.
        """
        _, keyboard = self.get_btn_callback_data(query)
        keyboard = cast("PersistKeyboards", keyboard)
        return keyboard.idx(self._get_cb_data_key(query))
    # -----------------------helper functions end-----------------------
