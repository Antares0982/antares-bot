import time,os
from typing import TYPE_CHECKING, Any, Optional, overload

from telegram import InlineKeyboardMarkup
from telegram.error import BadRequest

if TYPE_CHECKING:
    from bot_framework.botbase import BotBase


class BotMessageBase(object):
    def _reply_retries(self: 'BotBase', retries: int = 5, sleeptime: int = 5, kwargs={}) -> int:
        for i in range(retries):
            try:
                ans = self.bot.send_message(**kwargs).message_id
            except Exception as e:
                if (
                    e.__class__ is BadRequest
                    and str(e).find("Replied message not found") != -1
                ):
                    kwargs.pop("reply_to_message_id")
                    i -= 1
                    continue

                elif e.__class__ is BadRequest:
                    raise e

                elif i == retries - 1:
                    raise e

                time.sleep(sleeptime)

            else:
                break
        return ans

    @overload
    def reply(
        self: 'BotBase',
        chat_id: int,
        text: str,
        reply_markup: InlineKeyboardMarkup,
        reply_to_message_id: int,
        parse_mode: str,
        timeout: int,
    ) -> int:
        ...

    def reply(self: 'BotBase', *args, **kwargs) -> int:
        """
        调用send_message方法，回复或发送消息。
        支持telegram bot中`send_message`方法的keyword argument，
        如`reply_markup`，`reply_to_message_id`，`parse_mode`，`timeout`。
        返回值是message id
        """
        ans = None
        chat_id: Optional[int] = None
        text: str = None
        if len(args) > 0:
            if type(args[0]) is int:
                chat_id = args[0]
                kwargs["chat_id"] = chat_id
            elif type(args[0]) is str:
                text = args[0]
                kwargs["text"] = text

            if len(args) > 1:
                text = args[1]
                kwargs["text"] = text

        if chat_id is None and "chat_id" in kwargs:
            chat_id = kwargs["chat_id"]

        if text is None and "text" in kwargs:
            text = kwargs["text"]

        if not text:
            raise RuntimeError("error: no text to send")

        if chat_id is None:
            kwargs["chat_id"] = self.lastchat
            if self.lastmsgid >= 0 and "reply_to_message_id" not in kwargs:
                kwargs["reply_to_message_id"] = self.lastmsgid

        txts = text.split("\n")

        rp_markup = None
        if len(text) >= 1000:
            while len(txts) > 10 or len(text) >= 1000:
                if "reply_markup" in kwargs:
                    rp_markup = kwargs.pop("reply_markup")
                if len(txts) > 10:
                    line = 1
                    l = len(txts[0])
                    if l >= 1000:
                        kwargs["text"] = text[:1000]
                        text = text[1000:]
                        txts = text.split("\n")
                    else:
                        while line <= 10 and l < 1000:
                            l += len(txts[line])
                            line += 1
                        line -= 1
                        kwargs["text"] = "\n".join(txts[:line])
                        txts = txts[line:]
                        text = "\n".join(txts)
                else:
                    kwargs["text"] = text[:1000]
                    text = text[1000:]
                    txts = text.split("\n")

                ans = self._reply_retries(5, 5, kwargs)

        if len(text) > 0:
            kwargs["text"] = text
            if rp_markup is not None:
                kwargs["reply_markup"] = rp_markup
            ans = self._reply_retries(5, 5, kwargs)

        if ans is None:
            raise ValueError("没有成功发送消息")
        return ans

    @overload
    def reply_doc(
        self: 'BotBase',
        chat_id: int,
        document: Any,
        filename: str,
        caption: str,
        reply_markup: InlineKeyboardMarkup,
        reply_to_message_id: int,
        parse_mode: str,
        timeout: int,
    ) -> int:
        ...

    def reply_doc(self: 'BotBase', *args, **kwargs) -> int:
        """
        调用`send_document`方法，回复或发送消息.
        支持telegram bot中`send_document`方法的keyword argument，
        如`reply_markup`，`reply_to_message_id`，`parse_mode`，`timeout`.
        返回值是message id.

        Note:
            * 如果开头传入的参数不是keyword argument，只接受chat_id在前，
                document在后的顺序，且只支持这两个参数不使用keyword argument.
        """
        ans = None
        chat_id: Optional[int] = None
        document = None
        if len(args) > 0:
            if type(args[0]) is int:
                chat_id = args[0]
                kwargs["chat_id"] = chat_id
            else:
                document = args[0]
                kwargs["document"] = document

            if len(args) > 1:
                document = args[1]
                kwargs["document"] = document

        if document is None and "document" in kwargs:
            document = kwargs["document"]

        if document is None:
            raise ValueError("发生错误：发送消息时没有文件")

        if chat_id is None and "chat_id" in kwargs:
            chat_id = kwargs["chat_id"]

        if chat_id is None:
            kwargs["chat_id"] = self.lastchat
            if self.lastmsgid >= 0 and "reply_to_message_id" not in kwargs:
                kwargs["reply_to_message_id"] = self.lastmsgid

        if "timeout" not in kwargs:
            kwargs["timeout"] = 120

        self.debuginfo("sending document:" + str(kwargs))

        isfile = False

        with self.locks.filelock:
            if type(document) is str and os.path.exists(document):
                kwargs["document"] = open(document, "rb")
                isfile = True
            ans = self.bot.send_document(**kwargs).message_id

        if isfile:
            kwargs["document"].close()
        return ans

    @overload
    def reply_photo(
        self: 'BotBase',
        chat_id: int,
        photo: Any,
        filename: str,
        caption: str,
        reply_markup: InlineKeyboardMarkup,
        reply_to_message_id: int,
        parse_mode: str,
        timeout: int,
    ) -> int:
        ...

    def reply_photo(self: 'BotBase', *args, **kwargs) -> int:
        """
        调用`send_photo`方法，回复或发送消息.
        支持telegram bot中`send_photo`方法的keyword argument，
        如`reply_markup`，`reply_to_message_id`，`parse_mode`，`timeout`.
        返回值是message id.

        Note:
            * 如果开头传入的参数不是keyword argument，只接受chat_id在前，
                photo在后的顺序，且只支持这两个参数不使用keyword argument.
        """
        ans = None
        chat_id: Optional[int] = None
        photo = None
        if len(args) > 0:
            if type(args[0]) is int:
                chat_id = args[0]
                kwargs["chat_id"] = chat_id
            else:
                photo = args[0]
                kwargs["photo"] = photo

            if len(args) > 1:
                photo = args[1]
                kwargs["photo"] = photo

        if photo is None and "photo" in kwargs:
            photo = kwargs["photo"]

        if photo is None:
            raise ValueError("发生错误：发送消息时没有图像")

        if chat_id is None and "chat_id" in kwargs:
            chat_id = kwargs["chat_id"]

        if chat_id is None:
            kwargs["chat_id"] = self.lastchat
            if self.lastmsgid >= 0 and "reply_to_message_id" not in kwargs:
                kwargs["reply_to_message_id"] = self.lastmsgid

        if "timeout" not in kwargs:
            kwargs["timeout"] = 120

        self.debuginfo("sending photo:" + str(kwargs))

        isfile = False

        with self.locks.filelock:
            if type(photo) is str and os.path.exists(photo):
                kwargs["photo"] = open(photo, "rb")
                isfile = True
            ans = self.bot.send_photo(**kwargs).message_id

        if isfile:
            kwargs["photo"].close()
        return ans

    def delmsg(self: 'BotBase', chat_id: int, msgid: int, maxTries: int = 5) -> bool:
        """尝试删除消息`maxTries`次，该方法的目的是防止网络原因删除失败时导致执行出现失误"""
        assert maxTries > 0

        for i in range(maxTries):
            try:
                self.bot.delete_message(chat_id=chat_id, message_id=msgid)
            except:
                if i == maxTries - 1:
                    return False
                continue
            break

        return True
