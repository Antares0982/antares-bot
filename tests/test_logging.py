import asyncio
import logging

import pytest

import antares_bot.bot_logging as bl
from antares_bot.bot_logging import (
    GlobalLoggerInstance,
    PikaGlobalLoggerInstance,
    PikaHandler,
    _get_pika_connection_kw,
    _log_start,
    add_pika_log_handler,
    get_logger,
    get_root_logger,
    start_logger,
    stop_logger,
)


# ------------------------------------------------------------------ get_logger


def test_get_logger_prefixes_the_top_name():
    inst = GlobalLoggerInstance.INST
    assert inst is not None
    top = inst.logger_top_name
    assert get_logger("some.module").name == f"{top}.some.module"


def test_get_logger_strips_the_modules_prefix():
    inst = GlobalLoggerInstance.INST
    assert inst is not None
    top = inst.logger_top_name
    assert get_logger("modules.my_mod").name == f"{top}.my_mod"
    # only a leading occurrence is stripped
    assert get_logger("x.modules.y").name == f"{top}.x.modules.y"


def test_get_logger_requires_initialisation():
    GlobalLoggerInstance.INST = None
    with pytest.raises(RuntimeError):
        get_logger("x")
    with pytest.raises(RuntimeError):
        get_root_logger()


def test_get_root_logger_returns_the_configured_logger():
    inst = GlobalLoggerInstance.INST
    assert inst is not None
    assert get_root_logger() is inst.root_logger


# ------------------------------------------------------------------ _log_start


def test_log_start_is_idempotent():
    existing = GlobalLoggerInstance.INST
    assert existing is not None
    assert _log_start("something-else") is existing.root_logger
    assert GlobalLoggerInstance.INST is existing


def test_log_start_without_pika(cfg, monkeypatch):
    monkeypatch.setattr(cfg.AntaresBotConfig, "PIKA_LOGGER_ENABLED", False)
    GlobalLoggerInstance.INST = None
    root = _log_start("test_top")
    inst = GlobalLoggerInstance.INST
    assert type(inst) is GlobalLoggerInstance
    assert inst.pika_enabled is False
    assert root.name == "test_top"
    assert not any(isinstance(h, PikaHandler) for h in root.handlers)


def test_log_start_with_pika_attaches_handlers(cfg, monkeypatch):
    monkeypatch.setattr(cfg.AntaresBotConfig, "PIKA_LOGGER_ENABLED", True)
    GlobalLoggerInstance.INST = None
    root = _log_start("test_top_pika")
    inst = GlobalLoggerInstance.INST
    try:
        assert isinstance(inst, PikaGlobalLoggerInstance)
        assert inst.pika_enabled is True
        assert any(isinstance(h, PikaHandler) for h in root.handlers)
    finally:
        for name in (root.name, "telegram", "apscheduler"):
            logger = logging.getLogger(name)
            for handler in [h for h in logger.handlers if isinstance(h, PikaHandler)]:
                logger.removeHandler(handler)


def test_log_start_falls_back_when_aio_pika_is_missing(cfg, monkeypatch, capsys):
    monkeypatch.setattr(cfg.AntaresBotConfig, "PIKA_LOGGER_ENABLED", None)
    monkeypatch.setattr(bl, "find_spec", lambda name: None)
    GlobalLoggerInstance.INST = None
    _log_start("test_top_nopika")
    inst = GlobalLoggerInstance.INST
    assert inst is not None
    assert inst.pika_enabled is False
    assert "Pika not supported" in capsys.readouterr().err


# ---------------------------------------------------------- add_pika_log_handler


def test_add_pika_log_handler_without_pika(capsys):
    assert add_pika_log_handler("some.logger") is False
    assert "no effect" in capsys.readouterr().out


def test_add_pika_log_handler_requires_initialisation():
    GlobalLoggerInstance.INST = None
    with pytest.raises(RuntimeError):
        add_pika_log_handler("x")


def test_add_pika_log_handler_attaches_to_the_named_logger():
    inst = PikaGlobalLoggerInstance("top", needs_runtime_check=False)
    handler = PikaHandler()
    inst.set_pika_handler(handler)
    GlobalLoggerInstance.INST = inst

    logger = logging.getLogger("some.target.logger")
    try:
        assert add_pika_log_handler(logger) is True
        assert handler in logger.handlers
    finally:
        logger.removeHandler(handler)


# ------------------------------------------------------------------ PikaHandler


class CollectingInstance(PikaGlobalLoggerInstance):
    def __init__(self, top="antares_bot"):
        super().__init__(top, needs_runtime_check=False)
        self.enqueued: list[tuple[str, str]] = []

    def enqueue(self, routing_key, msg):
        self.enqueued.append((routing_key, msg))


def _record(name):
    return logging.LogRecord(name, logging.WARNING, "f.py", 1, "hello", None, None)


def test_pika_handler_builds_the_routing_key():
    inst = CollectingInstance("antares_bot")
    GlobalLoggerInstance.INST = inst
    PikaHandler().emit(_record("mymodule"))
    assert inst.enqueued == [("logging.antares_bot.mymodule", "hello")]


def test_pika_handler_does_not_double_prefix():
    inst = CollectingInstance("antares_bot")
    GlobalLoggerInstance.INST = inst
    PikaHandler().emit(_record("antares_bot.mymodule"))
    assert inst.enqueued == [("logging.antares_bot.mymodule", "hello")]


