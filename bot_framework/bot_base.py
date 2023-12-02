import asyncio
from typing import TYPE_CHECKING, Any, AsyncGenerator, Awaitable, Callable, List, TypeVar

from telegram.error import BadRequest, ChatMigrated, Forbidden, InvalidToken, RetryAfter, TelegramError

import context_manager
from text_splitter import longtext_split


if TYPE_CHECKING:
    from telegram import Message

    from bot_framework.context import RichCallbackContext


_T = TypeVar("_T")


class TelegramBotBase(object):
    RETRY_TIMES = 3
    RETRY_SLEEP_TIME = 1.

    @classmethod
    def get_context(cls) -> "RichCallbackContext":
        context = context_manager.get_context()
        if context is None:
            raise RuntimeError("No context found")
        return context

    @staticmethod
    async def _get_last(gen: AsyncGenerator[_T, Any]) -> _T:
        last = None
        async for m in gen:
            last = m
        assert last is not None
        return last
    ##############################

    @classmethod
    async def success_info(cls, text: str, **kwargs):
        await cls.reply(text, **kwargs)
        return True

    @classmethod
    async def error_info(cls, text: str, **kwargs):
        await cls.reply(text, **kwargs)
        return False
    ##############################

    @classmethod
    async def reply_to(cls, message: "Message", text: str, **kwargs) -> int:
        return (await cls._get_last(cls._reply_to(message, text, **kwargs))).id

    @classmethod
    async def reply_to_v2(cls, message: "Message", text: str, **kwargs) -> List[int]:
        return [m.id async for m in cls._reply_to(message, text, **kwargs)]

    @classmethod
    async def reply_to_v3(cls, message: "Message", text: str, **kwargs) -> "Message":
        return await cls._get_last(cls._reply_to(message, text, **kwargs))

    @classmethod
    async def reply_to_v4(cls, message: "Message", text: str, **kwargs) -> List["Message"]:
        return [m async for m in cls._reply_to(message, text, **kwargs)]

    @classmethod
    async def _reply_to(cls, message: "Message", text: str, **kwargs):
        texts = longtext_split(text)
        if 'reply_to_message_id' not in kwargs:
            kwargs['reply_to_message_id'] = message.id
        async for m in cls._sequence_send(message.reply_text, texts, **kwargs):
            yield m
    ##############################

    @classmethod
    async def reply(cls, text: str, **kwargs):
        return (await cls._get_last(cls._reply(text, **kwargs))).id

    @classmethod
    async def reply_v2(cls, text: str, **kwargs):
        return [m.id async for m in cls._reply(text, **kwargs)]

    @classmethod
    async def reply_v3(cls, text: str, **kwargs):
        return await cls._get_last(cls._reply(text, **kwargs))

    @classmethod
    async def reply_v4(cls, text: str, **kwargs):
        return [m async for m in cls._reply(text, **kwargs)]

    @classmethod
    async def _reply(cls, text: str, **kwargs):
        context = cls.get_context()
        chat_id: int = kwargs.get('chat_id', context.chat_id)
        kwargs.setdefault('chat_id', chat_id)
        if chat_id == context.chat_id and context.message_id is not None and 'reply_to_message_id' not in kwargs:
            kwargs['reply_to_message_id'] = context.message_id
        texts = longtext_split(text)
        async for m in cls._sequence_send(context.bot.send_message, texts, **kwargs):
            yield m
    ##############################

    @classmethod
    async def send_to(cls, chat_id: int, text: str, **kwargs):
        return (await cls._get_last(cls._send_to(chat_id, text, **kwargs))).id

    @classmethod
    async def send_to_v2(cls, chat_id: int, text: str, **kwargs):
        return [m.id async for m in cls._send_to(chat_id, text, **kwargs)]

    @classmethod
    async def send_to_v3(cls, chat_id: int, text: str, **kwargs):
        return await cls._get_last(cls._send_to(chat_id, text, **kwargs))

    @classmethod
    async def send_to_v4(cls, chat_id: int, text: str, **kwargs):
        return [m async for m in cls._send_to(chat_id, text, **kwargs)]

    @classmethod
    async def _send_to(cls, chat_id: int, text: str, **kwargs):
        context = cls.get_context()
        texts = longtext_split(text)
        kwargs['chat_id'] = chat_id
        async for m in cls._sequence_send(context.bot.send_message, texts, **kwargs):
            yield m
    ##############################

    @classmethod
    async def _sequence_send(cls, interface_func: Callable[..., Awaitable["Message"]], texts: List[str], **kwargs):
        rp_markup = kwargs.pop('reply_markup', None)
        for i, t in enumerate(texts):
            if rp_markup is not None and i == len(texts) - 1:
                kwargs['reply_markup'] = rp_markup
            yield await cls._send_ignore_parsemode_or_replyto_exceptions(interface_func, text=t, **kwargs)

    @classmethod
    async def _retry_call(cls, func: Callable[..., Awaitable[_T]], *args, **kwargs):
        # not using `raise from` to avoid long traceback
        for i in range(cls.RETRY_TIMES):
            try:
                return await func(*args, **kwargs)
            except (BadRequest, ChatMigrated, Forbidden, InvalidToken) as e:
                raise e  # exit fast
            except TelegramError as e:
                if i == cls.RETRY_TIMES - 1:
                    raise e
                _sleep_time = e.retry_after + 1 if isinstance(e, RetryAfter) else cls.RETRY_SLEEP_TIME
                await asyncio.sleep(_sleep_time)
        raise RuntimeError(f"unreachable: RETRY_TIMES={cls.RETRY_TIMES}")

    @classmethod
    async def _send_ignore_parsemode_or_replyto_exceptions(
        cls,
        interface_func: Callable[..., Awaitable["Message"]],
        **kwargs
    ) -> "Message":
        try:
            return await cls._retry_call(interface_func, **kwargs)
        except BadRequest as e:
            if str(e).find("Replied message not found") != -1:
                kwargs.pop('reply_to_message_id')
                return await cls._send_ignore_parsemode_or_replyto_exceptions(interface_func, **kwargs)
            if str(e).find('parse') != -1:
                parse_mode = kwargs.pop('parse_mode', None)
                if parse_mode is None:
                    raise BadRequest(e.message) from e
                return await cls._send_ignore_parsemode_or_replyto_exceptions(interface_func, **kwargs)
            raise BadRequest(e.message) from e
