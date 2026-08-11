import pytest

from antares_bot.callback_manager import PersistKeyboards
from antares_bot.error import InvalidQueryException
from antares_bot.framework import CallbackBase, command_callback_wrapper
from antares_bot.module_base import TelegramBotModuleBase


class SampleModule(TelegramBotModuleBase):
    def __init__(self, parent):
        super().__init__(parent)
        self.mark_calls = 0

    def mark_handlers(self):
        self.mark_calls += 1
        return [self.ping]

    @command_callback_wrapper
    async def ping(self, update, context):
        """ping - reply pong"""


class FakeQuery:
    def __init__(self, data):
        self.data = data


@pytest.fixture
def module(dummy_parent):
    return SampleModule(dummy_parent)


# ------------------------------------------------------------------ lifecycle


def test_instance_registers_itself(module):
    assert SampleModule.get_inst() is module
    assert SampleModule.INST is module


def test_default_lifecycle_hooks_are_noops(module, bot_app):
    assert module.do_init() is None


async def test_async_lifecycle_hooks_are_noops(module, bot_app):
    assert await module.post_init(bot_app.application) is None
    assert await module.do_stop() is None
    assert await module.daily_job() is None


def test_bot_id_is_delegated_to_the_parent(module, dummy_parent):
    assert module.bot_id == dummy_parent.bot_id


def test_job_queue_is_delegated_to_the_parent(module, dummy_parent):
    assert module.job_queue is dummy_parent.job_queue


def test_collect_handlers_is_cached(module):
    first = module.collect_handlers()
    second = module.collect_handlers()
    assert first is second
    assert module.mark_calls == 1
    assert isinstance(first[0], CallbackBase)


def test_mark_handlers_defaults_to_empty(dummy_parent):
    class Bare(TelegramBotModuleBase):
        pass

    assert Bare(dummy_parent).collect_handlers() == []


def test_cancel_is_a_command_callback(module):
    assert isinstance(module.cancel, CallbackBase)


# -------------------------------------------------------- callback data flow


def test_make_btn_callback_stores_data_and_builds_keys(module, dummy_parent):
    raw_keys, keys = module.make_btn_callback("mykey", ["a", "b"])
    assert keys == [f"mykey:{raw_keys[0]}", f"mykey:{raw_keys[1]}"]
    assert dummy_parent.callback_manager.peek_data(raw_keys[0]) == "a"
    assert dummy_parent.callback_manager.peek_data(raw_keys[1]) == "b"


def test_get_cb_data_key_takes_the_part_after_the_colon(module):
    assert module._get_cb_data_key(FakeQuery("mykey:42")) == "42"


def test_get_btn_callback_data_peeks_by_default(module, dummy_parent):
    raw_keys, keys = module.make_btn_callback("k", ["a"])
    query = FakeQuery(keys[0])
    assert module.get_btn_callback_data(query) == "a"
    # still there
    assert module.get_btn_callback_data(query) == "a"


def test_get_btn_callback_data_can_pop(module, dummy_parent):
    _, keys = module.make_btn_callback("k", ["a"])
    query = FakeQuery(keys[0])
    assert module.get_btn_callback_data(query, pop=True) == "a"
    assert module.get_btn_callback_data(query) is None


async def test_get_btn_callback_data_check_valid_raises(module, monkeypatch):
    invalid = []

    async def on_invalid_query(query):
        invalid.append(query)

    monkeypatch.setattr(module, "on_invalid_query", on_invalid_query)
    query = FakeQuery("k:999")
    with pytest.raises(InvalidQueryException):
        module.get_btn_callback_data(query, check_valid=True)
    # the notification task is scheduled on the running loop
    import asyncio

    await asyncio.sleep(0)
    assert invalid == [query]


def test_get_btn_callback_data_without_check_valid_returns_none(module):
    assert module.get_btn_callback_data(FakeQuery("k:999")) is None


# ------------------------------------------------------------- key caching


def test_cache_and_clean_cb_keys_by_id(module, dummy_parent):
    raw_keys, _ = module.make_btn_callback("k", ["a", "b"])
    module.cache_cb_keys_by_id(5, 10, raw_keys)
    assert dummy_parent.callback_key_dict[(5, 10)] == raw_keys

    module.clean_cb_keys_by_id(5, 10)
    assert (5, 10) not in dummy_parent.callback_key_dict
    assert all(dummy_parent.callback_manager.peek_data(k) is None for k in raw_keys)


def test_clean_cb_keys_for_an_unknown_message_is_a_noop(module):
    module.clean_cb_keys_by_id(1, 1)  # must not raise


def test_cache_and_clean_by_message(module, dummy_parent, make_update):
    message = make_update(msg_id=10, user_id=7).message
    raw_keys, _ = module.make_btn_callback("k", ["a"])
    module.cache_cb_keys_by_message(message, raw_keys)
    assert dummy_parent.callback_key_dict[(7, 10)] == raw_keys
    module.clean_cb_keys_by_message(message)
    assert (7, 10) not in dummy_parent.callback_key_dict


def test_clean_cb_keys_uses_the_context(module, dummy_parent, make_context):
    ct = make_context(msg_id=10, user_id=7)
    module.cache_cb_keys_by_id(ct.chat_id, ct.message_id, ["0"])
    module.clean_cb_keys(ct)
    assert dummy_parent.callback_key_dict == {}


# ------------------------------------------------------- query_at_btn_index


def test_query_at_btn_index(module, dummy_parent):
    kb: PersistKeyboards[str] = PersistKeyboards(dummy_parent.callback_manager)
    kb.setup_use_data(["a", "b", "c"])
    query = FakeQuery(f"pat:{kb.cb_data_keys[2]}")
    assert module.query_at_btn_index(query) == 2
