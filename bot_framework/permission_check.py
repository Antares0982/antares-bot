from enum import Enum
from typing import TYPE_CHECKING

import bot_cfg


if TYPE_CHECKING:
    from bot_framework.context import RichCallbackContext


class CheckLevel(Enum):
    MASTER = 0
    ADMIN = 1
    USER = 2
    ANY = 3


class ConditionLimit(Enum):
    GROUP = 1
    PRIVATE = 2
    CHANNEL = 4
    CALLBACK_QUERY = 8
    CHAT = GROUP | PRIVATE
    ALL = 0xf


def permission_check(context: "RichCallbackContext", level: CheckLevel, limit: ConditionLimit = ConditionLimit.ALL):
    if context.is_private_chat():
        if 0 == (limit.value & ConditionLimit.PRIVATE.value):
            return False
    elif context.is_group_chat():
        if 0 == (limit.value & ConditionLimit.GROUP.value):
            return False
    elif context.is_channel_message():
        if 0 == (limit.value & ConditionLimit.CHANNEL.value):
            return False
    if level == CheckLevel.MASTER:
        return context.chat_id == bot_cfg.MASTER_ID or context.user_id == bot_cfg.MASTER_ID
    # add more checks in future
    return True
