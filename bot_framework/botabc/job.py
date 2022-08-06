from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from bot_framework.botbase import BotBase


class BotJobBase(object):
    def remove_job_if_exists(self: 'BotBase', name: str) -> bool:
        """Remove job with given name. Returns whether job was removed."""

        current_jobs = self.updater.job_queue.get_jobs_by_name(name)
        if not current_jobs:
            return False
        for job in current_jobs:
            job.schedule_removal()
        return True

    def job_exists(self: 'BotBase', name: str) -> bool:
        current_jobs = self.updater.job_queue.get_jobs_by_name(name)
        return bool(current_jobs)
