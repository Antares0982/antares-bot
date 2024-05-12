from typing import TYPE_CHECKING, Optional

from antares_bot.context_manager import get_context
from bot_cfg import BasicConfig


if TYPE_CHECKING:
    from antares_bot.context import RichCallbackContext


def lang_context():
    try:
        ct = get_context()
        if ct is None:
            return BasicConfig.LOCALE
    except:
        return BasicConfig.LOCALE
    return LangContextManager.get_inst().get_user_lang(ct)


def set_lang(_id: int, locale: str):
    # id < 0 -> group, id > 0 -> private
    LangContextManager.get_inst().set_user_lang(_id, locale)

# TODO SQLITE


class LangContextManager:
    INST: Optional["LangContextManager"] = None

    def __init__(self) -> None:
        self.user_lang_context = dict()

    def get_user_lang(self, ct: "RichCallbackContext") -> str:
        ans = None
        if ct.is_group_chat():
            ans = self.user_lang_context.get(ct.chat_id)
        if ans is None:
            ans = self.user_lang_context.get(ct.user_id, BasicConfig.LOCALE)
        return ans

    def set_user_lang(self, _id: int, locale: str):
        self.user_lang_context[_id] = locale

    @classmethod
    def get_inst(cls):
        if cls.INST is None:
            cls.INST = LangContextManager()
        return cls.INST
