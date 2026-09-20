from contextvars import ContextVar, Token
from typing import Any, Callable, Coroutine, ParamSpec, TypeVar, overload

from antares_bot.context import RichCallbackContext


_P = ParamSpec("_P")
_R = TypeVar("_R")


class InvalidContextError(RuntimeError):
    pass


class InvalidContext:
    def __getattr__(self, _):
        raise InvalidContextError(
            "Invalid context. Did you forget to use `callback_job_wrapper` when creating callback?"
        )


ContextValue = RichCallbackContext | InvalidContext | None
context_manager: ContextVar[ContextValue] = ContextVar(
    "RichCallbackContext", default=None
)


def get_context() -> Any:
    return context_manager.get()


def set_context(context: RichCallbackContext) -> Token[ContextValue]:
    return context_manager.set(context)


def reset_context(token: Token[ContextValue]):
    context_manager.reset(token)


@overload
def callback_job_wrapper(
    context: RichCallbackContext, /
) -> Callable[
    [Callable[_P, Coroutine[Any, Any, _R]]],
    Callable[_P, Coroutine[Any, Any, _R]],
]: ...


@overload
def callback_job_wrapper(
    func: Callable[_P, Coroutine[Any, Any, _R]], /
) -> Callable[_P, Coroutine[Any, Any, _R]]: ...


def callback_job_wrapper(
    arg: RichCallbackContext | Callable[..., Coroutine[Any, Any, Any]], /
) -> Callable[..., Any]:
    if isinstance(arg, RichCallbackContext):

        def wrapper(func):
            async def wrapped(*args, **kwargs):
                with ContextHelper(arg):
                    return await func(*args, **kwargs)

            return wrapped

        return wrapper

    # is function
    _ct = get_context()
    if not isinstance(_ct, RichCallbackContext):
        raise RuntimeError("No context found")

    async def wrapped(*args, **kwargs):
        with ContextHelper(_ct):
            return await arg(*args, **kwargs)

    return wrapped


class ContextHelper:
    __slots__ = ("context", "token")

    def __init__(self, context: RichCallbackContext):
        self.context = context
        self.token: Token[ContextValue] | None = None

    def __enter__(self):
        self.token = set_context(self.context)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        assert self.token is not None
        reset_context(self.token)
        self.token = None
        return False


class ContextReverseHelper:
    def __init__(self):
        self.token: Token[ContextValue] | None = None

    def __enter__(self):
        self.token = context_manager.set(InvalidContext())
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        assert self.token is not None
        context_manager.reset(self.token)
        self.token = None
        return False
