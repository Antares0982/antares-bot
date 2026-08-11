import sys

import pytest

from antares_bot.module_analyze_utils import (
    get_module_class_from_module,
    get_module_class_from_name,
    get_module_from_name,
)
from antares_bot.module_base import TelegramBotModuleBase
from antares_bot.module_loader import (
    DEFAULT_PRIORITY,
    ModuleKeeper,
    TelegramBotModuleDesc,
)


# ----------------------------------------------------- module_analyze_utils


def test_get_module_from_name_for_an_imported_module():
    module, is_reload = get_module_from_name("antares_bot.utils")
    assert is_reload is True
    assert module is sys.modules["antares_bot.utils"]


def test_get_module_from_name_imports_on_demand(monkeypatch):
    monkeypatch.delitem(sys.modules, "antares_bot.test_commands", raising=False)
    module, is_reload = get_module_from_name("antares_bot.test_commands")
    assert is_reload is False
    assert module is not None


def test_get_module_from_name_swallows_import_errors():
    assert get_module_from_name("no.such.module_xyz") == (None, False)


def test_get_module_class_from_module_maps_snake_to_camel(tmp_path, monkeypatch):
    module = _write_module(tmp_path, monkeypatch, "my_example", _MODULE_SOURCE)
    kls = get_module_class_from_module(module)
    assert kls is not None
    assert kls.__name__ == "MyExample"


def test_get_module_class_from_module_returns_none_on_mismatch(tmp_path, monkeypatch):
    module = _write_module(
        tmp_path, monkeypatch, "mismatch", "class NotMatching: pass\n"
    )
    assert get_module_class_from_module(module) is None


def test_get_module_class_from_module_checks_the_base_class(tmp_path, monkeypatch):
    module = _write_module(
        tmp_path, monkeypatch, "plain_thing", "class PlainThing: pass\n"
    )
    assert get_module_class_from_module(module) is not None
    assert get_module_class_from_module(module, TelegramBotModuleBase) is None


def test_get_module_class_from_name_for_a_missing_module():
    assert get_module_class_from_name("no.such.module_xyz") is None


_MODULE_SOURCE = """\
from antares_bot.module_base import TelegramBotModuleBase


class MyExample(TelegramBotModuleBase):
    pass
"""


