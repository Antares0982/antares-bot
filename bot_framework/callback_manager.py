import bisect
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, Generic, Iterable, List, Optional, Tuple, TypeVar, Union, cast

from telegram import InlineKeyboardButton

from bot_framework.utils import flatten_button


if TYPE_CHECKING:
    from telegram import InlineKeyboardMarkup

_DataType = TypeVar("_DataType")


class CallbackHistoryManager:
    __slots__ = ("history_queue")

    def __init__(self) -> None:
        self.history_queue: List[Tuple[float, int]] = []

    def enqueue(self, key: int) -> None:
        self.history_queue.append((time.time(), key))

    def pop_before_keys(self, before: float):
        history_queue = self.history_queue
        idx = bisect.bisect_left(history_queue, (before, 0))
        if idx > 0:
            self.history_queue = history_queue[idx:]
        yield from (k for _, k in history_queue[:idx])


class CallbackDataManager:
    __slots__ = ("id", "_dict", "history")

    def __init__(self) -> None:
        self.id = 0
        self._dict: Dict[int, Any] = {}
        self.history = CallbackHistoryManager()

    def set_data(self, data=None) -> str:
        self._dict[self.id] = data
        self.history.enqueue(self.id)
        self.id += 1
        return str(self.id - 1)

    def pop_data(self, _id: Union[str, int]) -> Any:
        n_id = int(_id)
        return self._dict.pop(n_id, None)

    def peek_data(self, _id: Union[str, int]) -> Any:
        n_id = int(_id)
        return self._dict.get(n_id, None)

    def modify_data(self, _id: Union[str, int], data: Any) -> None:
        n_id = int(_id)
        self._dict[n_id] = data


class PersistKeyboards(Generic[_DataType]):
    """
    Parameter of repr_cb: idx, cb_data_key, data

    The normal usage is like:
    * construct with callback data manager.
    * call `store_data()` to store all data into self.
    * call `setup()` by the key returned from last step, and also the repr_cb, which is used to generate the text of buttons.
    * call `get()` to get the InlineKeyboardMarkup.

    When the data is retrieved:
    * the type of data is `Tuple[_DataType, PersistKeyboards[_DataType]]`.
    * the index can be retrieved by calling `idx()`.
    """

    def __init__(self, cb_manager: CallbackDataManager) -> None:
        self.cb_data_keys: List[str] = []
        self.repr_cb: Optional[Callable[[int, str, _DataType], str]] = None
        self.cb_manager = cb_manager
        self._idx_map: Dict[str, int] = dict()

    def get(self, pattern_key: str, button_in_row: int) -> Optional["InlineKeyboardMarkup"]:
        if len(self.cb_data_keys) == 0:
            return None
        return flatten_button(self._to_buttons(pattern_key), button_in_row)

    def _to_buttons(self, pattern_key: str) -> List[InlineKeyboardButton]:
        return [InlineKeyboardButton(self._get_text(i), callback_data=f"{pattern_key}:{k}") for i, k in enumerate(self.cb_data_keys)]

    def setup(self, cb_data_keys: List[str], repr_cb: Optional[Callable[[int, str, _DataType], str]] = None):
        self.cb_data_keys = cb_data_keys
        self.repr_cb = repr_cb
        for i, k in enumerate(cb_data_keys):
            self._idx_map[k] = i

    def modify_data(self, cb_data_key: str, data: _DataType) -> None:
        idx = self.idx(cb_data_key)
        self.modify_data_by_index(idx, data)

    def modify_data_by_index(self, idx: int, data: _DataType) -> None:
        cb_data_key = self.cb_data_keys[idx]
        self.cb_manager.modify_data(cb_data_key, (data, self))

    def _get_text(self, idx: int) -> str:
        if self.repr_cb is None:
            return str(idx)
        cb_data_key = self.cb_data_keys[idx]
        data: _DataType = self.cb_manager.peek_data(cb_data_key)[0]
        return self.repr_cb(idx, cb_data_key, data)

    def idx(self, cb_data_key: str) -> int:
        return self._idx_map[cb_data_key]

    def store_data(self, data: _DataType) -> str:
        return self.cb_manager.set_data((data, self))

    def clean(self) -> None:
        """
        clean all refs in callback manager when the keyboard is no longer used
        """
        for k in self.cb_data_keys:
            self.cb_manager.pop_data(k)
        self.cb_data_keys = []
        self._idx_map.clear()
        self.repr_cb = None

    def __len__(self) -> int:
        return len(self.cb_data_keys)
