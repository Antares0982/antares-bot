# region import
import types
from functools import wraps
from typing import Any, Callable, Dict, List, Tuple, TypeVar

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

from bot_framework.utils.workflow import (HandleBlocked, HandleStatus,
                                          handleIgnore)
from cfg import *

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from telegram import CallbackQuery
    from telegram.ext import CallbackContext

    from basebot import baseBot
# endregion


class fakeBotObject(object):
    """
    bot instance的伪装类。
    在并发情形下，bot object会在一个command callback函数执行完成之前获取
    新的lastuser，lastchat等信息。在一个update的范围内，如果需要保证这些
    参数是不会发生改变的，使用这个类来伪装成一个botinstance传给callback
    method。注意：除了上述三个数据不会发生改变以外，其他数据是会发生改变的。
    """

    __slots__ = ["_real_bot_obj", "lastchat", "lastuser", "lastmsgid"]

    def __init__(self, bot) -> None:
        self._real_bot_obj = bot
        self.lastchat = 0
        self.lastuser = 0
        self.lastmsgid = -1

    def __getattr__(self, attr):
        x = getattr(self._real_bot_obj, attr)
        if callable(x) and not isinstance(x, types.FunctionType):

            def wraped_func(*args, **kwargs):
                return getattr(type(self._real_bot_obj), attr)(self, *args, **kwargs)

            return wraped_func
        return x

    def __setattr__(self, __name: str, __value: Any) -> None:
        if __name in ["lastchat", "lastuser", "lastmsgid", "_real_bot_obj"]:
            object.__setattr__(self, __name, __value)
            return
        self._real_bot_obj.__dict__[__name] = __value


class commandCallback(object):
    def __init__(self, func: Callable) -> None:
        wraps(func)(self)

    def __call__(self, *args, **kwargs):
        numOfArgs = len(args) + len(kwargs.keys())
        if numOfArgs != 2:
            raise TypeError(f"指令的callback function参数个数应为2，但接受到{numOfArgs}个")
        return self.__wrapped__(*args, **kwargs)

    def __get__(self, instance, cls):
        if instance is not None:
            raise TypeError("该装饰器不适用于方法")
        return self


class buttonQueryHandleMethod(object):
    """
    用于相应按钮请求分发的装饰器。
    被装饰的方法必须通过`class.buttonHandler(self, ...)`的方式调用，并且只返回`matchdict`.
    `matchdict`结构如下：
        `key:(workingmethod, dispatched_method)`
    解释如下：
        key (:obj:`str`): 是callback query data经过split之后的第一个字符串。也就是说，将要相应以`key`
            开头的callback data对应的按钮。
        workingmethod (:obj:`str`): 是bot对该用户当前的工作状态，与
            `instance.workingMethod[instance.lastchat]`比较，这是保证当前该按钮确实处于活跃阶段，否则
            可能造成隐患。如果不同，说明当前不是处于应该相应用户这一按钮请求的时机。如果相同，将参数传给
            `dispatched_method`进行处理。
        dispatched_method (:method:`(CallbackQuery, List[str])->bool`): 实际的响应method。对于对应
            callback data和working method进行具体的处理。`query`与`query.data.split()`两个参数将被传入。
    """

    def __init__(self, func: Callable[[Any], dict]) -> None:
        wraps(func)(self)
        self.matchdict: Dict[
            str, Tuple[str, Callable[["CallbackQuery", List[str]], bool]]
        ] = {}

    def __call__(
        self, instance: "baseBot", update: Update, context: "CallbackContext", **kwargs
    ) -> HandleStatus:
        query: "CallbackQuery" = update.callback_query

        args = query.data.split(" ")

        workingmethod = (
            instance.workingMethod[instance.lastchat]
            if instance.lastchat in instance.workingMethod
            else ""
        )

        callback = args[0]

        if not self.matchdict:
            self.matchdict = self.__wrapped__(instance)

        if callback not in self.matchdict:
            return handleIgnore

        if workingmethod != self.matchdict[callback][0]:
            return HandleBlocked(instance.queryError(query))

        utilfunc = self.matchdict[callback][1]

        return HandleBlocked(utilfunc(instance, query, args))
