import datetime

import pytest
from telegram import Chat, Message
from telegram.error import (
    BadRequest,
    ChatMigrated,
    Forbidden,
    InvalidToken,
    RetryAfter,
    TelegramError,
)

from antares_bot.bot_method_wrapper import TelegramBotBaseWrapper
from antares_bot.text_process import TEXT_LENGTH_LIMIT


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Retry tests must not actually wait."""
    slept: list[float] = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    import antares_bot.bot_method_wrapper as bmw

    monkeypatch.setattr(bmw.asyncio, "sleep", fake_sleep)
    return slept


def _message(mid=1, text=None):
    msg = Message(
        message_id=mid,
        date=datetime.datetime.now(datetime.timezone.utc),
        chat=Chat(id=5, type=Chat.PRIVATE),
        text=text,
    )
    return msg


class Sender:
    """An awaitable send interface with a scripted error sequence."""

    __name__ = "sender"

    def __init__(self, *errors):
        self.errors = list(errors)
        self.calls: list[dict] = []

    async def __call__(self, **kwargs):
        self.calls.append(dict(kwargs))
        if self.errors:
            err = self.errors.pop(0)
            if err is not None:
                raise err
        return _message(len(self.calls), kwargs.get("text"))


W = TelegramBotBaseWrapper


# ------------------------------------------------------------- _retry_call


@pytest.mark.parametrize(
    "error",
    [
        BadRequest("nope"),
        ChatMigrated(new_chat_id=2),
        Forbidden("nope"),
        InvalidToken(),
    ],
)
async def test_retry_call_exits_fast_on_permanent_errors(error):
    sender = Sender(error)
    with pytest.raises(type(error)):
        await W._retry_call(sender)
    assert len(sender.calls) == 1


async def test_retry_call_retries_transient_errors():
    sender = Sender(TelegramError("temp"), TelegramError("temp"), None)
    message = await W._retry_call(sender)
    assert message.message_id == 3
    assert len(sender.calls) == W.RETRY_TIMES


async def test_retry_call_gives_up_after_retry_times():
    sender = Sender(*[TelegramError("temp")] * W.RETRY_TIMES)
    with pytest.raises(TelegramError):
        await W._retry_call(sender)
    assert len(sender.calls) == W.RETRY_TIMES


async def test_retry_call_honours_retry_after(no_sleep):
    sender = Sender(RetryAfter(12), None)
    await W._retry_call(sender)
    assert no_sleep == [13]


async def test_retry_call_uses_the_default_sleep(no_sleep):
    sender = Sender(TelegramError("temp"), None)
    await W._retry_call(sender)
    assert no_sleep == [W.RETRY_SLEEP_TIME]


# ------------------------- _send_ignore_parsemode_or_replyto_exceptions


async def test_reply_to_message_id_is_dropped_on_a_reply_error():
    sender = Sender(BadRequest("message to reply not found"), None)
    await W._send_ignore_parsemode_or_replyto_exceptions(
        sender, text="hi", reply_to_message_id=99
    )
    assert "reply_to_message_id" in sender.calls[0]
    assert "reply_to_message_id" not in sender.calls[1]


async def test_reply_error_without_a_reply_id_is_raised():
    sender = Sender(BadRequest("message to reply not found"))
    with pytest.raises(BadRequest):
        await W._send_ignore_parsemode_or_replyto_exceptions(sender, text="hi")


async def test_parse_mode_is_dropped_on_a_parse_error():
    sender = Sender(BadRequest("can't parse entities"), None)
    await W._send_ignore_parsemode_or_replyto_exceptions(
        sender, text="hi", parse_mode="MarkdownV2"
    )
    assert sender.calls[0]["parse_mode"] == "MarkdownV2"
    assert "parse_mode" not in sender.calls[1]


async def test_parse_error_without_a_parse_mode_is_raised():
    sender = Sender(BadRequest("can't parse entities"))
    with pytest.raises(BadRequest):
        await W._send_ignore_parsemode_or_replyto_exceptions(sender, text="hi")


async def test_unrelated_bad_request_is_raised():
    sender = Sender(BadRequest("chat not found"))
    with pytest.raises(BadRequest):
        await W._send_ignore_parsemode_or_replyto_exceptions(sender, text="hi")


async def test_no_retry_skips_the_retry_loop():
    sender = Sender(TelegramError("temp"))
    with pytest.raises(TelegramError):
        await W._send_ignore_parsemode_or_replyto_exceptions(
            sender, _no_retry=True, text="hi"
        )
    assert len(sender.calls) == 1


# --------------------------------------------------------- _sequence_send


async def test_sequence_send_puts_reply_markup_on_the_last_message_only():
    sender = Sender()
    markup = object()
    out = [
        m async for m in W._sequence_send(sender, ["a", "b", "c"], reply_markup=markup)
    ]
    assert len(out) == 3
    assert [c.get("reply_markup") for c in sender.calls] == [None, None, markup]


async def test_sequence_send_without_reply_markup():
    sender = Sender()
    [m async for m in W._sequence_send(sender, ["a"])]
    assert "reply_markup" not in sender.calls[0]


# ------------------------------------------------------------------ reply


class Ctx:
    def __init__(self, sender, *, chat_id=5, message_id=10, is_query=False):
        self.chat_id = chat_id
        self.message_id = message_id
        self._is_query = is_query
        self.bot = type("B", (), {"send_message": staticmethod(sender)})()

    def is_callback_query(self):
        return self._is_query


@pytest.fixture
def wrapper_with_context(monkeypatch):
    def _make(**ctx_kwargs):
        sender = Sender()
        ctx = Ctx(sender, **ctx_kwargs)

        class Sub(TelegramBotBaseWrapper):
            @classmethod
            def get_context(cls):
                return ctx

        return Sub, sender

    return _make


async def test_reply_returns_the_last_message_id(wrapper_with_context):
    Sub, sender = wrapper_with_context()
    assert await Sub.reply("hi") == 1
    assert sender.calls[0]["text"] == "hi"
    assert sender.calls[0]["chat_id"] == 5


async def test_reply_variants(wrapper_with_context):
    Sub, _ = wrapper_with_context()
    assert isinstance(await Sub.reply_v2("hi"), list)
    assert isinstance(await Sub.reply_v3("hi"), Message)
    assert isinstance((await Sub.reply_v4("hi"))[0], Message)


async def test_reply_splits_long_text(wrapper_with_context):
    Sub, sender = wrapper_with_context()
    text = "\n".join("line %d" % i for i in range(2000))
    ids = await Sub.reply_v2(text)
    assert len(ids) > 1
    assert len(sender.calls) == len(ids)
    assert all(len(c["text"]) < TEXT_LENGTH_LIMIT * 2 for c in sender.calls)


async def test_reply_with_entities_is_not_split(wrapper_with_context):
    Sub, sender = wrapper_with_context()
    text = "x" * (TEXT_LENGTH_LIMIT * 2)
    await Sub.reply(text, entities=[])
    assert len(sender.calls) == 1
    assert sender.calls[0]["text"] == text


async def test_reply_sets_reply_to_message_id(wrapper_with_context):
    Sub, sender = wrapper_with_context()
    await Sub.reply("hi")
    assert sender.calls[0]["reply_to_message_id"] == 10


async def test_reply_does_not_reply_to_a_callback_query(wrapper_with_context):
    Sub, sender = wrapper_with_context(is_query=True)
    await Sub.reply("hi")
    assert "reply_to_message_id" not in sender.calls[0]


async def test_reply_to_another_chat_does_not_set_reply_to(wrapper_with_context):
    Sub, sender = wrapper_with_context()
    await Sub.reply("hi", chat_id=999)
    assert "reply_to_message_id" not in sender.calls[0]
    assert sender.calls[0]["chat_id"] == 999


async def test_reply_respects_an_explicit_reply_to(wrapper_with_context):
    Sub, sender = wrapper_with_context()
    await Sub.reply("hi", reply_to_message_id=77)
    assert sender.calls[0]["reply_to_message_id"] == 77


async def test_success_and_error_info(wrapper_with_context):
    Sub, sender = wrapper_with_context()
    assert await Sub.success_info("yay") is True
    assert await Sub.error_info("nay") is False
    assert [c["text"] for c in sender.calls] == ["yay", "nay"]


# --------------------------------------------------------------- reply_to


class ReplyTarget:
    id = 33

    def __init__(self):
        self.calls: list[dict] = []

    async def reply_text(self, **kwargs):
        self.calls.append(dict(kwargs))
        return _message(len(self.calls), kwargs.get("text"))


async def test_reply_to_defaults_to_the_target_message():
    target = ReplyTarget()
    await TelegramBotBaseWrapper.reply_to(target, "hi")  # type: ignore[arg-type]
    assert target.calls[0]["reply_to_message_id"] == 33


async def test_reply_to_respects_an_explicit_reply_id():
    target = ReplyTarget()
    await TelegramBotBaseWrapper.reply_to(target, "hi", reply_to_message_id=1)  # type: ignore[arg-type]
    assert target.calls[0]["reply_to_message_id"] == 1


async def test_reply_to_v2_returns_every_id():
    target = ReplyTarget()
    text = "\n".join("line %d" % i for i in range(2000))
    ids = await TelegramBotBaseWrapper.reply_to_v2(target, text)  # type: ignore[arg-type]
    assert len(ids) == len(target.calls) > 1


# ---------------------------------------------------------------- send_to


@pytest.fixture
def stub_instance(monkeypatch):
    sender = Sender()

    class Inst:
        bot = type("B", (), {"send_message": staticmethod(sender)})()

    import antares_bot.bot_inst as bot_inst

    monkeypatch.setattr(bot_inst, "get_bot_instance", lambda: Inst())
    return sender


async def test_send_to_forces_the_chat_id(stub_instance):
    await TelegramBotBaseWrapper.send_to(123, "hi")
    assert stub_instance.calls[0]["chat_id"] == 123
    assert stub_instance.calls[0]["text"] == "hi"


async def test_send_to_v4_returns_every_message(stub_instance):
    text = "\n".join("line %d" % i for i in range(2000))
    messages = await TelegramBotBaseWrapper.send_to_v4(123, text)
    assert len(messages) > 1
    assert all(isinstance(m, Message) for m in messages)
