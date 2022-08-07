from functools import wraps
from typing import TYPE_CHECKING, Callable, TypeVar

from telegram import Update
from telegram.ext import CallbackContext

if TYPE_CHECKING:
    from bot_framework.botbase import BotBase


RT = TypeVar("RT")


class CommandCallbackMethod(object):
    """
    A decorator for command callback functions, only for class methods.
    """

    def __init__(self, func: Callable[[Update, "CallbackContext"], RT]) -> None:
        wraps(func)(self)
        self.instance: "BotBase" = None

    def __call__(self, *args, **kwargs):
        numOfArgs = len(args) + len(kwargs.keys())
        if numOfArgs != 2:
            raise RuntimeError(
                f"The number of arguments of callback method should be 2, but received {numOfArgs}"
            )

        if len(args) == 2:
            fakeinstance = self.preExecute(*args)
        elif len(args) == 1:
            fakeinstance = self.preExecute(args[0], **kwargs)
        else:
            fakeinstance = self.preExecute(**kwargs)

        instance = self.instance
        with instance.lock:
            if any(
                x in instance.blacklist
                for x in (fakeinstance.lastchat, fakeinstance.lastuser)
            ):
                fakeinstance.errorInfo("you are in blacklist")
                return

        return self.__wrapped__(fakeinstance, *args, **kwargs)

    def preExecute(self, update: Update, context: "CallbackContext") -> "BotBase":
        """在每个command Handler前调用，是指令的前置函数"""
        if self.instance is None:
            raise RuntimeError("command callback method还未获取实例")
        return self.instance.renewStatus(update)

    def __get__(self, instance, cls):
        if instance is None:
            raise TypeError("该装饰器仅适用于方法")
        if self.instance is None:
            self.instance = instance
        return self
