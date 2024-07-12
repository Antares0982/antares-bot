from typing import TYPE_CHECKING, Optional

from antares_bot.bot_default_cfg import BasicConfig
from antares_bot.context_manager import InvalidContext, get_context
from antares_bot.utils import read_user_cfg


if TYPE_CHECKING:
    from antares_bot.context import RichCallbackContext


def get_default_locale() -> str | None:
    return read_user_cfg(BasicConfig, "LOCALE")


def lang_context():
    try:
        ct = get_context()
        if ct is None or isinstance(ct, InvalidContext):
            return get_default_locale()
    except Exception:
        return get_default_locale()
    return LangContextManager.get_inst().get_user_lang(ct)


def set_lang(_id: int, locale: str):
    # id < 0 -> group, id > 0 -> private
    LangContextManager.get_inst().set_user_lang(_id, locale)


class LangContextManager:
    INST: Optional["LangContextManager"] = None

    def __init__(self) -> None:
        self.user_lang_context: dict[int, str] = dict()

    def get_user_lang(self, ct: "RichCallbackContext") -> str | None:
        return self.user_lang_context.get(ct.user_id, get_default_locale())  # type: ignore

    def set_user_lang(self, _id: int, locale: str):
        self.user_lang_context[_id] = locale

    @classmethod
    def get_inst(cls):
        if cls.INST is None:
            cls.INST = LangContextManager()
        return cls.INST
