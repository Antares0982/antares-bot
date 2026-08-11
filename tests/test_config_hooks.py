import os
import stat
import sys
import types

import pytest

from antares_bot import bot_default_cfg
from antares_bot.bot_default_cfg import AntaresBotConfig, BaseConfig, BasicConfig
from antares_bot.init_hooks import _hook_cfg, create_blank_cfg, read_user_cfg


# --------------------------------------------------------------- BaseConfig


def test_iter_all_config_keys_only_yields_upper_case():
    keys = set(BasicConfig.iter_all_config_keys())
    assert "TOKEN" in keys
    assert "MASTER_ID" in keys
    assert "non_empty" not in keys
    assert not any(k.startswith("__") for k in keys)
    assert all(k == k.upper() for k in keys)


def test_iter_all_config_keys_on_an_empty_config():
    class Empty(BaseConfig):
        pass

    assert list(Empty.iter_all_config_keys()) == []


# ------------------------------------------------------------ read_user_cfg


def test_read_user_cfg_returns_none_for_a_missing_section(cfg, monkeypatch):
    monkeypatch.delattr(cfg.AntaresBotConfig, "NOPE", raising=False)
    assert read_user_cfg(AntaresBotConfig, "NOPE") is None


def test_read_user_cfg_returns_none_for_a_missing_class(monkeypatch):
    empty = types.ModuleType("bot_cfg")
    monkeypatch.setitem(sys.modules, "bot_cfg", empty)
    assert read_user_cfg(BasicConfig, "TOKEN") is None


def test_read_user_cfg_reads_the_value(cfg):
    assert read_user_cfg(BasicConfig, "TOKEN") == cfg.BasicConfig.TOKEN


# ---------------------------------------------------------------- _hook_cfg


def _install_cfg(monkeypatch, **classes):
    module = types.ModuleType("bot_cfg")
    for name, kls in classes.items():
        setattr(module, name, kls)
    monkeypatch.setitem(sys.modules, "bot_cfg", module)
    return module


def test_hook_cfg_backfills_a_missing_optional_class(monkeypatch):
    class UserBasic:
        TOKEN = "t"
        MASTER_ID = 3

    module = _install_cfg(monkeypatch, BasicConfig=UserBasic)
    assert not hasattr(module, "AntaresBotConfig")
    _hook_cfg()
    # AntaresBotConfig has no `non_empty`, so the default class is installed
    assert module.AntaresBotConfig is bot_default_cfg.AntaresBotConfig


def test_hook_cfg_backfills_missing_keys(monkeypatch):
    class UserBasic:
        TOKEN = "t"
        MASTER_ID = 3

    _install_cfg(monkeypatch, BasicConfig=UserBasic)
    assert not hasattr(UserBasic, "LOCALE")
    try:
        _hook_cfg()
        assert UserBasic.LOCALE == BasicConfig.LOCALE
        assert UserBasic.DATA_DIR == BasicConfig.DATA_DIR
        # user values are never overwritten
        assert UserBasic.TOKEN == "t"
    finally:
        for k in ("LOCALE", "DATA_DIR"):
            if k in vars(UserBasic):
                delattr(UserBasic, k)


def test_hook_cfg_exits_when_a_required_class_is_absent(monkeypatch):
    _install_cfg(monkeypatch)  # no BasicConfig at all
    with pytest.raises(SystemExit) as exc:
        _hook_cfg()
    assert exc.value.code == 1


def test_hook_cfg_exits_when_a_required_key_is_missing(monkeypatch):
    class UserBasic:
        TOKEN = "t"  # MASTER_ID missing

    _install_cfg(monkeypatch, BasicConfig=UserBasic)
    with pytest.raises(SystemExit) as exc:
        _hook_cfg()
    assert exc.value.code == 1


def test_hook_cfg_exits_when_bot_cfg_cannot_be_imported(monkeypatch, tmp_path):
    monkeypatch.delitem(sys.modules, "bot_cfg")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "path", [str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        _hook_cfg()
    assert exc.value.code == 1
    # a template was written for the user
    assert (tmp_path / "bot_cfg.py").exists()


# ---------------------------------------------------------- create_blank_cfg


def test_create_blank_cfg_writes_a_private_valid_template(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    create_blank_cfg()
    path = tmp_path / "bot_cfg.py"
    assert path.exists()
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    source = path.read_text(encoding="utf-8")
    compile(source, "bot_cfg.py", "exec")  # must be importable Python
    assert "class BasicConfig" in source
    assert "class AntaresBotConfig" in source


def test_create_blank_cfg_never_overwrites(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "bot_cfg.py"
    path.write_text("# mine", encoding="utf-8")
    create_blank_cfg()
    assert path.read_text(encoding="utf-8") == "# mine"
    assert "already exists" in capsys.readouterr().err
