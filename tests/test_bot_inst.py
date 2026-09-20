import time

import pytest
from telegram.error import Conflict, NetworkError, RetryAfter, TimedOut

import antares_bot.bot_inst as bot_inst
from antares_bot.bot_inst import (
    TelegramBot,
    exception_handler,
    format_traceback,
    register_bot_class,
)
from antares_bot.context_manager import ContextHelper, InvalidContext, get_context
from antares_bot.error import InvalidChatTypeException, UserPermissionException
from antares_bot.patching.job_quque_ex import JobQueueEx


MASTER_ID = 1


@pytest.fixture(autouse=True)
def master(cfg, monkeypatch):
    monkeypatch.setattr(cfg.BasicConfig, "MASTER_ID", MASTER_ID)


class StubInstance:
    def __init__(self):
        self.sent: list[tuple[int, str]] = []
        self.replies: list[str] = []

    async def send_to(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text))
        return 1

    async def reply(self, text, **kwargs):
        self.replies.append(text)
        return 1


@pytest.fixture
def stub_instance(monkeypatch):
    stub = StubInstance()
    monkeypatch.setattr(bot_inst, "get_bot_instance", lambda: stub)
    return stub


# ------------------------------------------------------------ format_traceback


def test_format_traceback_includes_type_and_message():
    try:
        raise ValueError("boom")
    except ValueError as e:
        text = format_traceback(type(e), e, e.__traceback__)
    assert "ValueError" in text
    assert "boom" in text


# -------------------------------------------------------- bot class registry


def test_register_bot_class_accepts_a_subclass():
    class MyBot(TelegramBot):
        pass

    register_bot_class(MyBot)
    assert getattr(bot_inst, "__REGISTERED_BOT_CLASS") is MyBot


def test_register_bot_class_rejects_a_stranger():
    with pytest.raises(RuntimeError):
        register_bot_class(object)  # type: ignore[arg-type]


def test_get_bot_instance_is_a_singleton():
    from antares_bot.bot_inst import get_bot_instance

    assert get_bot_instance() is get_bot_instance()


# ------------------------------------------------------------- construction


def test_bot_builds_offline(bot_app):
    assert bot_app.application is not None
    assert bot_app.bot is bot_app.application.bot
    assert isinstance(bot_app.job_queue, JobQueueEx)
    assert bot_app.updater is not None
    assert bot_app.callback_manager is not None
    assert bot_app.handler_docs == {}
    assert bot_app.exit_fast is False


def test_data_dir_uses_the_config(cfg, monkeypatch):
    monkeypatch.setattr(cfg.BasicConfig, "DATA_DIR", "mydata")
    assert TelegramBot.data_dir().endswith("mydata")


def test_data_dir_rejects_non_string(cfg, monkeypatch):
    monkeypatch.setattr(cfg.BasicConfig, "DATA_DIR", None)
    with pytest.raises(TypeError, match="DATA_DIR"):
        TelegramBot.data_dir()


def test_bot_rejects_non_string_token(cfg, monkeypatch):
    monkeypatch.setattr(cfg.BasicConfig, "TOKEN", None)
    with pytest.raises(TypeError, match="TOKEN"):
        TelegramBot()


def test_patch_traceback_flag_is_read(cfg, monkeypatch):
    import traceback

    from antares_bot.format_exc import format_exception_with_local_vars

    original = traceback.format_exception
    monkeypatch.setattr(cfg.AntaresBotConfig, "PATCH_TRACEBACK", True, raising=False)
    try:
        bot = TelegramBot()
        assert bot._patch_traceback is True
        assert traceback.format_exception is format_exception_with_local_vars
    finally:
        traceback.format_exception = original


# --------------------------------------------------------- exception_handler


@pytest.mark.parametrize(
    "error",
    [
        None,
        NetworkError("x"),
        OSError("x"),
        TimedOut(),
        ConnectionError("x"),
        Conflict("x"),
        RetryAfter(1),
    ],
)
async def test_exception_handler_ignores_transient_errors(
    fake_context, stub_instance, error
):
    ctx = fake_context()
    ctx.error = error
    await exception_handler(None, ctx)
    assert stub_instance.sent == []


async def test_exception_handler_notifies_the_master(fake_context, stub_instance):
    ctx = fake_context()
    ctx.error = ValueError("boom")
    await exception_handler(None, ctx)
    assert len(stub_instance.sent) == 1
    chat_id, text = stub_instance.sent[0]
    assert chat_id == MASTER_ID
    assert "ValueError" in text
    assert "boom" in text


async def test_exception_handler_handles_a_leaked_permission_error(
    make_context, stub_instance
):
    ctx = make_context()
    ctx.error = UserPermissionException()
    with ContextHelper(ctx):
        await exception_handler(None, ctx)
    assert stub_instance.replies == ["Oops, you don't have permission..."]
    assert stub_instance.sent == []


async def test_exception_handler_handles_a_leaked_chat_type_error(
    make_context, stub_instance
):
    ctx = make_context()
    ctx.error = InvalidChatTypeException()
    with ContextHelper(ctx):
        await exception_handler(None, ctx)
    assert stub_instance.replies == ["Cannot be used in this chat type"]


