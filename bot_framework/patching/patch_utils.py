
from typing import TYPE_CHECKING, Any, Optional, Protocol, Tuple, TypeGuard, TypeVar

from telegram.ext import BaseHandler
from telegram.ext._utils.types import CCT

from bot_framework.patching.conversation_handler_ex import ConversationHandlerEx


if TYPE_CHECKING:
    from bot_framework.patching.application_ex import ApplicationEx


class AtomHandler(Protocol[CCT]):
    async def do_process_atom(
        self,
        context: Optional[CCT],
        update: object,
        app: "ApplicationEx[Any, CCT, Any, Any, Any, Any]",
    ) -> Tuple[bool, Optional[CCT], bool]:
        ...


def need_atom_process(handler: BaseHandler) -> TypeGuard[AtomHandler]:
    return isinstance(handler, ConversationHandlerEx)