def test_pika_handler_is_silent_without_an_instance():
    GlobalLoggerInstance.INST = None
    PikaHandler().emit(_record("x"))  # must not raise


def test_pika_handler_is_silent_when_pika_is_off():
    GlobalLoggerInstance.INST = GlobalLoggerInstance("top")
    PikaHandler().emit(_record("x"))  # must not raise


def test_pika_handler_repr():
    handler = PikaHandler()
    handler.set_name("named")
    assert "PikaHandler" in repr(handler)
    assert "named" in repr(handler)


# ------------------------------------------------ PikaGlobalLoggerInstance


class FakePublisher(PikaGlobalLoggerInstance):
    def __init__(self):
        super().__init__("top", needs_runtime_check=False)
        self.published: list[tuple[str, str]] = []

    async def _publish(self, routing_key, msg):
        assert isinstance(msg, str)
        self.published.append((routing_key, msg))

    async def _close_channel(self):
        pass


async def test_records_are_buffered_before_start():
    inst = FakePublisher()
    inst.enqueue("k", "one")
    inst.enqueue("k", "two")
    assert list(inst._prestart) == [("k", "one"), ("k", "two")]
    assert inst.published == []


async def test_start_flushes_the_buffer_in_order():
    inst = FakePublisher()
    inst.enqueue("k", "one")
    inst.enqueue("k", "two")
    await inst.start()
    inst.enqueue("k", "three")
    await asyncio.sleep(0)
    await inst.stop()
    assert inst.published == [("k", "one"), ("k", "two"), ("k", "three")]


async def test_stop_drains_the_queue():
    inst = FakePublisher()
    await inst.start()
    for i in range(50):
        inst.enqueue("k", str(i))
    # enqueue() hands off via call_soon_threadsafe; let those callbacks run
    await asyncio.sleep(0)
    await inst.stop()
    assert [msg for _, msg in inst.published] == [str(i) for i in range(50)]
    assert inst._consumer is None


async def test_stop_does_not_drop_records_enqueued_just_before_it():
    """The sentinel must not overtake records whose call_soon_threadsafe
    callback has not run yet -- that is what drops the last log lines before
    shutdown (e.g. the 'Finalize time' warning right before stop_logger())."""
    inst = FakePublisher()
    await inst.start()
    inst.enqueue("k", "last words")
    await inst.stop()
    assert inst.published == [("k", "last words")]


async def test_stop_drains_a_burst_enqueued_just_before_it():
    inst = FakePublisher()
    await inst.start()
    for i in range(20):
        inst.enqueue("k", str(i))
    await inst.stop()
    assert [msg for _, msg in inst.published] == [str(i) for i in range(20)]


async def test_a_failing_publish_does_not_kill_the_consumer():
    class Flaky(FakePublisher):
        async def _publish(self, routing_key, msg):
            if msg == "bad":
                raise RuntimeError("nope")
            self.published.append((routing_key, msg))

    inst = Flaky()
    await inst.start()
    inst.enqueue("k", "bad")
    inst.enqueue("k", "good")
    await asyncio.sleep(0)
    await inst.stop()
    assert inst.published == [("k", "good")]


async def test_a_disabled_instance_drops_records():
    inst = FakePublisher()
    inst._disabled = True
    inst.enqueue("k", "one")
    assert list(inst._prestart) == []


async def test_stop_before_start_is_safe():
    await FakePublisher().stop()  # must not raise


async def test_start_disables_itself_when_the_probe_fails(capsys):
    class Unreachable(PikaGlobalLoggerInstance):
        def __init__(self):
            super().__init__("top", needs_runtime_check=True)

        async def _ensure_channel(self):
            raise RuntimeError("no broker")

    inst = Unreachable()
    inst.enqueue("k", "one")
    await inst.start()
    assert inst._disabled is True
    assert list(inst._prestart) == []
    assert "Pika not supported" in capsys.readouterr().err


# ------------------------------------------------------- start/stop_logger


async def test_start_and_stop_logger_are_noops_without_pika():
    GlobalLoggerInstance.INST = GlobalLoggerInstance("top")
    await start_logger()
    await stop_logger()
    assert GlobalLoggerInstance.INST is None


async def test_stop_logger_without_an_instance():
    GlobalLoggerInstance.INST = None
    await stop_logger()  # must not raise


async def test_start_logger_drives_the_pika_instance():
    inst = FakePublisher()
    GlobalLoggerInstance.INST = inst
    inst.enqueue("k", "one")
    await start_logger()
    await stop_logger()
    assert inst.published == [("k", "one")]
    assert GlobalLoggerInstance.INST is None


# ----------------------------------------------------- _get_pika_connection_kw


def test_pika_connection_kw_is_empty_without_config(cfg, monkeypatch):
    monkeypatch.delattr(cfg.AntaresBotConfig, "PIKA_CONFIG", raising=False)
    assert _get_pika_connection_kw() == {}


def test_pika_connection_kw_is_a_deep_copy(cfg, monkeypatch):
    config = {"host": "example.com", "nested": {"a": 1}}
    monkeypatch.setattr(cfg.AntaresBotConfig, "PIKA_CONFIG", config, raising=False)
    out = _get_pika_connection_kw()
    assert out == config
    out["nested"]["a"] = 2
    assert config["nested"]["a"] == 1
