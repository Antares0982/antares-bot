from typing import Any, Generator, Literal, Optional, Sequence, Union

from telegram import Document, Message, MessageEntity, PhotoSize
from telegram._utils.defaultvalue import DEFAULT_NONE
from telegram._utils.types import DVInput, FileInput, JSONDict, ODVInput, ReplyMarkup
from telegram.ext._utils.types import RLARGS


class TelegramBotBaseWrapper(object):
    @classmethod
    async def success_info(
        cls,
        text: str,
        *,
        chat_id: Union[int, str, None] = None,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        entities: Optional[Sequence[MessageEntity]] = None,
        disable_web_page_preview: ODVInput[bool] = DEFAULT_NONE,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        reply_markup: Optional[ReplyMarkup] = None,
        message_thread_id: Optional[int] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = DEFAULT_NONE,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
        rate_limit_args: Optional[RLARGS] = None,
    ) -> Literal[True]:
        ...

    @classmethod
    async def error_info(
        cls,
        text: str,
        *,
        chat_id: Union[int, str, None] = None,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        entities: Optional[Sequence[MessageEntity]] = None,
        disable_web_page_preview: ODVInput[bool] = DEFAULT_NONE,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        reply_markup: Optional[ReplyMarkup] = None,
        message_thread_id: Optional[int] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = DEFAULT_NONE,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
        rate_limit_args: Optional[RLARGS] = None,
    ) -> Literal[False]:
        ...

    @classmethod
    async def reply_to(
        cls,
        message: Message,
        text: str,
        *,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        disable_web_page_preview: ODVInput[bool] = DEFAULT_NONE,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[ReplyMarkup] = None,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        entities: Optional[Sequence[MessageEntity]] = None,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        message_thread_id: Optional[int] = None,
        quote: Optional[bool] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = DEFAULT_NONE,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
    ) -> int:
        ...

    @classmethod
    async def reply_to_v2(
        cls,
        message: Message,
        text: str,
        *,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        disable_web_page_preview: ODVInput[bool] = DEFAULT_NONE,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[ReplyMarkup] = None,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        entities: Optional[Sequence[MessageEntity]] = None,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        message_thread_id: Optional[int] = None,
        quote: Optional[bool] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = DEFAULT_NONE,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
    ) -> list[int]:
        ...

    @classmethod
    async def reply_to_v3(
        cls,
        message: Message,
        text: str,
        *,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        disable_web_page_preview: ODVInput[bool] = DEFAULT_NONE,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[ReplyMarkup] = None,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        entities: Optional[Sequence[MessageEntity]] = None,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        message_thread_id: Optional[int] = None,
        quote: Optional[bool] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = DEFAULT_NONE,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
    ) -> Message:
        ...

    @classmethod
    async def reply_to_v4(
        cls,
        message: Message,
        text: str,
        *,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        disable_web_page_preview: ODVInput[bool] = DEFAULT_NONE,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[ReplyMarkup] = None,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        entities: Optional[Sequence[MessageEntity]] = None,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        message_thread_id: Optional[int] = None,
        quote: Optional[bool] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = DEFAULT_NONE,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
    ) -> list[Message]:
        ...

    @classmethod
    async def _reply_to(
        cls,
        message: Message,
        text: str,
        *,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        disable_web_page_preview: ODVInput[bool] = DEFAULT_NONE,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[ReplyMarkup] = None,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        entities: Optional[Sequence[MessageEntity]] = None,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        message_thread_id: Optional[int] = None,
        quote: Optional[bool] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = DEFAULT_NONE,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
    ) -> Generator[Message, Any, None]:
        ...

    @classmethod
    async def reply(
        cls,
        text: str,
        *,
        chat_id: Union[int, str, None] = None,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        entities: Optional[Sequence[MessageEntity]] = None,
        disable_web_page_preview: ODVInput[bool] = DEFAULT_NONE,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        reply_markup: Optional[ReplyMarkup] = None,
        message_thread_id: Optional[int] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = DEFAULT_NONE,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
        rate_limit_args: Optional[RLARGS] = None,
    ) -> int:
        ...

    @classmethod
    async def reply_v2(
        cls,
        text: str,
        *,
        chat_id: Union[int, str, None] = None,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        entities: Optional[Sequence[MessageEntity]] = None,
        disable_web_page_preview: ODVInput[bool] = DEFAULT_NONE,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        reply_markup: Optional[ReplyMarkup] = None,
        message_thread_id: Optional[int] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = DEFAULT_NONE,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
        rate_limit_args: Optional[RLARGS] = None,
    ) -> list[int]:
        ...

    @classmethod
    async def reply_v3(
        cls,
        text: str,
        *,
        chat_id: Union[int, str, None] = None,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        entities: Optional[Sequence[MessageEntity]] = None,
        disable_web_page_preview: ODVInput[bool] = DEFAULT_NONE,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        reply_markup: Optional[ReplyMarkup] = None,
        message_thread_id: Optional[int] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = DEFAULT_NONE,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
        rate_limit_args: Optional[RLARGS] = None,
    ) -> Message:
        ...

    @classmethod
    async def reply_v4(
        cls,
        text: str,
        *,
        chat_id: Union[int, str, None] = None,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        entities: Optional[Sequence[MessageEntity]] = None,
        disable_web_page_preview: ODVInput[bool] = DEFAULT_NONE,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        reply_markup: Optional[ReplyMarkup] = None,
        message_thread_id: Optional[int] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = DEFAULT_NONE,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
        rate_limit_args: Optional[RLARGS] = None,
    ) -> list[Message]:
        ...

    @classmethod
    async def _reply(
        cls,
        text: str,
        *,
        chat_id: Union[int, str, None] = None,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        entities: Optional[Sequence[MessageEntity]] = None,
        disable_web_page_preview: ODVInput[bool] = DEFAULT_NONE,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        reply_markup: Optional[ReplyMarkup] = None,
        message_thread_id: Optional[int] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = DEFAULT_NONE,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
        rate_limit_args: Optional[RLARGS] = None,
    ) -> Generator[Message, Any, None]:
        ...

    @classmethod
    async def send_to(
        cls,
        chat_id: int,
        text: str,
        *,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        entities: Optional[Sequence[MessageEntity]] = None,
        disable_web_page_preview: ODVInput[bool] = DEFAULT_NONE,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        reply_markup: Optional[ReplyMarkup] = None,
        message_thread_id: Optional[int] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = DEFAULT_NONE,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
        rate_limit_args: Optional[RLARGS] = None,
    ) -> int:
        ...

    @classmethod
    async def send_to_v2(
        cls,
        chat_id: int,
        text: str,
        *,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        entities: Optional[Sequence[MessageEntity]] = None,
        disable_web_page_preview: ODVInput[bool] = DEFAULT_NONE,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        reply_markup: Optional[ReplyMarkup] = None,
        message_thread_id: Optional[int] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = DEFAULT_NONE,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
        rate_limit_args: Optional[RLARGS] = None,
    ) -> list[int]:
        ...

    @classmethod
    async def send_to_v3(
        cls,
        chat_id: int,
        text: str,
        *,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        entities: Optional[Sequence[MessageEntity]] = None,
        disable_web_page_preview: ODVInput[bool] = DEFAULT_NONE,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        reply_markup: Optional[ReplyMarkup] = None,
        message_thread_id: Optional[int] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = DEFAULT_NONE,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
        rate_limit_args: Optional[RLARGS] = None,
    ) -> Message:
        ...

    @classmethod
    async def send_to_v4(
        cls,
        chat_id: int,
        text: str,
        *,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        entities: Optional[Sequence[MessageEntity]] = None,
        disable_web_page_preview: ODVInput[bool] = DEFAULT_NONE,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        reply_markup: Optional[ReplyMarkup] = None,
        message_thread_id: Optional[int] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = DEFAULT_NONE,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
        rate_limit_args: Optional[RLARGS] = None,
    ) -> list[Message]:
        ...

    @classmethod
    async def _send_to(
        cls,
        chat_id: int,
        text: str,
        *,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        entities: Optional[Sequence[MessageEntity]] = None,
        disable_web_page_preview: ODVInput[bool] = DEFAULT_NONE,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        reply_markup: Optional[ReplyMarkup] = None,
        message_thread_id: Optional[int] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = DEFAULT_NONE,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
        rate_limit_args: Optional[RLARGS] = None,
    ) -> Generator[Message, Any, None]:
        ...
    ##############################

    @classmethod
    async def send_photo(
        cls,
        chat_id: Union[int, str],
        photo: Union[FileInput, PhotoSize],
        *,
        caption: Optional[str] = None,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[ReplyMarkup] = None,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        caption_entities: Optional[Sequence["MessageEntity"]] = None,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        message_thread_id: Optional[int] = None,
        has_spoiler: Optional[bool] = None,
        filename: Optional[str] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = 20,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
        rate_limit_args: Optional[RLARGS] = None
    ) -> Message:
        ...

    @classmethod
    async def reply_photo(
        cls,
        photo: Union[FileInput, PhotoSize],
        *,
        chat_id: Union[int, str, None] = None,
        caption: Optional[str] = None,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[ReplyMarkup] = None,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        caption_entities: Optional[Sequence["MessageEntity"]] = None,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        message_thread_id: Optional[int] = None,
        has_spoiler: Optional[bool] = None,
        filename: Optional[str] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = 20,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
        rate_limit_args: Optional[RLARGS] = None
    ) -> Message:
        ...

    @classmethod
    async def send_document(
        cls,
        chat_id: Union[int, str],
        document: Union[FileInput, Document],
        *,
        caption: Optional[str] = None,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[ReplyMarkup] = None,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        disable_content_type_detection: Optional[bool] = None,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        caption_entities: Optional[Sequence["MessageEntity"]] = None,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        message_thread_id: Optional[int] = None,
        thumbnail: Optional[FileInput] = None,
        filename: Optional[str] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = 20,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
        rate_limit_args: Optional[RLARGS] = None,
    ) -> Message:
        ...

    @classmethod
    async def reply_document(
        cls,
        document: Union[FileInput, Document],
        *,
        chat_id: Union[int, str, None] = None,
        caption: Optional[str] = None,
        disable_notification: DVInput[bool] = DEFAULT_NONE,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[ReplyMarkup] = None,
        parse_mode: ODVInput[str] = DEFAULT_NONE,
        disable_content_type_detection: Optional[bool] = None,
        allow_sending_without_reply: ODVInput[bool] = DEFAULT_NONE,
        caption_entities: Optional[Sequence["MessageEntity"]] = None,
        protect_content: ODVInput[bool] = DEFAULT_NONE,
        message_thread_id: Optional[int] = None,
        thumbnail: Optional[FileInput] = None,
        filename: Optional[str] = None,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = 20,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
        rate_limit_args: Optional[RLARGS] = None,
    ) -> Message:
        ...
