import weakref
from typing import TYPE_CHECKING, Optional

from telegram.ext import JobQueue

from antares_bot.bot_default_cfg import AntaresBotConfig
from antares_bot.context_manager import ContextReverseHelper
from antares_bot.utils import read_user_cfg


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
        if scheduler_config is None:
            ret.setdefault("job_defaults", {})
            ret["job_defaults"]["misfire_grace_time"] = _MISFIRE_GRACE_TIME
            return ret
        else:

            # recursively update ret with scheduler_config
            for key, value in scheduler_config.items():
                if isinstance(value, dict):
                    ret.setdefault(key, {})
                    ret[key].update(value)
                else:
                    ret[key] = value


def merge_dicts(dict1: dict, dict2: dict):
    merged = dict1.copy()  # 先复制 dict1 的内容
    for key, value in dict2.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            # 如果两个 dict 中这个 key 的值都是 dict，那么递归合并
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value  # 否则直接覆盖
    return merged
