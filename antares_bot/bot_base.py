from logging import DEBUG as LOGLEVEL_DEBUG
from typing import TYPE_CHECKING, Any, Optional

from telegram import InlineKeyboardButton
from telegram.error import TelegramError

import antares_bot.context_manager as context_manager
from antares_bot import utils
from antares_bot.bot_default_cfg import BasicConfig
from antares_bot.bot_logging import get_logger, get_root_logger
from antares_bot.bot_method_wrapper import TelegramBotBaseWrapper
from antares_bot.error import IgnoreChannelUpdateException, InvalidChatTypeException, UserPermissionException
from antares_bot.permission_check import CheckLevel, ConditionLimit, PermissionState, permission_check


if TYPE_CHECKING:
    from telegram import Update

    from antares_bot.context import RichCallbackContext

DEBUG_LOGGER = get_logger("debug")


class TelegramBotBase(TelegramBotBaseWrapper):
    @classmethod
    def check(cls, level: CheckLevel, limit: ConditionLimit = ConditionLimit.ALL) -> None:
        check_result = permission_check(cls.get_context(), level, limit)
        cls._check_raise(check_result)

    @classmethod
    def _check_raise(cls, check_result: PermissionState):
        if check_result == PermissionState.PASSED:
            return
        if check_result == PermissionState.INVALID_USER:
            raise UserPermissionException
        elif check_result == PermissionState.INVALID_CHAT_TYPE:
            raise InvalidChatTypeException
        elif check_result == PermissionState.IGNORE_CHANNEL:
            raise IgnoreChannelUpdateException

    @classmethod
    def get_context(cls) -> "RichCallbackContext":
        context = cls.peek_context()
        if context is None:
            raise RuntimeError("No context found")
        return context

    @classmethod
    def peek_context(cls) -> Optional["RichCallbackContext"]:
        return context_manager.get_context()

    ##############################

    @classmethod
    async def del_msg(cls, chat_id: int, msgid: int, maxTries: int = 5) -> bool:
        from antares_bot.bot_inst import get_bot_instance
        if maxTries <= 0:
            raise ValueError("Invalid retry times")

        for i in range(maxTries):
            try:
                await get_bot_instance().bot.delete_message(chat_id=chat_id, message_id=msgid)
            except TelegramError:
                if i == maxTries - 1:
                    return False
                continue
            break

        return True

    @classmethod
    def debug_info(cls, msg, *args):
        DEBUG_LOGGER.debug(msg, *args)

    ##############################

    @classmethod
    def get_master_id(cls) -> int:
        return utils.read_user_cfg(BasicConfig, "MASTER_ID")

    @classmethod
    def is_master(cls, ct: "RichCallbackContext | None" = None) -> bool:
        # TODO: consider private channel
        master_id = cls.get_master_id()
        if ct is None:
            ct = cls.get_context()
        return ct.chat_id == master_id or ct.user_id == master_id

    @classmethod
    def format_inline_keyboard_button(cls, text: str, callback_key_name: str, callback_arg: Any):
        return InlineKeyboardButton(text, callback_data=f"{callback_key_name}:{callback_arg}")

    @classmethod
    def _is_debug_level(cls):
        root_logger = get_root_logger()
        return root_logger.level == LOGLEVEL_DEBUG

    @classmethod
    async def fetch_url(cls, url: str):
        return await utils.fetch_url(url)

    @classmethod
    def get_message_after_command(cls, update: "Update") -> str:
        assert update.message is not None
        assert update.message.text is not None
        txt = update.message.text.strip()
        pre_command = txt.split()[0]
        return txt[len(pre_command):].strip()

    @property
    def bot_id(self):
        raise NotImplementedError
