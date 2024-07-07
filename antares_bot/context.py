from typing import TYPE_CHECKING, Any, Dict, Optional, cast

from telegram import Update
from telegram.constants import ChatType
from telegram.ext import Application, CallbackContext, ExtBot

from antares_bot.utils import ObjectDict, get_msg_id, get_reply_to_msg_id


if TYPE_CHECKING:
    from typing import Self


class ChatData:
    def __init__(self) -> None:
        self.rich_data: Dict[int, Any] = ObjectDict()
        """key: message id"""


class UserData:
    pass


class RichCallbackContext(CallbackContext[ExtBot, UserData, ChatData, dict]):
    def __init__(
            self,
            application: Application,
            chat_id: int | None = None,
            user_id: int | None = None
    ):
        super().__init__(application, chat_id, user_id)
        self._last_message_id: Optional[int] = None
        self._reply_to_message_id: Optional[int] = None
        self._update: Optional[Update] = None
        self._type = ""

    @classmethod
    def from_update(cls, update: object, application: "Application") -> "Self":
        """Override from_update to set _message_id."""
        context = super().from_update(update, application)
        if isinstance(update, Update):
            # pylint: disable=protected-access
            context._last_message_id = get_msg_id(update)
            context._reply_to_message_id = get_reply_to_msg_id(update)
            context._update = update
            if update.effective_chat is not None:
                context._type = update.effective_chat.type
            # pylint: enable=protected-access
        return context

    def is_private_chat(self):
        return self._type == ChatType.PRIVATE

    def is_group_chat(self):
        return self._type in [ChatType.GROUP, ChatType.SUPERGROUP]

    def is_channel_message(self):
        return self._type == ChatType.CHANNEL

    def chat_type_str(self):
        return self._type

    def is_callback_query(self):
        return self._update.callback_query is not None

    def get_key(self):
        return (self.chat_id, self.user_id)

    @property
    def user_id(self) -> int:
        return cast(int, self._user_id)

    @property
    def chat_id(self) -> int:
        return cast(int, self._chat_id)

    @property
    def message_id(self) -> int:
        return cast(int, self._last_message_id)

    @property
    def reply_to_message_id(self) -> int:
        return cast(int, self._reply_to_message_id)

    @property
    def type(self) -> str:
        return self._type
