import weakref
from typing import TYPE_CHECKING, Optional

from telegram.ext import JobQueue

from context_manager import ContextReverseHelper


try:
    import pytz  # type: ignore
    from apscheduler.executors.asyncio import AsyncIOExecutor  # type: ignore
    from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore

    APS_AVAILABLE = True
except ImportError:
    APS_AVAILABLE = False

if TYPE_CHECKING:
    from telegram.ext import Application


class _PatchedAsyncIOScheduler(AsyncIOScheduler):
    def add_job(self, *args, **kwargs):
        with ContextReverseHelper():
            return super().add_job(*args, **kwargs)


class JobQueueEx(JobQueue):
    def __init__(self) -> None:
        if not APS_AVAILABLE:
            raise RuntimeError(
                "To use `JobQueueEx`, PTB must be installed via `pip install "
                '"python-telegram-bot[job-queue]"`.'
            )

        self._application: Optional[weakref.ReferenceType["Application"]] = None
        self._executor = AsyncIOExecutor()
        self.scheduler: AsyncIOScheduler = _PatchedAsyncIOScheduler(
            timezone=pytz.utc, executors={"default": self._executor}
        )
