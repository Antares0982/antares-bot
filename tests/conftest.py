"""Shared fixtures.

The synthetic ``bot_cfg`` module below MUST be installed into ``sys.modules``
before anything imports ``antares_bot``: ``antares_bot.init_hooks`` runs
``_hook_cfg()`` at import time, which imports ``bot_cfg`` from the CWD and
``exit(1)``s (after writing a template) when it is missing.  Registering it here
also keeps the suite independent from the developer's local (gitignored)
``bot_cfg.py``.
"""

import sys
import types


class _BasicConfig:
    TOKEN = "123456:ABCdefGHIjklMNOpqrSTUvwxYZ"
    MASTER_ID = 1
    LOCALE = "en"
    DATA_DIR = "data"


class _AntaresBotConfig:
    PIKA_LOGGER_ENABLED = False
    PULL_WHEN_STOP = False


if "bot_cfg" not in sys.modules:
    _cfg_module = types.ModuleType("bot_cfg")
    _cfg_module.BasicConfig = _BasicConfig  # type: ignore[attr-defined]
    _cfg_module.AntaresBotConfig = _AntaresBotConfig  # type: ignore[attr-defined]
    sys.modules["bot_cfg"] = _cfg_module

# ruff: noqa: E402
import datetime

import pytest
from telegram import CallbackQuery, Chat, Message, Update, User

from antares_bot.bot_logging import GlobalLoggerInstance
from antares_bot.callback_manager import CallbackDataManager
from antares_bot.context import RichCallbackContext
from antares_bot.module_base import TelegramBotModuleBase
from antares_bot.multi_lang import context as lang_context_module
from antares_bot.sqlite.manager import DataBasesManager


@pytest.fixture
def cfg():
    """The synthetic ``bot_cfg`` module. Patch attributes on its config classes
    with ``monkeypatch.setattr(..., raising=False)``: ``read_user_cfg`` re-reads
    ``sys.modules["bot_cfg"]`` on every call, so changes take effect at once."""
    return sys.modules["bot_cfg"]


@pytest.fixture(autouse=True)
def reset_singletons():
    """Save/restore every process-global the framework keeps."""
    import antares_bot.bot_inst as bot_inst

    # `__bot_singleton` / `__REGISTERED_BOT_CLASS` live at module level, where
    # no name mangling applies, so these are the real attribute names
    saved = {
        "logger": GlobalLoggerInstance.INST,
        "lang": lang_context_module.LangContextManager.INST,
        "db": DataBasesManager.INST,
        "bot": getattr(bot_inst, "__bot_singleton"),
        "bot_cls": getattr(bot_inst, "__REGISTERED_BOT_CLASS"),
    }
    yield
    GlobalLoggerInstance.INST = saved["logger"]
    lang_context_module.LangContextManager.INST = saved["lang"]
    DataBasesManager.INST = saved["db"]
    setattr(bot_inst, "__bot_singleton", saved["bot"])
    setattr(bot_inst, "__REGISTERED_BOT_CLASS", saved["bot_cls"])


@pytest.fixture(scope="session")
def bot_app():
    """A real, offline PTB ``Application``. Building it performs no network I/O.

    Session-scoped: constructing it is the expensive part and nothing in the
    suite mutates it.
    """
    from antares_bot.bot_inst import TelegramBot

    return TelegramBot()


@pytest.fixture
def make_update(bot_app):
    """Build a ``telegram.Update`` for the given chat type."""

    def _make(
        chat_type: str = Chat.PRIVATE,
        *,
        msg_id: int = 10,
        user_id: int = 7,
        chat_id: int | None = None,
        text: str | None = None,
        reply_to_msg_id: int | None = None,
        reply_to_user_id: int | None = None,
        callback_query: bool = False,
        callback_data: str = "k:0",
        kind: str = "message",
    ) -> Update:
        if chat_id is None:
            chat_id = user_id if chat_type == Chat.PRIVATE else -100
        user = User(id=user_id, first_name="tester", is_bot=False)
        chat = Chat(id=chat_id, type=chat_type)
        now = datetime.datetime.now(datetime.timezone.utc)
        reply_to = None
        if reply_to_msg_id is not None:
            reply_to = Message(
                message_id=reply_to_msg_id,
                date=now,
                chat=chat,
                from_user=(
                    User(id=reply_to_user_id, first_name="other", is_bot=False)
                    if reply_to_user_id is not None
                    else None
                ),
            )
            reply_to.set_bot(bot_app.bot)
        message = Message(
            message_id=msg_id,
            date=now,
            chat=chat,
            from_user=user,
            text=text,
            reply_to_message=reply_to,
        )
        message.set_bot(bot_app.bot)
        if callback_query:
            query = CallbackQuery(
                id="q1",
                from_user=user,
                chat_instance="ci",
                data=callback_data,
                message=message,
            )
            query.set_bot(bot_app.bot)
            return Update(update_id=1, callback_query=query)
        kwargs = {kind: message}
        return Update(update_id=1, **kwargs)  # type: ignore[arg-type]

    return _make


