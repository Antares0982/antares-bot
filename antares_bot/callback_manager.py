import bisect
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, Generic, Iterable, List, Optional, Tuple, TypeVar, Union

from telegram import InlineKeyboardButton

from antares_bot.utils import flatten_button


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
        """
        store data and return the key to retrieve it later.
        the key is a string of int.
        """
        if data is not None:
            self._dict[self.id] = data
            self.history.enqueue(self.id)
        self.id += 1
        return str(self.id - 1)

    def pop_data(self, _id: Union[str, int]) -> Any:
        """
        pop the data by the key.
        """
        n_id = int(_id)
        return self._dict.pop(n_id, None)

    def peek_data(self, _id: Union[str, int]) -> Any:
        """
        peek the data by the key.
        """
        n_id = int(_id)
        return self._dict.get(n_id, None)

    def modify_data(self, _id: Union[str, int], data: Any) -> None:
        """
        modify the data by the key.
        """
        n_id = int(_id)
        if data is not None:
            self._dict[n_id] = data
        else:
            self._dict.pop(n_id, None)


class PersistKeyboards(Generic[_DataType]):
    """
    Parameter of repr_cb: idx, cb_data_key, data

    The normal usage is like:
    * construct with callback data manager.
    * call `setup_use_data()` to store all data into self, and also the repr_cb, which is used to generate the text of buttons. If you want to customize, you can split this method into two steps: `store_data()`, `setup_use_keys()`.
    * call `get_reply_markup()` to get the InlineKeyboardMarkup.

    When the data is retrieved:
    * the type of data is `Tuple[_DataType, PersistKeyboards[_DataType]]`.
    * the index can be retrieved by calling `self.idx(get_cb_data_key)`, where `get_cb_data_key = bot_module._get_cb_data_key(query)`.
    """

    def __init__(self, cb_manager: CallbackDataManager) -> None:
        self.cb_data_keys: List[str] = []
        self.repr_cb: Optional[Callable[[int, str, _DataType], str]] = None
        self.cb_manager = cb_manager
        self._idx_map: Dict[str, int] = dict()

    def get_reply_markup(self, pattern_key: str, button_in_row: int) -> Optional["InlineKeyboardMarkup"]:
        """
        get the InlineKeyboardMarkup. return `None` if no callback data keys are set.
        """
        if len(self.cb_data_keys) == 0:
            return None
        return flatten_button(self._to_buttons(pattern_key), button_in_row)

    def _to_buttons(self, pattern_key: str) -> List[InlineKeyboardButton]:
        return [InlineKeyboardButton(self._get_text(i), callback_data=f"{pattern_key}:{k}") for i, k in enumerate(self.cb_data_keys)]

    def setup_use_data(self, data_list: Iterable[_DataType], repr_cb: Optional[Callable[[int, str, _DataType], str]] = None):
        """
        setting up the keyboard.
        store all callback data into callback manager, store corresponding keys into persist keyboard, and set the `repr_cb` for formatting the button text.

        Parameter of repr_cb: `idx`, `cb_data_key`, `data`.
        """
        cb_data_keys: List[str] = []
        for data in data_list:
            cb_data_keys.append(self.store_data(data))
        self.setup_use_keys(cb_data_keys, repr_cb)

    def setup_use_keys(self, cb_data_keys: List[str], repr_cb: Optional[Callable[[int, str, _DataType], str]] = None):
        """
        setting up the keyboard.
        store all callback data keys into persist keyboard, and set the `repr_cb` for formatting the button text.

        Parameter of repr_cb: `idx`, `cb_data_key`, `data`.
        """
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

    def get_data_by_index(self, idx: int) -> _DataType:
        cb_data_key = self.cb_data_keys[idx]
        data: _DataType = self.cb_manager.peek_data(cb_data_key)[0]
        return data

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
