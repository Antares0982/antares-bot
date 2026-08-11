import pytest
from telegram import Chat, InlineKeyboardButton

from antares_bot.bot_default_cfg import AntaresBotConfig
from antares_bot.utils import (
    ChatMessage,
    ObjectDict,
    flatten_button,
    get_chat_id,
    get_from_id,
    get_msg_id,
    get_reply_to_msg_id,
    is_channel,
    is_group,
    is_private,
    markdown_escape,
    markdown_v2_escape,
    merge_dicts,
    systemd_service_info,
)


# ------------------------------------------------------------------ ObjectDict


def test_object_dict_attribute_and_item_access_are_the_same_store():
    d = ObjectDict()
    d.a = 1
    assert d["a"] == 1
    d["b"] = 2
    assert d.b == 2


def test_object_dict_missing_attribute_is_none():
    assert ObjectDict().nope is None


# ----------------------------------------------------------------- ChatMessage


def test_chat_message_equality_and_hash():
    a = ChatMessage(1, 2)
    b = ChatMessage(1, 2)
    c = ChatMessage(1, 3)
    assert a == b
    assert hash(a) == hash(b)
    assert a != c
    assert len({a, b, c}) == 2


def test_chat_message_not_equal_to_other_types():
    assert ChatMessage(1, 2) != "1 2"
    assert ChatMessage(1, 2) != object()


def test_chat_message_str():
    assert str(ChatMessage(1, 2)) == "1 2"


# --------------------------------------------------------------- flatten_button


def _buttons(n):
    return [InlineKeyboardButton(str(i), callback_data=str(i)) for i in range(n)]


@pytest.mark.parametrize(
    "count,per_row,expected_rows",
    [(6, 3, [3, 3]), (7, 3, [3, 3, 1]), (2, 5, [2]), (0, 3, [])],
)
def test_flatten_button_rows(count, per_row, expected_rows):
    markup = flatten_button(_buttons(count), per_row)
    assert [len(row) for row in markup.inline_keyboard] == expected_rows


# --------------------------------------------------------------------- escaping


def test_markdown_v2_escape_covers_every_special_char():
    for c in "_*[]()~`>#+-=|{}.!":
        assert markdown_v2_escape(c) == "\\" + c
    assert markdown_v2_escape("a_b") == "a\\_b"
    assert markdown_v2_escape("plain") == "plain"


def test_markdown_escape_covers_only_legacy_specials():
    assert markdown_escape("`*_[") == "\\`\\*\\_\\["
    # not special in legacy markdown
    assert markdown_escape("a.b-c!") == "a.b-c!"


# ------------------------------------------------------------------ merge_dicts


def test_merge_dicts_is_recursive():
    a = {"x": {"y": 1, "z": 2}, "k": 1}
    b = {"x": {"y": 9}, "n": 3}
    assert merge_dicts(a, b) == {"x": {"y": 9, "z": 2}, "k": 1, "n": 3}


def test_merge_dicts_does_not_mutate_inputs():
    a = {"x": {"y": 1}}
    b = {"x": {"y": 2}}
    merge_dicts(a, b)
    assert a == {"x": {"y": 1}}
    assert b == {"x": {"y": 2}}


def test_merge_dicts_non_dict_replaces_dict():
    assert merge_dicts({"x": {"y": 1}}, {"x": 5}) == {"x": 5}
    assert merge_dicts({"x": 5}, {"x": {"y": 1}}) == {"x": {"y": 1}}


# ----------------------------------------------------------- update accessors


def test_get_ids_from_message_update(make_update):
    update = make_update(msg_id=11, user_id=7)
    assert get_from_id(update) == 7
    assert get_chat_id(update) == 7
    assert get_msg_id(update) == 11
    assert get_reply_to_msg_id(update) is None


def test_get_ids_from_reply(make_update):
    update = make_update(msg_id=11, reply_to_msg_id=3)
    assert get_reply_to_msg_id(update) == 3


def test_get_ids_from_callback_query(make_update):
    update = make_update(callback_query=True, msg_id=11, user_id=7)
    assert get_from_id(update) == 7
    assert get_msg_id(update) == 11
    assert get_chat_id(update) == 7


def test_get_ids_from_callback_query_reply(make_update):
    update = make_update(callback_query=True, reply_to_msg_id=4)
    assert get_reply_to_msg_id(update) == 4


@pytest.mark.parametrize("kind", ["channel_post", "edited_channel_post"])
def test_get_ids_from_channel_posts(make_update, kind):
    update = make_update(Chat.CHANNEL, kind=kind, msg_id=21, user_id=7)
    assert get_from_id(update) == 7
    assert get_msg_id(update) == 21
    update = make_update(Chat.CHANNEL, kind=kind, reply_to_msg_id=5)
    assert get_reply_to_msg_id(update) == 5


def test_get_ids_on_empty_update():
    from telegram import Update

    empty = Update(update_id=1)
    assert get_from_id(empty) is None
    assert get_chat_id(empty) is None
    assert get_msg_id(empty) is None
    assert get_reply_to_msg_id(empty) is None


@pytest.mark.parametrize(
    "chat_type,private,group,channel",
    [
        (Chat.PRIVATE, True, False, False),
        (Chat.GROUP, False, True, False),
        (Chat.SUPERGROUP, False, True, False),
        (Chat.CHANNEL, False, False, True),
    ],
)
def test_chat_type_predicates(make_update, chat_type, private, group, channel):
    update = make_update(chat_type)
    assert is_private(update) is private
    assert is_group(update) is group
    assert is_channel(update) is channel


# ------------------------------------------------------------ systemd_service_info


def test_systemd_service_info_unset(cfg, monkeypatch):
    monkeypatch.delattr(cfg.AntaresBotConfig, "SYSTEMD_SERVICE_NAME", raising=False)
    assert systemd_service_info() == (None, None)


def test_systemd_service_info_set(cfg, monkeypatch):
    monkeypatch.setattr(
        cfg.AntaresBotConfig, "SYSTEMD_SERVICE_NAME", "my.service", raising=False
    )
    name, is_root = systemd_service_info()
    assert name == "my.service"
    assert isinstance(is_root, bool)


def test_read_user_cfg_reflects_live_module_state(cfg, monkeypatch):
    from antares_bot.utils import read_user_cfg

    monkeypatch.setattr(cfg.AntaresBotConfig, "SOME_KEY", 7, raising=False)
    assert read_user_cfg(AntaresBotConfig, "SOME_KEY") == 7
