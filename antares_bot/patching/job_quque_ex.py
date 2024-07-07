import weakref
from typing import TYPE_CHECKING, Any, Optional

from telegram.ext import JobQueue

from antares_bot.bot_default_cfg import AntaresBotConfig
from antares_bot.context_manager import ContextReverseHelper
from antares_bot.utils import merge_dicts, read_user_cfg


try:
    import pytz  # type: ignore
    from apscheduler.executors.asyncio import AsyncIOExecutor  # type: ignore
    from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore

    APS_AVAILABLE = True
except ImportError:
    APS_AVAILABLE = False

if TYPE_CHECKING:
    from telegram.ext import Application


_MISFIRE_GRACE_TIME = 60  # seconds


class _PatchedAsyncIOScheduler(AsyncIOScheduler):
    def add_job(self, *args, **kwargs):
        with ContextReverseHelper():
            return super().add_job(*args, **kwargs)


class JobQueueEx(JobQueue):
    def __init__(self) -> None:  # pylint: disable=super-init-not-called
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

    @property
    def scheduler_configuration(self):
        ret = super().scheduler_configuration
        scheduler_config = read_user_cfg(AntaresBotConfig, "JOB_QUEUE_CONFIG")
        if scheduler_config is not None:
            ret = merge_dicts(ret, scheduler_config)
        fix_misfire_grace_time(ret)
        return ret


def fix_misfire_grace_time(d: dict[str, Any]):
    d.setdefault("job_defaults", {}).setdefault("misfire_grace_time", _MISFIRE_GRACE_TIME)
