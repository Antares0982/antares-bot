import pytest
from telegram import Chat

from antares_bot.context_manager import (
    ContextHelper,
    ContextReverseHelper,
    InvalidContext,
    InvalidContextError,
    callback_job_wrapper,
    get_context,
)


# ------------------------------------------------------ RichCallbackContext


def test_from_update_populates_message_ids(make_update, make_context):
    update = make_update(msg_id=11, reply_to_msg_id=3, user_id=7)
    ct = make_context(update)
    assert ct.message_id == 11
    assert ct.reply_to_message_id == 3
    assert ct.chat_id == 7
    assert ct.user_id == 7
    assert ct.get_key() == (7, 7)


@pytest.mark.parametrize(
    "chat_type,private,group,channel",
    [
        (Chat.PRIVATE, True, False, False),
        (Chat.GROUP, False, True, False),
        (Chat.SUPERGROUP, False, True, False),
        (Chat.CHANNEL, False, False, True),
    ],
)
def test_chat_type_predicates(make_context, chat_type, private, group, channel):
    ct = make_context(chat_type=chat_type)
    assert ct.is_private_chat() is private
    assert ct.is_group_chat() is group
    assert ct.is_channel_message() is channel
    assert ct.chat_type_str() == chat_type
    assert ct.type == chat_type


def test_is_callback_query(make_context):
    assert make_context(callback_query=True).is_callback_query() is True
    assert make_context().is_callback_query() is False


def test_from_update_with_non_update_object(bot_app):
    from antares_bot.context import RichCallbackContext

    ct = RichCallbackContext.from_update(object(), bot_app.application)
    assert ct.chat_type_str() == ""
    assert ct.message_id is None


# ----------------------------------------------------------- ContextHelper


def test_context_helper_sets_and_restores(make_context):
    ct = make_context()
    assert get_context() is None
    with ContextHelper(ct):
        assert get_context() is ct
    assert get_context() is None


def test_context_helper_nests(make_context):
    outer = make_context(user_id=1)
    inner = make_context(user_id=2)
    with ContextHelper(outer):
        with ContextHelper(inner):
            assert get_context() is inner
        assert get_context() is outer


def test_context_helper_restores_on_exception(make_context):
    ct = make_context()
    with pytest.raises(ValueError):
        with ContextHelper(ct):
            raise ValueError
    assert get_context() is None


# ---------------------------------------------------- ContextReverseHelper


def test_reverse_helper_installs_invalid_context(make_context):
    ct = make_context()
    with ContextHelper(ct):
        with ContextReverseHelper():
            current = get_context()
            assert isinstance(current, InvalidContext)
            with pytest.raises(InvalidContextError):
                current.chat_id
            with pytest.raises(InvalidContextError):
                current.anything_at_all
        assert get_context() is ct


# --------------------------------------------------- callback_job_wrapper


async def test_callback_job_wrapper_with_explicit_context(make_context):
    ct = make_context()
    seen = []

    @callback_job_wrapper(ct)
    async def job(*args):
        seen.append(get_context())

    assert get_context() is None
    await job()
    assert seen == [ct]
    assert get_context() is None


async def test_callback_job_wrapper_captures_current_context(make_context):
    ct = make_context()
    seen = []

    with ContextHelper(ct):

        async def job(*args):
            seen.append(get_context())

        wrapped = callback_job_wrapper(job)

    # called outside the original frame: the context is still restored
    assert get_context() is None
    await wrapped()
    assert seen == [ct]


async def test_callback_job_wrapper_forwards_arguments(make_context):
    @callback_job_wrapper(make_context())
    async def job(a, b=None):
        return (a, b)

    assert await job(1, b=2) == (1, 2)