def _write_module(tmp_path, monkeypatch, name, source):
    (tmp_path / f"{name}.py").write_text(source, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(sys.modules, name, raising=False)
    import importlib

    module = importlib.import_module(name)
    monkeypatch.delitem(sys.modules, name, raising=False)
    return module


# ------------------------------------------------- TelegramBotModuleDesc


class _Mod(TelegramBotModuleBase):
    pass


def test_priority_defaults():
    assert TelegramBotModuleDesc("m", _Mod).priority == DEFAULT_PRIORITY


def test_priority_is_read_from_the_class():
    class Prioritised(TelegramBotModuleBase):
        MODULE_PRIORITY = 10

    assert TelegramBotModuleDesc("m", Prioritised).priority == 10


@pytest.mark.parametrize("priority", [-1, 256, 1000])
def test_check_priority_valid_rejects_out_of_range(priority):
    class Bad(TelegramBotModuleBase):
        MODULE_PRIORITY = priority

    with pytest.raises(ValueError):
        TelegramBotModuleDesc("bad", Bad).check_priority_valid()


@pytest.mark.parametrize("priority", [0, 128, 255])
def test_check_priority_valid_accepts_the_range(priority):
    class Good(TelegramBotModuleBase):
        MODULE_PRIORITY = priority

    assert TelegramBotModuleDesc("good", Good).check_priority_valid() is None


def test_desc_repr_and_py_module():
    desc = TelegramBotModuleDesc("m", _Mod)
    assert "m" in repr(desc)
    assert desc.py_module() is sys.modules[_Mod.__module__]


def test_desc_lifecycle_without_an_instance_is_safe():
    desc = TelegramBotModuleDesc("m", _Mod)
    assert desc.module_instance is None
    assert desc.enabled is True
    desc.set_enabled(False)
    assert desc.enabled is False


async def test_desc_post_init_and_stop_without_an_instance():
    desc = TelegramBotModuleDesc("m", _Mod)
    assert await desc.post_init(None) is None  # type: ignore[arg-type]
    assert await desc.do_stop() is None


def test_desc_do_init_constructs_the_module(dummy_parent):
    desc = TelegramBotModuleDesc("m", _Mod)
    desc.do_init(dummy_parent)  # type: ignore[arg-type]
    assert isinstance(desc.module_instance, _Mod)
    assert desc.module_instance.parent is dummy_parent


# ------------------------------------------------------------ ModuleKeeper


def _klass(name, priority=None):
    attrs = {} if priority is None else {"MODULE_PRIORITY": priority}
    return type(name, (TelegramBotModuleBase,), attrs)


def test_sort_modules_orders_by_priority_then_name():
    klss = {
        "b_low": _klass("BLow", 10),
        "a_low": _klass("ALow", 10),
        "z_high": _klass("ZHigh", 200),
        "m_default": _klass("MDefault"),
    }
    ordered = ModuleKeeper._sort_modules(klss)
    assert [m.top_name for m in ordered] == ["a_low", "b_low", "m_default", "z_high"]


def test_keeper_lookup_by_name_and_class():
    keeper = ModuleKeeper()
    kls = _klass("Sample")
    keeper._add_modules(ModuleKeeper._sort_modules({"sample": kls}))

    desc = keeper.get_all_enabled_modules()[0]
    desc.module_instance = "INSTANCE"  # type: ignore[assignment]
    assert keeper.get_module("sample") == "INSTANCE"
    assert keeper.get_module_by_class(kls) == "INSTANCE"
    assert keeper.get_module("nope") is None
    assert keeper.get_module_by_class(_klass("Other")) is None


def test_keeper_run_over_visits_every_module():
    keeper = ModuleKeeper()
    keeper._add_modules(
        ModuleKeeper._sort_modules({"a": _klass("A"), "b": _klass("B")})
    )
    seen = []
    keeper.run_over(seen.append)
    assert [d.top_name for d in seen] == ["a", "b"]


def test_keeper_clear():
    keeper = ModuleKeeper()
    keeper._add_modules(ModuleKeeper._sort_modules({"a": _klass("A")}))
    keeper.clear()
    assert keeper.get_all_enabled_modules() == []
    assert keeper.get_module("a") is None


def test_disable_module_is_not_implemented():
    """Guards the TODO in module_loader: flipping it on must be deliberate."""
    keeper = ModuleKeeper()
    keeper._add_modules(ModuleKeeper._sort_modules({"a": _klass("A")}))
    with pytest.raises(NotImplementedError):
        keeper.disable_module("a")


# --------------------------------------------------- _import_all_modules


@pytest.fixture
def modules_dir(tmp_path, monkeypatch, cfg):
    """A CWD with a ``modules/`` package, isolated from the internal modules."""
    monkeypatch.setattr(
        cfg.AntaresBotConfig, "SKIP_LOAD_ALL_INTERNAL_MODULES", True, raising=False
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    root = tmp_path / "modules"
    root.mkdir()
    (root / "__init__.py").write_text("", encoding="utf-8")

    created: list[str] = []

    def write(rel_path: str, source: str):
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        created.append(rel_path)
        return path

    yield write

    for name in list(sys.modules):
        if name == "modules" or name.startswith("modules."):
            del sys.modules[name]


def _module_source(class_name: str) -> str:
    return (
        "from antares_bot.module_base import TelegramBotModuleBase\n\n\n"
        f"class {class_name}(TelegramBotModuleBase):\n    pass\n"
    )


def test_import_all_modules_picks_up_a_matching_class(modules_dir):
    modules_dir("my_example.py", _module_source("MyExample"))
    found = ModuleKeeper._import_all_modules()
    assert set(found) == {"my_example"}
    assert found["my_example"].__name__ == "MyExample"


def test_import_all_modules_skips_a_mismatched_class_name(modules_dir):
    modules_dir("my_example.py", _module_source("SomethingElse"))
    assert ModuleKeeper._import_all_modules() == {}


def test_import_all_modules_skips_non_module_classes(modules_dir):
    modules_dir("plain_thing.py", "class PlainThing:\n    pass\n")
    assert ModuleKeeper._import_all_modules() == {}


def test_import_all_modules_ignores_dunder_init(modules_dir):
    modules_dir("__init__.py", _module_source("Init"))
    assert ModuleKeeper._import_all_modules() == {}


def test_import_all_modules_walks_subdirectories(modules_dir):
    modules_dir("sub_dir/__init__.py", "")
    modules_dir("sub_dir/sub_test.py", _module_source("SubTest"))
    found = ModuleKeeper._import_all_modules()
    # keyed by file name, not by path
    assert set(found) == {"sub_test"}


def test_import_all_modules_honours_skip_load_module(modules_dir, cfg, monkeypatch):
    modules_dir("my_example.py", _module_source("MyExample"))
    monkeypatch.setattr(
        cfg.AntaresBotConfig, "SKIP_LOAD_MODULE_MY_EXAMPLE", True, raising=False
    )
    assert ModuleKeeper._import_all_modules() == {}


def test_import_all_modules_raises_on_a_broken_module(modules_dir, cfg, monkeypatch):
    modules_dir("broken_one.py", "raise RuntimeError('boom')\n")
    monkeypatch.setattr(
        cfg.AntaresBotConfig, "IGNORE_IMPORT_MODULE_ERROR", False, raising=False
    )
    with pytest.raises(RuntimeError):
        ModuleKeeper._import_all_modules()


def test_import_all_modules_can_ignore_a_broken_module(modules_dir, cfg, monkeypatch):
    modules_dir("broken_one.py", "raise RuntimeError('boom')\n")
    modules_dir("my_example.py", _module_source("MyExample"))
    monkeypatch.setattr(
        cfg.AntaresBotConfig, "IGNORE_IMPORT_MODULE_ERROR", True, raising=False
    )
    assert set(ModuleKeeper._import_all_modules()) == {"my_example"}


def test_import_all_modules_loads_internal_modules_by_default(
    tmp_path, monkeypatch, cfg
):
    monkeypatch.setattr(
        cfg.AntaresBotConfig, "SKIP_LOAD_ALL_INTERNAL_MODULES", False, raising=False
    )
    monkeypatch.chdir(tmp_path)  # no modules/ dir at all
    found = ModuleKeeper._import_all_modules()
    assert "internal_modules.antares_builtin" in found
    assert "internal_modules.obj_graph" in found


def test_skip_load_internal_module(tmp_path, monkeypatch, cfg):
    monkeypatch.setattr(
        cfg.AntaresBotConfig, "SKIP_LOAD_ALL_INTERNAL_MODULES", False, raising=False
    )
    monkeypatch.setattr(
        cfg.AntaresBotConfig,
        "SKIP_LOAD_INTERNAL_MODULE_OBJ_GRAPH",
        True,
        raising=False,
    )
    monkeypatch.chdir(tmp_path)
    found = ModuleKeeper._import_all_modules()
    assert "internal_modules.obj_graph" not in found
    assert "internal_modules.antares_builtin" in found
