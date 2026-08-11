import pytest

from antares_bot.basic_language import BasicLanguage
from antares_bot.context_manager import ContextHelper, ContextReverseHelper
from antares_bot.multi_lang import LocaleError, t
from antares_bot.multi_lang import context as lang_ctx
from antares_bot.multi_lang.context import (
    LangContextManager,
    get_default_locale,
    lang_context,
    set_lang,
)


D = {"en": "hello", "zh-CN": "你好"}


@pytest.fixture(autouse=True)
def fresh_lang_manager():
    LangContextManager.INST = None
    yield
    LangContextManager.INST = None


@pytest.fixture(autouse=True)
def clear_warn_cache():
    import antares_bot.multi_lang as ml

    ml._CACHE_LOGGED.clear()
    yield
    ml._CACHE_LOGGED.clear()


# ---------------------------------------------------------------------- t()


def test_t_uses_explicit_locale():
    assert t(D, "zh-CN") == "你好"
    assert t(D, "en") == "hello"


def test_t_raises_for_an_unknown_explicit_locale():
    with pytest.raises(LocaleError):
        t(D, "fr")


def test_t_falls_back_to_the_default_locale(cfg, monkeypatch):
    monkeypatch.setattr(cfg.BasicConfig, "LOCALE", "zh-CN")
    assert t(D) == "你好"


def test_t_falls_back_to_the_first_value(cfg, monkeypatch):
    monkeypatch.setattr(cfg.BasicConfig, "LOCALE", "fr")
    assert t(D) == "hello"


def test_t_warns_only_once_per_dict_and_locale(cfg, monkeypatch, caplog):
    import antares_bot.multi_lang as ml

    monkeypatch.setattr(cfg.BasicConfig, "LOCALE", "fr")
    with caplog.at_level("WARNING", logger=ml._LOGGER.name):
        t(D)
        t(D)
    assert len(caplog.records) == 1
    assert len(ml._CACHE_LOGGED) == 1


def test_t_single_entry_dict_never_raises(cfg, monkeypatch):
    monkeypatch.setattr(cfg.BasicConfig, "LOCALE", "fr")
    assert t({"de": "hallo"}) == "hallo"


# ------------------------------------------------------------ lang_context()


def test_get_default_locale_reads_config(cfg, monkeypatch):
    monkeypatch.setattr(cfg.BasicConfig, "LOCALE", "zh-CN")
    assert get_default_locale() == "zh-CN"


def test_lang_context_without_a_context_returns_the_default(cfg, monkeypatch):
    monkeypatch.setattr(cfg.BasicConfig, "LOCALE", "zh-CN")
    assert lang_context() == "zh-CN"


def test_lang_context_with_invalid_context_returns_the_default(cfg, monkeypatch):
    monkeypatch.setattr(cfg.BasicConfig, "LOCALE", "zh-CN")
    with ContextReverseHelper():
        assert lang_context() == "zh-CN"


def test_lang_context_when_get_context_raises(cfg, monkeypatch):
    monkeypatch.setattr(cfg.BasicConfig, "LOCALE", "zh-CN")

    def boom():
        raise RuntimeError

    monkeypatch.setattr(lang_ctx, "get_context", boom)
    assert lang_context() == "zh-CN"


def test_lang_context_uses_the_per_user_locale(make_context):
    ct = make_context(user_id=42)
    set_lang(42, "zh-CN")
    with ContextHelper(ct):
        assert lang_context() == "zh-CN"
        assert t(D) == "你好"


def test_unknown_user_falls_back_to_the_default(cfg, monkeypatch, make_context):
    monkeypatch.setattr(cfg.BasicConfig, "LOCALE", "en")
    set_lang(42, "zh-CN")
    with ContextHelper(make_context(user_id=99)):
        assert lang_context() == "en"


def test_lang_context_manager_is_a_singleton():
    assert LangContextManager.get_inst() is LangContextManager.get_inst()


# ---------------------------------------------------------- BasicLanguage


def _language_dicts():
    return {
        name: value
        for name, value in vars(BasicLanguage).items()
        if not name.startswith("_") and isinstance(value, dict)
    }


def test_every_language_entry_covers_the_same_locales():
    dicts = _language_dicts()
    assert dicts, "no language entries found"
    expected = set(next(iter(dicts.values())))
    missing = {
        name: expected - set(value)
        for name, value in dicts.items()
        if set(value) != expected
    }
    assert missing == {}


def test_every_language_entry_is_translatable():
    for name, value in _language_dicts().items():
        for locale in value:
            assert BasicLanguage.t(value, locale), name


def test_basic_language_t_delegates_to_multi_lang():
    assert BasicLanguage.t(BasicLanguage.CANCELLED, "en") == "Cancelled~"
    assert BasicLanguage.t(BasicLanguage.CANCELLED, "zh-CN") == "操作取消～"
