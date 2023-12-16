from contextvars import ContextVar
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from contextvars import Token

    from bot_framework.context import RichCallbackContext

context_manager: ContextVar['RichCallbackContext'] = ContextVar('RichCallbackContext', default=None)  # type: ignore


def get_context():
    return context_manager.get()


def set_context(context: "RichCallbackContext"):
    return context_manager.set(context)


def reset_context(token: "Token[RichCallbackContext]"):
    context_manager.reset(token)


class ContextHelper:
    __slots__ = ("context", "token")

    def __init__(self, context: "RichCallbackContext"):
        self.context = context
        self.token = None

    def __enter__(self):
        self.token = set_context(self.context)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        reset_context(self.token)
        self.token = None
        return False
