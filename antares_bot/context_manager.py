from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Coroutine, TypeVar, overload

from antares_bot.context import RichCallbackContext


if TYPE_CHECKING:
    from contextvars import Token


_JobCallback = Callable[[RichCallbackContext], Awaitable[Any]]
_CoroutineJobCallback = Callable[[RichCallbackContext], Coroutine[Any, Any, Any]]
_T = TypeVar("_T", _JobCallback, _CoroutineJobCallback)

context_manager: ContextVar[RichCallbackContext] = ContextVar('RichCallbackContext', default=None)  # type: ignore


def get_context():
    return context_manager.get()


def set_context(context: RichCallbackContext):
    return context_manager.set(context)


def reset_context(token: "Token[RichCallbackContext]"):
    context_manager.reset(token)


@overload
def callback_job_wrapper(context: RichCallbackContext) -> Callable[[_T], _T]:
    ...


@overload
def callback_job_wrapper(func: _T) -> _T:
    ...


def callback_job_wrapper(arg):
    if isinstance(arg, RichCallbackContext):
        def wrapper(func):
            async def wrapped(*args, **kwargs):
                with ContextHelper(arg):
                    return await func(*args, **kwargs)
            return wrapped
        return wrapper

    # is function
    _ct = get_context()

    async def wrapped(*args, **kwargs):
        with ContextHelper(_ct):
            return await arg(*args, **kwargs)
    return wrapped


class ContextHelper:
    __slots__ = ("context", "token")

    def __init__(self, context: RichCallbackContext):
        self.context = context
        self.token = None

    def __enter__(self):
        self.token = set_context(self.context)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        reset_context(self.token)
        self.token = None
        return False


class InvalidContextError(RuntimeError):
    pass


class InvalidContext:
    def __getattr__(self, _):
        raise InvalidContextError("Invalid context. Did you forget to use `callback_job_wrapper` when creating callback?")


class ContextReverseHelper:
    def __init__(self):
        self.token = None

    def __enter__(self):
        self.token = context_manager.set(InvalidContext())
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        context_manager.reset(self.token)
        self.token = None
        return False
