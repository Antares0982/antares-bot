# pylint: disable=no-member, not-callable, arguments-differ
import re
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Pattern, Type, Union, overload

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from telegram.ext import filters as filters_module

from antares_bot.basic_language import BasicLanguage as L
from antares_bot.bot_logging import get_logger
from antares_bot.context_manager import ContextHelper
from antares_bot.error import InvalidChatTypeException, InvalidQueryException, UserPermissionException, permission_exceptions


if TYPE_CHECKING:
    from telegram.ext import BaseHandler

    from antares_bot.context import RichCallbackContext

_LOGGER = get_logger(__name__)


class CallbackBase(object):
    """
    Base class for all callback wrappers.
    subclasses need to implement `kwargs` property and `on_init`.
    """
    handler_type: Type["BaseHandler"]

    def __init__(self, func, *args, **kwargs):
        self._instance = None
        self.on_init(*args, **kwargs)
        self._register_and_wrap(func)
        self._pre_executer = None

    def on_init(self, *args, **kwargs):
        raise NotImplementedError

    def _register_and_wrap(self, func):
        wraps(func)(self)

    async def __call__(self, update: Update, context: "RichCallbackContext"):
        # pre execute
        await self.pre_execute(update, context)

        # check blacklist
        # pass
        with ContextHelper(context):
            try:
                if self._instance is not None:
                    return await self.__wrapped__(self._instance, update, context)  # type: ignore
                else:
                    return await self.__wrapped__(update, context)  # type: ignore
            except permission_exceptions() as e:
                try:
                    if self.handler_type == CommandHandler and not context.is_channel_message():
                        if isinstance(e, UserPermissionException):
                            from antares_bot.bot_inst import get_bot_instance
                            await get_bot_instance().reply(L.t(L.NO_PERMISSION))
                        elif isinstance(e, InvalidChatTypeException):
                            from antares_bot.bot_inst import get_bot_instance
                            await get_bot_instance().reply(L.t(L.INVALID_CHAT_TYPE).format(context.chat_type_str()))
                except Exception:
                    _LOGGER.error("%s.__call__", self.__class__.__name__, exc_info=True)
            except InvalidQueryException as e:
                _LOGGER.warning("Invalid query: %s %s", update.callback_query, e)

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

    def __repr__(self) -> str:
        try:
            name = self.__name__  # type: ignore
        except AttributeError:
            name = self.__class__.__name__
        return f"{name}, of type {self.handler_type.__name__}"


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
            "command": self.__wrapped__.__name__,  # pylint: disable=no-member
        }


class GeneralCallback(CallbackBase):
    PRE_EXUCUTER_KW = 'pre_executer'

    def on_init(self, handler_type, kwargs: dict):
        self.handler_type = handler_type
        self.kwargs = kwargs
        #
        pre_executer = kwargs.pop(self.PRE_EXUCUTER_KW, None)
        if pre_executer is not None:
            self._pre_executer = pre_executer


class _CommandCallbackMethodDecor(object):
    """
    Internal decorator for command callback functions.
    """

    def __init__(
        self,
        filters: Optional[filters_module.BaseFilter] = None,
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


class ConditionFilter(filters_module.BaseFilter):
    def __init__(self, condition: Callable[[Update], bool]):
        super().__init__()
        self.condition = condition

    def check_update(self, update: Update) -> bool:
        return self.condition(update)


@overload
def command_callback_wrapper(func: Callable) -> CommandCallback:
    ...


@overload
def command_callback_wrapper(
    block: bool = False,
    filters: Optional[filters_module.BaseFilter] = None,
) -> CommandCallback:
    ...


def command_callback_wrapper(  # type: ignore
    block: Any = False,
    filters: Optional[filters_module.BaseFilter] = None,
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
    kwargs: Dict[str, Any] = {}
    kwargs['pattern'] = pattern
    kwargs[GeneralCallback.PRE_EXUCUTER_KW] = _btn_pre_executer
    return general_callback_wrapper(CallbackQueryHandler, **kwargs)


@overload
def msg_handle_wrapper(filters: Callable[["Update"], Any]) -> GeneralCallbackWrapper:
    ...


@overload
def msg_handle_wrapper(func: Callable[[Any, "Update", "RichCallbackContext"], Any]) -> GeneralCallback:
    ...


@overload
def msg_handle_wrapper(filters: Optional[filters_module.BaseFilter] = None) -> GeneralCallbackWrapper:
    ...


def msg_handle_wrapper(*args, **kwargs):
    """
    message handler wrapper.
    if need check before execute, pass a filter object in kwargs `filters`
    """
    if len(args) > 0 and callable(args[0]):
        return general_callback_wrapper(MessageHandler, filters=None)(args[0])
    # has kwargs
    filters = kwargs.get('filters', None)
    if filters is not None and not isinstance(filters, filters_module.BaseFilter):
        # wrap it
        _filters = ConditionFilter(filters)
        kwargs['filters'] = _filters
    return general_callback_wrapper(MessageHandler, *args, **kwargs)


photo_handle_wrapper = general_callback_wrapper(MessageHandler, filters=filters_module.PHOTO & (~filters_module.ChatType.CHANNEL))