async def test_permission_errors_without_a_context_are_logged(
    fake_context, stub_instance, caplog
):
    ctx = fake_context()
    ctx.error = UserPermissionException()
    with caplog.at_level("ERROR"):
        await exception_handler(None, ctx)
    assert "No context found" in caplog.text
    assert stub_instance.replies == []


async def test_exception_handler_never_raises(fake_context, monkeypatch):
    class Exploding:
        async def send_to(self, *args, **kwargs):
            raise RuntimeError("send failed")

    monkeypatch.setattr(bot_inst, "get_bot_instance", lambda: Exploding())
    ctx = fake_context()
    ctx.error = ValueError("boom")
    await exception_handler(None, ctx)  # must not raise


# ---------------------------------------------------------------- _daily_job


class RecordingModuleDesc:
    def __init__(self, instance):
        self.module_instance = instance
        self.top_name = "rec"


class RecordingModule:
    def __init__(self):
        self.contexts = []

    async def daily_job(self):
        self.contexts.append(get_context())


async def test_daily_job_prunes_expired_callback_data(bot_app, monkeypatch):
    manager = bot_app.callback_manager
    now = time.time()

    monkeypatch.setattr(bot_inst.time, "time", lambda: now - 2 * bot_inst.TIME_IN_A_DAY)
    old_key = manager.set_data("old")
    monkeypatch.setattr(bot_inst.time, "time", lambda: now)
    fresh_key = manager.set_data("fresh")

    await bot_app._daily_job(None)  # type: ignore[arg-type]

    assert manager.peek_data(old_key) is None
    assert manager.peek_data(fresh_key) == "fresh"


async def test_daily_job_runs_modules_without_a_usable_context(
    bot_app, make_context, monkeypatch
):
    module = RecordingModule()
    monkeypatch.setattr(
        bot_app._module_keeper,
        "get_all_enabled_modules",
        lambda: [RecordingModuleDesc(module)],
    )
    with ContextHelper(make_context()):
        await bot_app._daily_job(None)  # type: ignore[arg-type]
    assert len(module.contexts) == 1
    assert isinstance(module.contexts[0], InvalidContext)


# ------------------------------------------------------ remove_job_if_exists


class FakeJob:
    def __init__(self):
        self.removed = False

    def schedule_removal(self):
        self.removed = True


def test_remove_job_if_exists(bot_app, monkeypatch):
    jobs = [FakeJob(), FakeJob()]
    monkeypatch.setattr(bot_app.job_queue, "get_jobs_by_name", lambda name: jobs)
    assert bot_app.remove_job_if_exists("x") is True
    assert all(j.removed for j in jobs)


def test_remove_job_if_exists_without_a_job(bot_app, monkeypatch):
    monkeypatch.setattr(bot_app.job_queue, "get_jobs_by_name", lambda name: [])
    assert bot_app.remove_job_if_exists("x") is False


# -------------------------------------------------------------- get_module


def test_get_module_by_name_and_class(bot_app, monkeypatch):
    sentinel = object()
    monkeypatch.setattr(bot_app._module_keeper, "get_module", lambda name: sentinel)
    monkeypatch.setattr(
        bot_app._module_keeper, "get_module_by_class", lambda kls: sentinel
    )
    assert bot_app.get_module("x") is sentinel
    assert bot_app.get_module(TelegramBot) is sentinel  # type: ignore[arg-type]


# ---------------------------------------------------------- log_stacktrace


def test_get_log_stacktrace_lists_frames(bot_app):
    lines = bot_app._get_log_stacktrace()
    assert lines[0].startswith("[_get_log_stacktrace]")
    assert any('File "' in line for line in lines)


def test_log_stacktrace_never_raises(bot_app, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError

    monkeypatch.setattr(bot_app, "_get_log_stacktrace", boom)
    bot_app.log_stacktrace()  # must not raise


def test_guard_stop(monkeypatch):
    calls = []
    monkeypatch.setattr(
        bot_inst.faulthandler,
        "dump_traceback_later",
        lambda timeout, *, exit: calls.append((timeout, exit)),
    )

    TelegramBot._guard_stop()

    assert calls == [(10, True)]


# ------------------------------------------------------------ custom hooks


def test_custom_hooks_are_stored(bot_app):
    async def task():
        pass

    coro_init = task()
    coro_stop = task()
    try:
        bot_app.custom_post_init(coro_init)
        bot_app.custom_post_stop(coro_stop)
        assert bot_app._custom_post_init_task is coro_init
        assert bot_app._custom_post_stop_task is coro_stop

        bot_app.custom_restart_command("echo hi")
        assert bot_app._custom_restart_command == "echo hi"

        finalize = lambda: None  # noqa: E731
        bot_app.custom_finalize(finalize)
        assert bot_app._custom_finalize_task is finalize
    finally:
        coro_init.close()
        coro_stop.close()
        bot_app._custom_post_init_task = None
        bot_app._custom_post_stop_task = None
        bot_app._custom_restart_command = None
        bot_app._custom_finalize_task = None