@pytest.fixture
def make_context(bot_app, make_update):
    """Build a real ``RichCallbackContext`` from an ``Update``."""

    def _make(update: Update | None = None, **kwargs) -> RichCallbackContext:
        if update is None:
            update = make_update(**kwargs)
        return RichCallbackContext.from_update(update, bot_app.application)

    return _make


class FakeContext:
    """Minimal stand-in for ``RichCallbackContext``.

    Used where building the whole PTB object graph would only obscure what is
    being asserted (permission matrix, send helpers).
    """

    def __init__(
        self,
        chat_type: str = Chat.PRIVATE,
        *,
        chat_id: int = 5,
        user_id: int = 7,
        message_id: int | None = 10,
        is_query: bool = False,
        bot=None,
    ):
        self._type = chat_type
        self.chat_id = chat_id
        self.user_id = user_id
        self.message_id = message_id
        self._is_query = is_query
        self.bot = bot
        self.error = None
        self.args: list[str] | None = None

    def is_private_chat(self):
        return self._type == Chat.PRIVATE

    def is_group_chat(self):
        return self._type in (Chat.GROUP, Chat.SUPERGROUP)

    def is_channel_message(self):
        return self._type == Chat.CHANNEL

    def is_callback_query(self):
        return self._is_query

    def chat_type_str(self):
        return self._type


@pytest.fixture
def fake_context():
    return FakeContext


class RecordingBot:
    """Records outgoing calls; can be told to raise a scripted error sequence."""

    def __init__(self, errors: list | None = None):
        self.calls: list[tuple[str, dict]] = []
        self.errors = list(errors or [])
        self._next_id = 100

    def _maybe_raise(self):
        if self.errors:
            err = self.errors.pop(0)
            if err is not None:
                raise err

    def _message(self, kwargs) -> Message:
        self._next_id += 1
        chat_id = kwargs.get("chat_id", 5)
        msg = Message(
            message_id=self._next_id,
            date=datetime.datetime.now(datetime.timezone.utc),
            chat=Chat(id=chat_id, type=Chat.PRIVATE),
            text=kwargs.get("text"),
        )
        return msg

    async def send_message(self, **kwargs):
        self.calls.append(("send_message", kwargs))
        self._maybe_raise()
        return self._message(kwargs)

    async def send_photo(self, **kwargs):
        self.calls.append(("send_photo", kwargs))
        self._maybe_raise()
        return self._message(kwargs)

    async def send_document(self, **kwargs):
        self.calls.append(("send_document", kwargs))
        self._maybe_raise()
        return self._message(kwargs)

    async def delete_message(self, **kwargs):
        self.calls.append(("delete_message", kwargs))
        self._maybe_raise()
        return True


@pytest.fixture
def recording_bot():
    return RecordingBot


class DummyParent:
    """Stands in for ``TelegramBot`` when driving ``TelegramBotModuleBase``."""

    def __init__(self):
        self.callback_manager = CallbackDataManager()
        self.callback_key_dict: dict[tuple[int, int], list[str]] = {}
        self.handler_docs: dict[str, str] = {}
        self.job_queue = None
        self.bot_id = 42


@pytest.fixture
def dummy_parent():
    return DummyParent()


@pytest.fixture(autouse=True)
def _reset_module_inst():
    """Modules register themselves on ``cls.INST``; drop stale registrations."""
    yield
    for kls in list(_iter_subclasses(TelegramBotModuleBase)):
        if "INST" in vars(kls):
            delattr(kls, "INST")


def _iter_subclasses(kls):
    for sub in kls.__subclasses__():
        yield sub
        yield from _iter_subclasses(sub)
