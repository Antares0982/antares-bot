import re
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Optional, Pattern, Type, Union, overload

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters

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
        self._pre_executer = None

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
        await self.pre_execute(update, context)

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

    async def pre_execute(self, update: Update, context: "RichCallbackContext"):
        if self._pre_executer:
            await self._pre_executer(update, context)


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
    PRE_EXUCUTER_KW = 'pre_executer'

    def on_init(self, handler_type, kwargs):
        self.handler_type = handler_type
        self.kwargs = kwargs
        if self.PRE_EXUCUTER_KW in kwargs:
            self._pre_executer = kwargs[self.PRE_EXUCUTER_KW]
            kwargs.pop(self.PRE_EXUCUTER_KW)


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
        return GeneralCallback(func, self.handler_type, self.kwargs)


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


def general_callback_wrapper(handler_type, block=False, **kwargs):
    if not callable(handler_type):
        raise TypeError("general_callback_wrapper use first argument to identify handler type")
    if 'block' not in kwargs:
        kwargs['block'] = block
    return GeneralCallbackWrapper(handler_type, **kwargs)


async def _btn_pre_executer(update: Update, context: "RichCallbackContext"):
    query = update.callback_query
    assert query is not None and query.data is not None
    await query.answer()


def btn_click_wrapper(
        pattern: Optional[Union[str, Pattern[str], type, Callable[[object], Optional[bool]]]] = None
):
    if isinstance(pattern, str):
        # startswith `pattern`
        pattern = re.compile(f"^{pattern}")
    return general_callback_wrapper(CallbackQueryHandler, pre_executer=_btn_pre_executer, pattern=pattern)


msg_handle_wrapper = general_callback_wrapper(MessageHandler, filters=None)
