import re

import pytest
from telegram import Chat
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from telegram.ext import filters as filters_module

import antares_bot.framework as framework
from antares_bot.context_manager import get_context
from antares_bot.error import (
    InvalidChatTypeException,
    InvalidQueryException,
    UserPermissionException,
)
from antares_bot.framework import (
    CommandCallback,
    ConditionFilter,
    GeneralCallback,
    GeneralCallbackWrapper,
    btn_click_wrapper,
    command_callback_wrapper,
    general_callback_wrapper,
    msg_handle_wrapper,
)


class RecordingReplies:
    """Stands in for ``get_bot_instance()``; records what would be sent."""

    def __init__(self, fail=False):
        self.replies: list[str] = []
        self.fail = fail

    async def reply(self, text, **kwargs):
        if self.fail:
            raise RuntimeError("reply failed")
        self.replies.append(text)
        return 1


@pytest.fixture
def stub_bot(monkeypatch):
    def _install(fail=False):
        stub = RecordingReplies(fail)
        import antares_bot.bot_inst as bot_inst

        monkeypatch.setattr(bot_inst, "get_bot_instance", lambda: stub)
        return stub

    return _install


# --------------------------------------------------------- command callbacks


def test_command_callback_wrapper_bare():
    @command_callback_wrapper
    async def my_command(update, context):
        """doc"""

    assert isinstance(my_command, CommandCallback)
    assert my_command.kwargs["command"] == "my_command"
    assert my_command.kwargs["block"] is False
    assert my_command.kwargs["filters"] is None
    assert my_command.__doc__ == "doc"


def test_command_callback_wrapper_with_arguments():
    flt = filters_module.TEXT

    @command_callback_wrapper(block=True, filters=flt)
    async def other(update, context): ...

    assert other.kwargs["block"] is True
    assert other.kwargs["filters"] is flt


def test_to_handler_builds_a_command_handler():
    @command_callback_wrapper
    async def ping(update, context): ...

    handler = ping.to_handler()
    assert isinstance(handler, CommandHandler)
    assert set(handler.commands) == {"ping"}
    assert handler.callback is ping


def test_repr_mentions_name_and_handler_type():
    @command_callback_wrapper
    async def ping(update, context): ...

    assert "ping" in repr(ping)
    assert "CommandHandler" in repr(ping)


def test_descriptor_binds_the_owning_instance():
    class Mod:
        @command_callback_wrapper
        async def cmd(self, update, context):
            return self

    inst = Mod()
    bound = inst.cmd
    assert bound._instance is inst


async def test_call_passes_the_instance_through(make_context):
    seen = []

    class Mod:
        @command_callback_wrapper
        async def cmd(self, update, context):
            seen.append(self)
            return "ok"

    inst = Mod()
    ct = make_context()
    assert await inst.cmd(None, ct) == "ok"
    assert seen == [inst]


async def test_call_enters_the_context(make_context):
    seen = []

    @command_callback_wrapper
    async def cmd(update, context):
        seen.append(get_context())

    ct = make_context()
    await cmd(None, ct)
    assert seen == [ct]
    assert get_context() is None


# -------------------------------------------------- permission error handling


async def test_permission_exception_triggers_a_reply(make_context, stub_bot):
    stub = stub_bot()

    @command_callback_wrapper
    async def cmd(update, context):
        raise UserPermissionException

    await cmd(None, make_context())
    assert stub.replies == ["Oops, you don't have permission..."]


async def test_invalid_chat_type_reply_includes_the_chat_type(make_context, stub_bot):
    stub = stub_bot()

    @command_callback_wrapper
    async def cmd(update, context):
        raise InvalidChatTypeException

    await cmd(None, make_context(chat_type=Chat.GROUP))
    assert stub.replies == ["Cannot be used in this chat type"]


async def test_channel_messages_get_no_permission_reply(make_context, stub_bot):
    stub = stub_bot()

    @command_callback_wrapper
    async def cmd(update, context):
        raise UserPermissionException

    await cmd(None, make_context(chat_type=Chat.CHANNEL))
    assert stub.replies == []


async def test_non_command_handlers_do_not_reply(make_context, stub_bot):
    stub = stub_bot()

    @general_callback_wrapper(MessageHandler, filters=None)
    async def handler(update, context):
        raise UserPermissionException

    await handler(None, make_context())
    assert stub.replies == []


async def test_a_failing_reply_does_not_escape(make_context, stub_bot):
    stub_bot(fail=True)

    @command_callback_wrapper
    async def cmd(update, context):
        raise UserPermissionException

    await cmd(None, make_context())  # must not raise


async def test_invalid_query_exception_is_swallowed(make_context, make_update):
    @command_callback_wrapper
    async def cmd(update, context):
        raise InvalidQueryException

    update = make_update(callback_query=True)
    await cmd(update, make_context(update))  # must not raise


