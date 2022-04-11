# region import
import types
from functools import wraps
from typing import Any, Callable, Dict, List, Tuple, TypeVar

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

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

# region const
RT = TypeVar("RT")
# endregion

# region function


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


def flattenButton(
    buttons: List[InlineKeyboardButton], numberInOneLine: int
) -> InlineKeyboardMarkup:
    btl: List[List[InlineKeyboardButton]] = []
    while len(buttons) > numberInOneLine:
        btl.append(buttons[:numberInOneLine])
        buttons = buttons[numberInOneLine:]
    if len(buttons) > 0:
        btl.append(buttons)
    return InlineKeyboardMarkup(btl)


# endregion


class handleStatus(object):
    __slots__ = ["block", "normal"]

    def __init__(self, normal: bool, block: bool) -> None:
        self.block: bool = block
        self.normal: bool = normal

    def __bool__(self):
        ...

    def blocked(self):
        return self.block


handlePassed = handleStatus(True, False)


class handleBlocked(handleStatus):
    __slots__ = []

    def __init__(self, normal: bool = True) -> None:
        super().__init__(normal=normal, block=True)

    def __bool__(self):
        return self.normal


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


class commandCallbackMethod(object):
    """表示一个指令的callback函数，仅限于类的成员方法。
    调用时，会执行一次指令的前置函数。"""

    def __init__(self, func: Callable[[Update, "CallbackContext"], RT]) -> None:
        wraps(func)(self)
        self.instance: "baseBot" = None

    def __call__(self, *args, **kwargs):
        numOfArgs = len(args) + len(kwargs.keys())
        if numOfArgs != 2:
            raise RuntimeError(f"指令的callback function参数个数应为2，但接受到{numOfArgs}个")

        if len(args) == 2:
            fakeinstance = self.preExecute(*args)
        elif len(args) == 1:
            fakeinstance = self.preExecute(args[0], **kwargs)
        else:
            fakeinstance = self.preExecute(**kwargs)

        inst = self.instance
        with inst.lock:
            if any(
                x in inst.blacklist
                for x in (fakeinstance.lastchat, fakeinstance.lastuser)
            ):
                fakeinstance.errorInfo("你在黑名单中，无法使用任何功能")
                return

        return self.__wrapped__(fakeinstance, *args, **kwargs)

    def preExecute(self, update: Update, context: "CallbackContext") -> "baseBot":
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
    ) -> handleStatus:
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
            return handlePassed

        if workingmethod != self.matchdict[callback][0]:
            return handleBlocked(instance.queryError(query))

        utilfunc = self.matchdict[callback][1]

        return handleBlocked(utilfunc(instance, query, args))
