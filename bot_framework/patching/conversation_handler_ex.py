import asyncio
import datetime
from typing import TYPE_CHECKING, Any, Coroutine, Dict, List, Optional, Tuple, TypeVar, Union, cast

from telegram import Update
from telegram._utils.defaultvalue import DEFAULT_TRUE
from telegram._utils.types import DVType
from telegram.ext import CallbackContext, ConversationHandler
from telegram.ext._basehandler import BaseHandler
from telegram.ext._conversationhandler import PendingState

from bot_logging import get_logger


CCT = TypeVar("CCT", bound="CallbackContext[Any, Any, Any, Any]")

if TYPE_CHECKING:
    from telegram.ext import BaseHandler

    from bot_framework.patching.application_ex import ApplicationEx

_LOGGER = get_logger(__name__)


class ConversationHandlerEx(ConversationHandler[CCT]):
    def __init__(
        self,
        entry_points: List[BaseHandler[Update, CCT]],
        states: Dict[object, List[BaseHandler[Update, CCT]]],
        fallbacks: List[BaseHandler[Update, CCT]],
        allow_reentry: bool = False,
        per_chat: bool = True,
        per_user: bool = True,
        per_message: bool = False,
        conversation_timeout: Optional[Union[float, datetime.timedelta]] = None,
        name: Optional[str] = None,
        persistent: bool = False,
        map_to_parent: Optional[Dict[object, object]] = None,
        block: DVType[bool] = DEFAULT_TRUE,
    ):
        super().__init__(
            entry_points,
            states,
            fallbacks,
            allow_reentry,
            per_chat,
            per_user,
            per_message,
            conversation_timeout,
            name,
            persistent,
            map_to_parent,
            block,
        )
        self._locks_holder = dict()

    def _get_lock(self, key: Tuple[Any, ...]) -> asyncio.Lock:
        # asyncio run in single thread, so we can use dict as lock holder
        lk = self._locks_holder.get(key, None)
        if lk is None:
            lk = asyncio.Lock()
            self._locks_holder[key] = lk
        return lk

    async def do_process_atom(
        self,
        context: Optional[CCT],
        update: object,
        app: "ApplicationEx[Any, CCT, Any, Any, Any, Any]",
    ) -> Tuple[bool, Optional[CCT], bool]:
        """Check if the handler should handle the update, and handle it if yes.
        Override if needed.

        Args:
            context (:class:`telegram.ext.CallbackContext`, optional): The context
                object, may be `None` if not already built.
            update (:obj:`object` | :class:`telegram.Update`): The update to be checked
                (and handled).
            application (:class:`telegram.ext.Application`): The calling application.

        Returns:
            `Tuple[bool, telegram.ext.CallbackContext, bool]`.
            The first boolean is whether the handler handled the update. the second
            is the returned context. The third boolean is whether the handler is
            blocking when handled (should always be `False` if not handled).

        """
        default_ret = False, context, False
        # >>>>>>>>>>>
        # check = self.check_update(update)  # Should the handler handle this update?
        if not isinstance(update, Update):
            return default_ret
        # Ignore messages in channels
        if update.channel_post or update.edited_channel_post:
            return default_ret
        if self.per_chat and not update.effective_chat:
            return default_ret
        if self.per_user and not update.effective_user:
            return default_ret
        if self.per_message and not update.callback_query:
            return default_ret
        if update.callback_query and self.per_chat and not update.callback_query.message:
            return default_ret

        key = self._get_key(update)
        lk = self._get_lock(key)
        async with lk:
            state = self._conversations.get(key)
            check: Optional[object] = None

            # Resolve futures
            if isinstance(state, PendingState):
                _LOGGER.debug("Waiting for asyncio Task to finish ...")

                # check if future is finished or not
                if state.done():
                    res = state.resolve()
                    # Special case if an error was raised in a non-blocking entry-point
                    if state.old_state is None and state.task.exception():
                        self._conversations.pop(key, None)
                        state = None
                    else:
                        self._update_state(res, key)
                        state = self._conversations.get(key)

                # if not then handle WAITING state instead
                else:
                    handlers = self.states.get(self.WAITING, [])
                    for handler_ in handlers:
                        check = handler_.check_update(update)
                        if check is not None and check is not False:
                            _check = self.WAITING, key, handler_, check
                            return await self.__internal_process(context, update, app, _check)
                    return default_ret

            _LOGGER.debug("Selecting conversation %s with state %s", str(key), str(state))

            handler: Optional["BaseHandler"] = None

            # Search entry points for a match
            if state is None or self.allow_reentry:
                for entry_point in self.entry_points:
                    check = entry_point.check_update(update)
                    if check is not None and check is not False:
                        handler = entry_point
                        break

                else:
                    if state is None:
                        return default_ret

            # Get the handler list for current state, if we didn't find one yet and we're still here
            if state is not None and handler is None:
                for candidate in self.states.get(state, []):
                    check = candidate.check_update(update)
                    if check is not None and check is not False:
                        handler = candidate
                        break

                # Find a fallback handler if all other handlers fail
                else:
                    for fallback in self.fallbacks:
                        check = fallback.check_update(update)
                        if check is not None and check is not False:
                            handler = fallback
                            break
                    else:
                        return default_ret

            _check = state, key, handler, check  # type: ignore[return-value]
            return await self.__internal_process(context, update, app, _check)

    async def __internal_process(
        self,
        context: Optional[CCT],
        update: object,
        app: "ApplicationEx[Any, CCT, Any, Any, Any, Any]",
        check: object,
    ):
        if check is None or check is False:  # ensure check is valid
            return False, context, False
        if not context:  # build a context if not already built
            context = app.context_types.context.from_update(update, app)
            await context.refresh_data()
        update = cast(Update, update)
        coroutine: Coroutine = self.handle_update(update, app, check, context)
        is_blocking = await app.do_process_update(self, update, coroutine)
        # Only a max of 1 handler per group is handled
        return True, context, is_blocking
