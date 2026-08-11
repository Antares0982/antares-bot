import pytest

from antares_bot.context_manager import ContextHelper, InvalidContext, get_context
from antares_bot.patching.job_quque_ex import (
    _MISFIRE_GRACE_TIME,
    JobQueueEx,
    _PatchedAsyncIOScheduler,
    fix_misfire_grace_time,
)


# ------------------------------------------------------ fix_misfire_grace_time


def test_fix_misfire_grace_time_creates_the_section():
    d: dict = {}
    fix_misfire_grace_time(d)
    assert d == {"job_defaults": {"misfire_grace_time": _MISFIRE_GRACE_TIME}}


def test_fix_misfire_grace_time_does_not_override():
    d = {"job_defaults": {"misfire_grace_time": 5}}
    fix_misfire_grace_time(d)
    assert d["job_defaults"]["misfire_grace_time"] == 5


def test_fix_misfire_grace_time_keeps_sibling_keys():
    d = {"job_defaults": {"coalesce": True}}
    fix_misfire_grace_time(d)
    assert d["job_defaults"] == {
        "coalesce": True,
        "misfire_grace_time": _MISFIRE_GRACE_TIME,
    }


# --------------------------------------------------- scheduler_configuration


def test_scheduler_configuration_defaults(cfg, monkeypatch):
    monkeypatch.delattr(cfg.AntaresBotConfig, "JOB_QUEUE_CONFIG", raising=False)
    config = JobQueueEx().scheduler_configuration
    assert config["job_defaults"]["misfire_grace_time"] == _MISFIRE_GRACE_TIME


def test_scheduler_configuration_merges_user_config(cfg, monkeypatch):
    monkeypatch.setattr(
        cfg.AntaresBotConfig,
        "JOB_QUEUE_CONFIG",
        {"job_defaults": {"misfire_grace_time": 30}},
        raising=False,
    )
    config = JobQueueEx().scheduler_configuration
    assert config["job_defaults"]["misfire_grace_time"] == 30


def test_scheduler_configuration_merge_is_deep(cfg, monkeypatch):
    """A nested override must not wipe the sibling keys PTB set up."""
    base = JobQueueEx().scheduler_configuration
    assert "executors" in base

    monkeypatch.setattr(
        cfg.AntaresBotConfig,
        "JOB_QUEUE_CONFIG",
        {"job_defaults": {"coalesce": False}},
        raising=False,
    )
    config = JobQueueEx().scheduler_configuration
    # keys PTB set up survive the merge
    assert set(config) >= set(base)
    assert config["job_defaults"]["coalesce"] is False
    assert config["job_defaults"]["misfire_grace_time"] == _MISFIRE_GRACE_TIME


def test_scheduler_configuration_aliases_a_user_only_section(cfg, monkeypatch):
    """``merge_dicts`` only copies sections present on *both* sides. PTB's base
    config has no ``job_defaults``, so the user's dict is carried over by
    reference and ``fix_misfire_grace_time`` writes the default straight into
    it. Harmless (the value written is the one that would be applied anyway),
    but the config object the user declared does get touched.
    """
    user_config: dict = {"job_defaults": {}}
    monkeypatch.setattr(
        cfg.AntaresBotConfig, "JOB_QUEUE_CONFIG", user_config, raising=False
    )
    JobQueueEx().scheduler_configuration
    assert user_config == {"job_defaults": {"misfire_grace_time": _MISFIRE_GRACE_TIME}}


# ------------------------------------------------- _PatchedAsyncIOScheduler


def test_add_job_runs_with_an_invalidated_context(monkeypatch, make_context):
    seen = []

    def fake_add_job(self, *args, **kwargs):
        seen.append(get_context())
        return "job"

    monkeypatch.setattr(_PatchedAsyncIOScheduler.__bases__[0], "add_job", fake_add_job)

    scheduler = JobQueueEx().scheduler
    ct = make_context()
    with ContextHelper(ct):
        assert scheduler.add_job(lambda: None) == "job"
        # the handler context is restored afterwards
        assert get_context() is ct

    assert isinstance(seen[0], InvalidContext)


def test_job_queue_ex_uses_the_patched_scheduler():
    assert isinstance(JobQueueEx().scheduler, _PatchedAsyncIOScheduler)


def test_job_queue_ex_requires_apscheduler(monkeypatch):
    import antares_bot.patching.job_quque_ex as jq

    monkeypatch.setattr(jq, "APS_AVAILABLE", False)
    with pytest.raises(RuntimeError, match="job-queue"):
        JobQueueEx()
