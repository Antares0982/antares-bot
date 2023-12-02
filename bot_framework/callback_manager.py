from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Union

from bot_framework.utils import flatten_button


if TYPE_CHECKING:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class CallbackDataManager:
    __slots__ = ("id", "_dict")

    def __init__(self) -> None:
        self.id = 0
        self._dict: Dict[int, Any] = {}

    def set_data(self, data=None) -> str:
        self._dict[self.id] = data
        self.id += 1
        return str(self.id - 1)

    def get_data(self, _id: Union[str, int]) -> Any:
        n_id = int(_id)
        return self._dict.pop(n_id, None)

    def peek_data(self, _id: Union[str, int]) -> Any:
        n_id = int(_id)
        return self._dict.get(n_id, None)


class KeyboardStateManager:
    STATE_DEFAULT = 0

    def __init__(self, callback_manager: CallbackDataManager) -> None:
        # cb key -> state
        self.callback_manager = callback_manager
        self.data_states: Dict[str, int] = {}

    def set_refs(self, data_keys: Iterable[str]):
        for k in data_keys:
            self.data_states[k] = self.STATE_DEFAULT

    def clear_refs(self):
        for k in self.data_states.keys():
            self.callback_manager.get_data(k)
        self.data_states = {}

    def ref_keys(self):
        yield from self.data_states.keys()

    def get_markup(self, btn_per_row: int) -> Optional["InlineKeyboardMarkup"]:
        btns = self.get_markup_buttons()
        if len(btns) == 0:
            return None
        return flatten_button(btns, btn_per_row)

    def fix(self, key: str, new_key: str, additional_data: Optional[Any] = None):
        raise NotImplementedError

    def get_markup_buttons(self) -> List["InlineKeyboardButton"]:
        raise NotImplementedError
