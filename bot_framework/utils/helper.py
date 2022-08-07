from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from typing import List

__all__ = [
    "getfromid",
    "getchatid",
    "getmsgid",
    "isprivate",
    "isgroup",
    "ischannel",
    "flattenButton",
]


def getfromid(update: Update) -> int:
    """返回`from_user.id`"""
    return update.message.from_user.id


def getchatid(update: Update) -> int:
    """返回`chat_id`"""
    return update.effective_chat.id


def getmsgid(update: Update) -> int:
    """返回message_id"""
    if update.message is not None:
        return update.message.message_id
    if update.channel_post is not None:
        return update.channel_post.message_id
    if update.edited_channel_post is not None:
        return update.edited_channel_post.message_id
    raise ValueError("无法从update获取msgid")


def isprivate(update: Update) -> bool:
    return update.effective_chat.type == "private"


def isgroup(update: Update) -> bool:
    return update.effective_chat.type.find("group") != -1


def ischannel(update: Update) -> bool:
    return update.effective_chat.type == "channel"


def flattenButton(
    buttons: List[InlineKeyboardButton], numberInOneLine: int
) -> InlineKeyboardMarkup:
    btl: List[List[InlineKeyboardButton]] = []
    while len(buttons) > numberInOneLine:
        btl.append(buttons[:numberInOneLine])
        buttons = buttons[numberInOneLine:]
    if len(buttons) > 0:
        btl.append(buttons)
    return InlineKeyboardMarkup(btl)
