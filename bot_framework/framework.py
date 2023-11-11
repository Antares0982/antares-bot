from functools import wraps
from typing import TYPE_CHECKING, Optional, Protocol, overload

from telegram import Update
from telegram.ext import filters

if TYPE_CHECKING:
    from context import RichCallbackContext


class CommandCallbackMethodProtocol(Protocol):
    def __call__(_, self, update: Update, context: "RichCallbackContext"):
        ...


class CommandCallback(object):
    def __init__(self, func: CommandCallbackMethodProtocol, filters, block):
        self.filters = filters
        self.block = block
        self.__instance = None
        wraps(func)(self)

    async def __call__(self, update: Update, context: "RichCallbackContext"):
        # pre execute
        # pass

        # check blacklist
        # pass
        return await self.__wrapped__(self.__instance, update, context)

    def __get__(self, instance, cls):
        if instance is None:
            raise TypeError("Should only be used on methods.")
        if self.__instance is None:
            self.__instance = instance
        return self


class _CommandCallbackMethodDecor(object):
    """
    Internal decorator for command callback functions.
    """

    def __init__(
        self,
        filters: Optional[filters.BaseFilter] = None,
        block: bool = False
    ):
        self.filters = filters
        self.block = block

    def __call__(self, func: CommandCallbackMethodProtocol):
        return CommandCallback(func, self.filters, self.block)

    # def _on_handle(self, update: Update, context: "RichCallbackContext"):
    #     # pre execute
    #     pass

    #     # check blacklist
    #     pass

        # numOfArgs = len(args) + len(kwargs.keys())
        # if numOfArgs != 2:
        #     raise RuntimeError(
        #         f"The number of arguments of callback method should be 2, but received {numOfArgs}"
        #     )

        # if len(args) == 2:
        #     fakeinstance = self.preExecute(*args)
        # elif len(args) == 1:
        #     fakeinstance = self.preExecute(args[0], **kwargs)
        # else:
        #     fakeinstance = self.preExecute(**kwargs)

        # instance = self.instance
        # with instance.lock:
        #     if any(
        #         x in instance.blacklist
        #         for x in (fakeinstance.lastchat, fakeinstance.lastuser)
        #     ):
        #         fakeinstance.errorInfo("you are in blacklist")
        #         return

        # return self.__wrapped__(fakeinstance, *args, **kwargs)

    # def preExecute(self, update: Update, context: "CallbackContext") -> "BotBase":
    #     """在每个command Handler前调用，是指令的前置函数"""
    #     if self.instance is None:
    #         raise RuntimeError("command callback method还未获取实例")
    #     return self.instance.renewStatus(update)

    # def __get__(self, instance, cls):
    #     if instance is None:
    #         raise TypeError("该装饰器仅适用于方法")
    #     if self.instance is None:
    #         self.instance = instance
    #     return self


@overload
def command_callback_wrapper(func: CommandCallbackMethodProtocol) -> CommandCallback:
    ...


def command_callback_wrapper(
        block: bool = False,
        filters: Optional[filters.BaseFilter] = None,
):
    if callable(block):
        return _CommandCallbackMethodDecor()(block)
    return _CommandCallbackMethodDecor(filters, block)
