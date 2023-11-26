import importlib
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Optional, Protocol, Type, overload

from telegram import Update
from telegram.ext import CommandHandler, filters

from bot_framework.module_analyze_utils import get_module_class_from_name
from bot_framework.module_base import TelegramBotModuleBase
from bot_logging import warn
from context_manager import ContextHelper


if TYPE_CHECKING:
    from telegram.ext import BaseHandler

    from bot_framework.context import RichCallbackContext


class CallbackBase(object):
    handler_type: Type["BaseHandler"]

    def __init__(self, func, *args, **kwargs):
        self._instance = None
        self.on_init(*args, **kwargs)
        self._register_and_wrap(func)

    def on_init(self, *args, **kwargs):
        raise NotImplementedError

    def _register_and_wrap(self, func):
        # try:
        #     module_name = func.__module__
        #     kls = get_module_class_from_name(module_name, TelegramBotModuleBase)
        #     if kls is None:
        #         warn("class is None, skip register")
        #     else:
        #         kls.register_new_handler(func)
        # except Exception as e:
        #     warn("_register_and_wrap:" + repr(e))
        wraps(func)(self)

    async def __call__(self, update: Update, context: "RichCallbackContext"):
        # pre execute
        # pass

        # check blacklist
        # pass
        with ContextHelper(context):
            if self._instance is not None:
                return await self.__wrapped__(self._instance, update, context)  # type: ignore
            else:
                return await self.__wrapped__(update, context)  # type: ignore

    def __get__(self, instance, cls):
        if instance is not None:
            self._instance = instance
        return self

    def to_handler(self, **kwds):
        kwds.update(self.kwargs)
        return self.handler_type(callback=self, **kwds)


class CommandCallback(CallbackBase):
    handler_type = CommandHandler

    def on_init(self, filters, block):
        self.filters = filters
        self.block = block

    @property
    def kwargs(self):
        return {
            "filters": self.filters,
            "block": self.block,
            "command": self.__wrapped__.__name__,
        }


class GeneralCallback(CallbackBase):
    def on_init(self, handler_type, kwargs):
        self.handler_type = handler_type
        self.kwargs = kwargs


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

    def __call__(self, func):
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


class GeneralCallbackWrapper(object):
    """
    Internal decorator for command callback functions.
    """

    def __init__(
        self,
        handler_type, **kwargs
    ):
        self.handler_type = handler_type
        self.kwargs = kwargs

    def __call__(self, func):
        return CommandCallback(func, self.handler_type, self.kwargs)


@overload
def command_callback_wrapper(func: Callable) -> CommandCallback:
    ...


@overload
def command_callback_wrapper(
    block: bool = False,
    filters: Optional[filters.BaseFilter] = None,
) -> CommandCallback:
    ...


def command_callback_wrapper(  # type: ignore
    block: Any = False,
    filters: Optional[filters.BaseFilter] = None,
):
    if callable(block):
        return _CommandCallbackMethodDecor()(block)
    return _CommandCallbackMethodDecor(filters, block)


def general_callback_wrapper(handler_type, **kwargs):
    if not callable(handler_type):
        raise TypeError("general_callback_wrapper use first argument to identify handler type")
    return GeneralCallbackWrapper(handler_type, **kwargs)
