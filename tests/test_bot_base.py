import pytest
from telegram import Chat, InlineKeyboardButton
from telegram.error import TelegramError

from antares_bot.bot_base import TelegramBotBase
from antares_bot.context_manager import ContextHelper
from antares_bot.error import (
    IgnoreChannelUpdateException,
    InvalidChatTypeException,
    UserPermissionException,
)
from antares_bot.permission_check import CheckLevel, ConditionLimit, PermissionState


MASTER_ID = 1


@pytest.fixture(autouse=True)
def master(cfg, monkeypatch):
    monkeypatch.setattr(cfg.BasicConfig, "MASTER_ID", MASTER_ID)


# ------------------------------------------------------------- _check_raise


def test_check_raise_passes_silently():
    assert TelegramBotBase._check_raise(PermissionState.PASSED) is None


@pytest.mark.parametrize(
    "state,exc",
    [
        (PermissionState.INVALID_USER, UserPermissionException),
        (PermissionState.INVALID_CHAT_TYPE, InvalidChatTypeException),
        (PermissionState.IGNORE_CHANNEL, IgnoreChannelUpdateException),
    ],
)
def test_check_raise_maps_states_to_exceptions(state, exc):
    with pytest.raises(exc):
        TelegramBotBase._check_raise(state)


def test_check_uses_the_current_context(make_context):
    with ContextHelper(make_context(user_id=MASTER_ID)):
        assert TelegramBotBase.check(CheckLevel.MASTER) is None


def test_check_raises_for_a_non_master(make_context):
    with ContextHelper(make_context(user_id=999, chat_id=-100, chat_type=Chat.GROUP)):
        with pytest.raises(UserPermissionException):
            TelegramBotBase.check(CheckLevel.MASTER)


def test_check_raises_for_a_wrong_chat_type(make_context):
    with ContextHelper(make_context(chat_type=Chat.GROUP, user_id=MASTER_ID)):
        with pytest.raises(InvalidChatTypeException):
            TelegramBotBase.check(CheckLevel.MASTER, ConditionLimit.PRIVATE)


# ------------------------------------------------------------- context access


def test_peek_context_is_none_outside_a_handler():
    assert TelegramBotBase.peek_context() is None


def test_get_context_raises_outside_a_handler():
    with pytest.raises(RuntimeError):
        TelegramBotBase.get_context()


def test_get_context_inside_a_handler(make_context):
    ct = make_context()
    with ContextHelper(ct):
        assert TelegramBotBase.get_context() is ct


# ------------------------------------------------------------------- master


def test_get_master_id():
    assert TelegramBotBase.get_master_id() == MASTER_ID


def test_is_master_by_user_id(fake_context):
    assert TelegramBotBase.is_master(fake_context(chat_id=-100, user_id=MASTER_ID))


def test_is_master_by_chat_id(fake_context):
    assert TelegramBotBase.is_master(fake_context(chat_id=MASTER_ID, user_id=999))


def test_is_master_rejects_others(fake_context):
    assert not TelegramBotBase.is_master(fake_context(chat_id=-100, user_id=999))


def test_is_master_uses_the_current_context(make_context):
    with ContextHelper(make_context(user_id=MASTER_ID)):
        assert TelegramBotBase.is_master()


# --------------------------------------------- get_message_after_command


@pytest.mark.parametrize(
    "text,expected",
    [
        ("/exec print(1)", "print(1)"),
        ("/exec   spaced   out  ", "spaced   out"),
        ("/exec", ""),
        ("/exec@my_bot arg", "arg"),
        ("  /exec arg  ", "arg"),
        ("/exec line1\nline2", "line1\nline2"),
    ],
)
def test_get_message_after_command(make_update, text, expected):
    update = make_update(text=text)
    assert TelegramBotBase.get_message_after_command(update) == expected


# ------------------------------------------------------------------ del_msg


class DeletingBot:
    def __init__(self, *errors):
        self.errors = list(errors)
        self.calls = 0

    async def delete_message(self, **kwargs):
        self.calls += 1
        if self.errors:
            err = self.errors.pop(0)
            if err is not None:
                raise err
        return True


@pytest.fixture
def stub_delete(monkeypatch):
    def _install(*errors):
        bot = DeletingBot(*errors)

        class Inst:
            pass

        Inst.bot = bot  # type: ignore[attr-defined]
        import antares_bot.bot_inst as bot_inst

        monkeypatch.setattr(bot_inst, "get_bot_instance", lambda: Inst())
        return bot

    return _install


async def test_del_msg_succeeds_on_the_first_try(stub_delete):
    bot = stub_delete()
    assert await TelegramBotBase.del_msg(5, 10) is True
    assert bot.calls == 1


async def test_del_msg_retries_then_succeeds(stub_delete):
    bot = stub_delete(TelegramError("x"), TelegramError("x"), None)
    assert await TelegramBotBase.del_msg(5, 10) is True
    assert bot.calls == 3


async def test_del_msg_gives_up(stub_delete):
    bot = stub_delete(*[TelegramError("x")] * 5)
    assert await TelegramBotBase.del_msg(5, 10) is False
    assert bot.calls == 5


async def test_del_msg_respects_max_tries(stub_delete):
    bot = stub_delete(*[TelegramError("x")] * 2)
    assert await TelegramBotBase.del_msg(5, 10, maxTries=2) is False
    assert bot.calls == 2


async def test_del_msg_rejects_a_non_positive_max_tries(stub_delete):
    stub_delete()
    with pytest.raises(ValueError):
        await TelegramBotBase.del_msg(5, 10, maxTries=0)


# ------------------------------------------------------------------- misc


def test_format_inline_keyboard_button():
    btn = TelegramBotBase.format_inline_keyboard_button("text", "key", 7)
    assert isinstance(btn, InlineKeyboardButton)
    assert btn.text == "text"
    assert btn.callback_data == "key:7"


def test_is_debug_level_follows_the_root_logger():
    import logging

    from antares_bot.bot_logging import get_root_logger

    root = get_root_logger()
    old = root.level
    try:
        root.setLevel(logging.DEBUG)
        assert TelegramBotBase._is_debug_level() is True
        root.setLevel(logging.WARNING)
        assert TelegramBotBase._is_debug_level() is False
    finally:
        root.setLevel(old)


def test_bot_id_is_abstract():
    with pytest.raises(NotImplementedError):
        TelegramBotBase().bot_id
