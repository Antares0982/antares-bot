from typing import TYPE_CHECKING, Any, Optional

from telegram import InlineKeyboardButton
from telegram.error import TelegramError

import bot_framework.context_manager as context_manager
from bot_framework.bot_logging import get_logger
from bot_framework.bot_method_wrapper import TelegramBotBaseWrapper
from bot_framework.error import UserPermissionException
from bot_framework.permission_check import CheckLevel, ConditionLimit, permission_check


if TYPE_CHECKING:
    from bot_framework.context import RichCallbackContext


DEBUG_LOGGER = get_logger("debug")


class TelegramBotBase(TelegramBotBaseWrapper):
    @classmethod
    def check(cls, level: CheckLevel, limit: ConditionLimit = ConditionLimit.ALL) -> None:
        if not permission_check(cls.get_context(), level, limit):
            raise UserPermissionException

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
        from bot_framework.bot_inst import get_bot_instance
        if maxTries <= 0:
            raise ValueError("无效的重试次数")

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
    def is_master(cls) -> bool:
        from bot_cfg import MASTER_ID
        return cls.get_context().chat_id == MASTER_ID or cls.get_context().user_id == MASTER_ID

    @classmethod
    def format_inline_keyboard_button(cls, text: str, callback_key_name: str, callback_arg: Any):
        return InlineKeyboardButton(text, callback_data=f"{callback_key_name}:{callback_arg}")
