from functools import wraps
from typing import TYPE_CHECKING, Callable, TypeVar

from telegram import Update
from typing_extensions import final

from cfg import *

if TYPE_CHECKING:
    from telegram.ext import CallbackContext

    from basebot import baseBot

RT = TypeVar('RT')


def chatisfromme(update: Update) -> bool:
    return getchatid(update) == MYID


def isfromme(update: Update) -> bool:
    """检查是否来自`MYID`"""
    return getfromid(update) == MYID


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


class handleStatus(object):
    __slots__ = ['block', 'normal']

    def __init__(self, normal: bool, block: bool) -> None:
        self.block: bool = block
        self.normal: bool = normal

    def __bool__(self):
        ...

    def blocked(self):
        return self.block


handlePassed = handleStatus(True, False)


@final
class handleBlocked(handleStatus):
    __slots__ = []

    def __init__(self, normal: bool = True) -> None:
        super().__init__(normal=normal, block=True)

    def __bool__(self):
        return self.normal


@final
class commandCallback(object):
    def __init__(self, func: Callable) -> None:
        wraps(func)(self)

    def __call__(self, *args, **kwargs):
        numOfArgs = len(args)+len(kwargs.keys())
        if numOfArgs != 2:
            raise TypeError(f"指令的callback function参数个数应为2，但接受到{numOfArgs}个")
        return self.__wrapped__(*args, **kwargs)

    def __get__(self, instance, cls):
        if instance is not None:
            raise TypeError("该装饰器不适用于方法")
        return self


@final
class commandCallbackMethod(object):
    """表示一个指令的callback函数，仅限于类的成员方法。
    调用时，会执行一次指令的前置函数。"""

    def __init__(self, func: Callable[[Update, 'CallbackContext'], RT]) -> None:
        wraps(func)(self)
        self.instance: 'baseBot' = None

    def __call__(self, *args, **kwargs):
        numOfArgs = len(args)+len(kwargs.keys())
        if numOfArgs != 2:
            raise RuntimeError(f"指令的callback function参数个数应为2，但接受到{numOfArgs}个")

        if len(args) == 2:
            self.preExecute(*args)
        elif len(args) == 1:
            self.preExecute(args[0], **kwargs)
        else:
            self.preExecute(**kwargs)

        inst = self.instance
        if any(x in inst.blacklist for x in (inst.lastchat, inst.lastuser)):
            inst.errorInfo("你在黑名单中，无法使用任何功能")
            return

        return self.__wrapped__(self.instance, *args, **kwargs)

    def preExecute(self, update: Update, context: 'CallbackContext') -> None:
        """在每个command Handler前调用，是指令的前置函数"""
        if self.instance is None:
            raise RuntimeError("command callback method还未获取实例")
        self.instance.renewStatus(update)

    def __get__(self, instance, cls):
        if instance is None:
            raise TypeError("该装饰器仅适用于方法")
        if self.instance is None:
            self.instance = instance
        return self
