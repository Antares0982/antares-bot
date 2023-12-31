from typing import List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatType


class ObjectDict(dict):
    """
    General json object that allows attributes 
    to be bound to and also behaves like a dict.
    """

    def __getattr__(self, attr: str):
        return self.get(attr)

    def __setattr__(self, attr: str, value):
        self[attr] = value


def get_from_id(update: Update) -> Optional[int]:
    """返回`from_user.id`"""
    if update.message is not None and update.message.from_user is not None:
        return update.message.from_user.id
    if update.callback_query is not None and update.callback_query.from_user is not None:
        return update.callback_query.from_user.id
    if update.channel_post is not None and update.channel_post.from_user is not None:
        return update.channel_post.from_user.id
    if update.edited_channel_post is not None and update.edited_channel_post.from_user is not None:
        return update.edited_channel_post.from_user.id
    return None


def get_chat_id(update: Update) -> Optional[int]:
    """返回`chat_id`"""
    if update.effective_chat is not None:
        return update.effective_chat.id
    return None


def get_msg_id(update: Update) -> Optional[int]:
    """返回message_id"""
    if update.message is not None:
        return update.message.message_id
    if update.callback_query is not None:
        return update.callback_query.message.message_id  # type: ignore
    if update.channel_post is not None:
        return update.channel_post.message_id
    if update.edited_channel_post is not None:
        return update.edited_channel_post.message_id
    return None


def get_reply_to_msg_id(update: Update) -> Optional[int]:
    if update.message is not None and update.message.reply_to_message is not None:
        return update.message.reply_to_message.message_id
    if update.callback_query is not None and update.callback_query.message.reply_to_message is not None:  # type: ignore
        return update.callback_query.message.reply_to_message.message_id  # type: ignore
    if update.channel_post is not None and update.channel_post.reply_to_message is not None:
        return update.channel_post.reply_to_message.message_id
    if update.edited_channel_post is not None and update.edited_channel_post.reply_to_message is not None:
        return update.edited_channel_post.reply_to_message.message_id
    return None


def is_private(update: Update) -> bool:
    return update.effective_chat.type == ChatType.PRIVATE  # type: ignore


def is_group(update: Update) -> bool:
    return update.effective_chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]  # type: ignore


def is_channel(update: Update) -> bool:
    return update.effective_chat.type == ChatType.CHANNEL  # type: ignore


def flatten_button(
    buttons: List[InlineKeyboardButton], numberInOneLine: int
) -> InlineKeyboardMarkup:
    btl: List[List[InlineKeyboardButton]] = []
    while len(buttons) > numberInOneLine:
        btl.append(buttons[:numberInOneLine])
        buttons = buttons[numberInOneLine:]
    if len(buttons) > 0:
        btl.append(buttons)
    return InlineKeyboardMarkup(btl)
