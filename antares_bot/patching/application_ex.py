from typing import Any, Coroutine, Optional, Union

from telegram._utils.defaultvalue import DEFAULT_TRUE
from telegram.ext import Application, ApplicationHandlerStop, BaseHandler, ExtBot
from telegram.ext._utils.types import BD, BT, CCT, CD, JQ, UD

from antares_bot.bot_logging import get_logger
from antares_bot.patching.patch_utils import need_atom_process


_LOGGER = get_logger(__name__)


class ApplicationEx(Application[BT, CCT, UD, CD, BD, JQ]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handler_docs: dict[str, str] = {}

    async def process_update(self, update: object) -> None:
        """Processes a single update and marks the update to be updated by the persistence later.
        Exceptions raised by handler callbacks will be processed by :meth:`process_error`.

        .. seealso:: :wiki:`Concurrency`

        .. versionchanged:: 20.0
            Persistence is now updated in an interval set by
            :attr:`telegram.ext.BasePersistence.update_interval`.

        Args:
            update (:class:`telegram.Update` | :obj:`object` | \
                :class:`telegram.error.TelegramError`): The update to process.

        Raises:
            :exc:`RuntimeError`: If the application was not initialized.
        """
        # Processing updates before initialize() is a problem e.g. if persistence is used
        self._check_initialized()

        context = None
        any_blocking = False  # Flag which is set to True if any handler specifies block=True

        for handlers in self.handlers.values():
            try:
                for handler in handlers:
                    if need_atom_process(handler):
                        processed, context, _cur_blocking = await handler.do_process_atom(
                            context, update, self
                        )
                        if processed:
                            any_blocking |= _cur_blocking
                            break
                    else:
                        check = handler.check_update(update)  # Should the handler handle this update?
                        if not (check is None or check is False):  # if yes,
                            if not context:  # build a context if not already built
                                context = self.context_types.context.from_update(update, self)
                                await context.refresh_data()
                            coroutine: Coroutine = handler.handle_update(update, self, check, context)

                            if await self.do_process_update(handler, update, coroutine):
                                any_blocking = True
                            break  # Only a max of 1 handler per group is handled

            # Stop processing with any other handler.
            except ApplicationHandlerStop:
                _LOGGER.debug("Stopping further handlers due to ApplicationHandlerStop")
                break

            # Dispatch any error.
            except Exception as exc:
                if await self.process_error(update=update, error=exc):
                    _LOGGER.debug("Error handler stopped further handlers.")
                    break

        if any_blocking:
            # Only need to mark the update for persistence if there was at least one
            # blocking handler - the non-blocking handlers mark the update again when finished
            # (in __create_task_callback)
            self._mark_for_persistence_update(update=update)

    def _check_should_create_async_task(
        self, handler: BaseHandler[Any, CCT]
    ) -> Optional[Union[bool, object]]:
        return not handler.block or (  # if handler is running with block=False
            handler.block is DEFAULT_TRUE
            and isinstance(self.bot, ExtBot)
            and self.bot.defaults
            and not self.bot.defaults.block
        )

    async def do_process_update(
        self, handler: BaseHandler[Any, CCT], update: object, coroutine: Coroutine
    ) -> bool:
        """Called by a handle to truely process an update.

        Args:
            handler (:class:`telegram.ext.BaseHandler`): The handler that be responsible for
                this update.
            update (:class:`telegram.Update` | :obj:`object` | \
                :class:`telegram.error.TelegramError`): The update to process.
            coroutine (:obj:`Coroutine`): The task that to be processed.

        Returns:
            :obj:`bool`: Whether the handling process is blocking.

        """
        if self._check_should_create_async_task(handler):
            self.create_task(
                coroutine,
                update=update,
                name=(f"Application:{self.bot.id}:do_process_update_non_blocking:{handler}"),
            )
            return False
        await coroutine
        return True
