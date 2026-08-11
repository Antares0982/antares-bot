import pytest
from telegram import Chat

from antares_bot.permission_check import (
    CheckLevel,
    ConditionLimit,
    PermissionState,
    permission_check,
)


MASTER_ID = 1


@pytest.fixture(autouse=True)
def master(cfg, monkeypatch):
    monkeypatch.setattr(cfg.BasicConfig, "MASTER_ID", MASTER_ID)


def test_condition_limit_values_are_a_bitmask():
    assert ConditionLimit.CHAT.value == (
        ConditionLimit.GROUP.value | ConditionLimit.PRIVATE.value
    )
    assert ConditionLimit.ALL.value == 0xF


@pytest.mark.parametrize(
    "chat_type,limit,expected",
    [
        (Chat.PRIVATE, ConditionLimit.PRIVATE, PermissionState.PASSED),
        (Chat.PRIVATE, ConditionLimit.GROUP, PermissionState.INVALID_CHAT_TYPE),
        (Chat.GROUP, ConditionLimit.GROUP, PermissionState.PASSED),
        (Chat.SUPERGROUP, ConditionLimit.GROUP, PermissionState.PASSED),
        (Chat.GROUP, ConditionLimit.PRIVATE, PermissionState.INVALID_CHAT_TYPE),
        (Chat.CHANNEL, ConditionLimit.CHANNEL, PermissionState.PASSED),
        (Chat.CHANNEL, ConditionLimit.CHAT, PermissionState.IGNORE_CHANNEL),
        (Chat.PRIVATE, ConditionLimit.CHAT, PermissionState.PASSED),
        (Chat.GROUP, ConditionLimit.CHAT, PermissionState.PASSED),
        (Chat.PRIVATE, ConditionLimit.ALL, PermissionState.PASSED),
        (Chat.CHANNEL, ConditionLimit.ALL, PermissionState.PASSED),
    ],
)
def test_chat_type_limits(fake_context, chat_type, limit, expected):
    ctx = fake_context(chat_type, chat_id=MASTER_ID, user_id=MASTER_ID)
    assert permission_check(ctx, CheckLevel.ANY, limit) == expected


def test_master_level_passes_on_chat_id_match(fake_context):
    ctx = fake_context(Chat.GROUP, chat_id=MASTER_ID, user_id=999)
    assert permission_check(ctx, CheckLevel.MASTER) == PermissionState.PASSED


def test_master_level_passes_on_user_id_match(fake_context):
    ctx = fake_context(Chat.GROUP, chat_id=-100, user_id=MASTER_ID)
    assert permission_check(ctx, CheckLevel.MASTER) == PermissionState.PASSED


def test_master_level_rejects_others(fake_context):
    ctx = fake_context(Chat.GROUP, chat_id=-100, user_id=999)
    assert permission_check(ctx, CheckLevel.MASTER) == PermissionState.INVALID_USER


@pytest.mark.parametrize("level", [CheckLevel.ADMIN, CheckLevel.USER, CheckLevel.ANY])
def test_non_master_levels_always_pass(fake_context, level):
    ctx = fake_context(Chat.GROUP, chat_id=-100, user_id=999)
    assert permission_check(ctx, level) == PermissionState.PASSED


def test_chat_type_check_precedes_user_check(fake_context):
    """A non-master in a forbidden chat type reports the chat type, not the user."""
    ctx = fake_context(Chat.GROUP, chat_id=-100, user_id=999)
    assert (
        permission_check(ctx, CheckLevel.MASTER, ConditionLimit.PRIVATE)
        == PermissionState.INVALID_CHAT_TYPE
    )
