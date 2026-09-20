import pytest

from antares_bot.callback_manager import (
    CallbackDataManager,
    CallbackHistoryManager,
    PersistKeyboards,
)


# ------------------------------------------------------- CallbackDataManager


def test_set_data_returns_incrementing_string_keys():
    m = CallbackDataManager()
    assert m.set_data("a") == "0"
    assert m.set_data("b") == "1"
    assert m.peek_data("0") == "a"
    assert m.peek_data(1) == "b"


def test_set_data_none_advances_the_id_without_storing():
    m = CallbackDataManager()
    key = m.set_data(None)
    assert key == "0"
    assert m.peek_data(key) is None
    # the id was still consumed, so the next key is distinct
    assert m.set_data("x") == "1"


def test_pop_data_removes_the_entry():
    m = CallbackDataManager()
    key = m.set_data("a")
    assert m.pop_data(key) == "a"
    assert m.pop_data(key) is None
    assert m.peek_data(key) is None


def test_peek_and_pop_accept_int_and_str():
    m = CallbackDataManager()
    key = m.set_data("a")
    assert m.peek_data(int(key)) == "a"
    assert m.pop_data(int(key)) == "a"


def test_modify_data_overwrites_and_none_deletes():
    m = CallbackDataManager()
    key = m.set_data("a")
    m.modify_data(key, "b")
    assert m.peek_data(key) == "b"
    m.modify_data(key, None)
    assert m.peek_data(key) is None


def test_set_data_records_history():
    m = CallbackDataManager()
    m.set_data("a")
    m.set_data(None)  # not recorded
    m.set_data("b")
    assert [k for _, k in m.history.history_queue] == [0, 2]


# ---------------------------------------------------- CallbackHistoryManager


@pytest.fixture
def frozen_time(monkeypatch):
    import antares_bot.callback_manager as cm

    class Clock:
        now = 1000.0

        def __call__(self):
            return self.now

    clock = Clock()
    monkeypatch.setattr(cm.time, "time", clock)
    return clock


def test_pop_before_keys_yields_and_trims(frozen_time):
    h = CallbackHistoryManager()
    h.enqueue(1)
    frozen_time.now = 1010.0
    h.enqueue(2)
    frozen_time.now = 1020.0
    h.enqueue(3)

    assert list(h.pop_before_keys(1015.0)) == [1, 2]
    assert [k for _, k in h.history_queue] == [3]


def test_pop_before_keys_with_nothing_expired_keeps_everything(frozen_time):
    h = CallbackHistoryManager()
    h.enqueue(1)
    assert list(h.pop_before_keys(500.0)) == []
    assert [k for _, k in h.history_queue] == [1]


def test_pop_before_keys_can_drain_all(frozen_time):
    h = CallbackHistoryManager()
    h.enqueue(1)
    h.enqueue(2)
    assert list(h.pop_before_keys(2000.0)) == [1, 2]
    assert h.history_queue == []


# -------------------------------------------------------- PersistKeyboards


def test_persist_keyboards_end_to_end():
    m = CallbackDataManager()
    kb: PersistKeyboards[str] = PersistKeyboards(m)
    kb.setup_use_data(["a", "b", "c"], repr_cb=lambda idx, key, data: f"{idx}-{data}")

    assert len(kb) == 3
    markup = kb.get_reply_markup("pat", 2)
    assert markup is not None
    rows = markup.inline_keyboard
    assert [len(r) for r in rows] == [2, 1]
    assert [b.text for r in rows for b in r] == ["0-a", "1-b", "2-c"]
    assert [b.callback_data for r in rows for b in r] == ["pat:0", "pat:1", "pat:2"]

    # the manager stores (data, keyboard) tuples
    assert m.peek_data("0") == ("a", kb)
    assert kb.idx("1") == 1
    assert kb.get_data_by_index(1) == "b"


def test_persist_keyboards_without_repr_cb_uses_indices():
    m = CallbackDataManager()
    kb: PersistKeyboards[str] = PersistKeyboards(m)
    kb.setup_use_data(["a", "b"])
    markup = kb.get_reply_markup("pat", 5)
    assert markup is not None
    assert [b.text for b in markup.inline_keyboard[0]] == ["0", "1"]


def test_persist_keyboards_empty_has_no_markup():
    kb: PersistKeyboards[str] = PersistKeyboards(CallbackDataManager())
    assert kb.get_reply_markup("pat", 3) is None
    assert len(kb) == 0


def test_persist_keyboards_modify_data():
    m = CallbackDataManager()
    kb: PersistKeyboards[str] = PersistKeyboards(m)
    kb.setup_use_data(["a", "b"])
    kb.modify_data("0", "z")
    assert kb.get_data_by_index(0) == "z"
    kb.modify_data_by_index(1, "y")
    assert kb.get_data_by_index(1) == "y"


def test_persist_keyboards_clean_releases_manager_refs():
    m = CallbackDataManager()
    kb: PersistKeyboards[str] = PersistKeyboards(m)
    kb.setup_use_data(["a", "b"])
    kb.clean()
    assert m.peek_data("0") is None
    assert m.peek_data("1") is None
    assert len(kb) == 0
    assert kb.repr_cb is None
    with pytest.raises(KeyError):
        kb.idx("0")


def test_persist_keyboards_setup_use_keys_reuses_existing_keys():
    m = CallbackDataManager()
    kb: PersistKeyboards[str] = PersistKeyboards(m)
    keys = [kb.store_data("a"), kb.store_data("b")]
    kb.setup_use_keys(keys)
    assert kb.cb_data_keys == keys
    assert kb.idx(keys[1]) == 1
