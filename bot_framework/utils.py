import logging
from typing import List, Optional

import httpx
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


class ChatMessage(object):
    __slots__ = ["chat", "msgid"]

    def __init__(self, chat: int, msgid: int) -> None:
        self.chat = chat
        self.msgid = msgid

    def __hash__(self) -> int:
        return hash((self.chat, self.msgid))

    def __eq__(self, o) -> bool:
        if not isinstance(o, ChatMessage):
            return False
        try:
            return self.chat == o.chat and self.msgid == o.msgid
        except Exception:
            return False

    def __expr__(self) -> str:
        return str(self.chat) + ' ' + str(self.msgid)

    def __str__(self) -> str:
        return self.__expr__()


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


async def exception_manual_handle(logger: logging.Logger, e: Exception):
    """
    no raise
    """
    try:
        logger.debug("exception catched, manually handling it")
        from bot_framework.bot_inst import exception_handler, format_traceback
        from bot_framework.context_manager import get_context
        context = get_context()
        context.error = e
    except Exception as _e:
        try:
            logger.error("when manually handling exception, another exception raised: %s", format_traceback(_e))
        except Exception:
            pass
        return
    # exception_handler does not raise
    await exception_handler(None, context)


async def fetch_url(url: str, **kwargs):
    async with httpx.AsyncClient() as client:
        return await client.get(url, **kwargs)


def markdown_v2_escape(s: str) -> str:
    """
    Escape markdown special characters.
    Reference: https://www.markdownguide.org/basic-syntax/#characters-you-can-escape
    """
    # note that ~ < > in telegram is also special
    special_chars = ['\\', '`', '*', '_', '{', '}', '[', ']', '(', ')', '#', '+', '-', '.', '!', '|', '~', '<', '>']
    for c in special_chars:
        s = s.replace(c, "\\" + c)
    return s


def markdown_escape(s:str) ->str:
    """
    Escape markdown special characters.
    Reference: https://www.markdownguide.org/basic-syntax/#characters-you-can-escape
    """
    special_chars = ['\\', '`', '*', '_', '{', '}', '[', ']', '(', ')', '#', '+', '-', '.', '!', '|']
    for c in special_chars:
        s = s.replace(c, "\\" + c)
    return s