async def test_other_exceptions_propagate(make_context):
    @command_callback_wrapper
    async def cmd(update, context):
        raise ValueError("boom")

    with pytest.raises(ValueError):
        await cmd(None, make_context())


# ------------------------------------------------------------ general wrappers


def test_general_callback_wrapper_rejects_a_non_callable_handler_type():
    with pytest.raises(TypeError):
        general_callback_wrapper("not-a-type")


def test_general_callback_wrapper_defaults_block():
    wrapper = general_callback_wrapper(MessageHandler, filters=None)
    assert wrapper.kwargs["block"] is False


def test_pre_executer_kwarg_is_consumed(make_context):
    """The kwarg is popped, not forwarded to the PTB handler constructor."""

    async def pre(update, context): ...

    @general_callback_wrapper(MessageHandler, filters=None, pre_executer=pre)
    async def handler(update, context): ...

    assert GeneralCallback.PRE_EXUCUTER_KW not in handler.kwargs
    handler.to_handler()  # would raise TypeError if the kwarg leaked


async def test_pre_executer_runs_before_the_callback(make_context):
    order = []

    async def pre(update, context):
        order.append("pre")

    @general_callback_wrapper(MessageHandler, filters=None, pre_executer=pre)
    async def handler(update, context):
        order.append("body")

    await handler(None, make_context())
    assert order == ["pre", "body"]


# ------------------------------------------------------------ btn_click_wrapper


def test_btn_click_wrapper_anchors_a_string_pattern():
    @btn_click_wrapper("mykey")
    async def on_click(update, context): ...

    assert on_click.kwargs["pattern"] == re.compile("^mykey")
    handler = on_click.to_handler()
    assert isinstance(handler, CallbackQueryHandler)


def test_btn_click_wrapper_keeps_a_compiled_pattern():
    pattern = re.compile("abc")

    @btn_click_wrapper(pattern)
    async def on_click(update, context): ...

    assert on_click.kwargs["pattern"] is pattern


def test_btn_click_wrapper_installs_the_answering_pre_executer():
    wrapper = btn_click_wrapper("k")
    assert (
        wrapper.kwargs[GeneralCallback.PRE_EXUCUTER_KW] is framework._btn_pre_executer
    )


async def test_btn_click_pre_executer_answers_the_query(
    make_update, make_context, monkeypatch
):
    from telegram import CallbackQuery

    answered = []

    async def fake_answer(self, *args, **kwargs):
        answered.append(self.id)

    monkeypatch.setattr(CallbackQuery, "answer", fake_answer)

    @btn_click_wrapper("k")
    async def on_click(update, context): ...

    update = make_update(callback_query=True)
    await on_click(update, make_context(update))
    assert answered == ["q1"]


async def test_btn_pre_executer_ignores_an_update_without_a_query(
    make_update, make_context
):
    """A pattern-less btn_click_wrapper also matches game callback queries."""
    update = make_update()
    await framework._btn_pre_executer(update, make_context(update))  # must not raise


async def test_btn_pre_executer_survives_a_failing_answer(
    make_update, make_context, monkeypatch
):
    """Answering is cosmetic: a stale query must not take the handler down."""
    from telegram import CallbackQuery
    from telegram.error import BadRequest

    async def fake_answer(self, *args, **kwargs):
        raise BadRequest("Query is too old and response timeout expired")

    monkeypatch.setattr(CallbackQuery, "answer", fake_answer)
    ran = []

    @btn_click_wrapper("k")
    async def on_click(update, context):
        ran.append(True)

    update = make_update(callback_query=True)
    await on_click(update, make_context(update))
    assert ran == [True]


# ------------------------------------------------------------ msg_handle_wrapper


def test_msg_handle_wrapper_bare():
    @msg_handle_wrapper
    async def on_msg(update, context): ...

    assert isinstance(on_msg, GeneralCallback)
    assert isinstance(on_msg.to_handler(), MessageHandler)


def test_msg_handle_wrapper_with_a_ptb_filter():
    wrapper = msg_handle_wrapper(filters=filters_module.TEXT)
    assert isinstance(wrapper, GeneralCallbackWrapper)
    assert wrapper.kwargs["filters"] is filters_module.TEXT


def test_msg_handle_wrapper_wraps_a_plain_callable_filter():
    wrapper = msg_handle_wrapper(filters=lambda update: True)
    assert isinstance(wrapper.kwargs["filters"], ConditionFilter)


def test_condition_filter_delegates():
    calls = []

    def condition(update):
        calls.append(update)
        return update == "yes"

    flt = ConditionFilter(condition)
    assert flt.check_update("yes") is True
    assert flt.check_update("no") is False
    assert calls == ["yes", "no"]


def test_photo_handle_wrapper_is_a_ready_made_wrapper():
    assert isinstance(framework.photo_handle_wrapper, GeneralCallbackWrapper)

    @framework.photo_handle_wrapper
    async def on_photo(update, context): ...

    assert isinstance(on_photo.to_handler(), MessageHandler)
