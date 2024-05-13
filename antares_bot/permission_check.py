from enum import Enum
from typing import TYPE_CHECKING

from antares_bot.bot_default_cfg import BasicConfig
from antares_bot.utils import read_user_cfg


if TYPE_CHECKING:
    from antares_bot.context import RichCallbackContext


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


class PermissionState(Enum):
    PASSED = 0
    INVALID_USER = 1
    INVALID_CHAT_TYPE = 2
    IGNORE_CHANNEL = 3


def permission_check(context: "RichCallbackContext", level: CheckLevel, limit: ConditionLimit = ConditionLimit.ALL):
    if context.is_private_chat():
        if 0 == (limit.value & ConditionLimit.PRIVATE.value):
            return PermissionState.INVALID_CHAT_TYPE
    elif context.is_group_chat():
        if 0 == (limit.value & ConditionLimit.GROUP.value):
            return PermissionState.INVALID_CHAT_TYPE
    elif context.is_channel_message():
        if 0 == (limit.value & ConditionLimit.CHANNEL.value):
            return PermissionState.IGNORE_CHANNEL
    if level == CheckLevel.MASTER:
        master_id = read_user_cfg(BasicConfig, "MASTER_ID")
        is_master = context.chat_id == master_id or context.user_id == master_id
        return PermissionState.PASSED if is_master else PermissionState.INVALID_USER
    # add more checks in future
    return PermissionState.PASSED
