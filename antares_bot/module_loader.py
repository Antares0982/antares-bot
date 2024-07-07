import importlib
import os
import sys
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable, Dict, Generic, List, Optional, Type, TypeVar, cast

from antares_bot.bot_default_cfg import AntaresBotConfig
from antares_bot.bot_logging import get_logger
from antares_bot.module_base import TelegramBotModuleBase
from antares_bot.utils import read_user_cfg


if TYPE_CHECKING:
    from telegram.ext import Application

    from antares_bot.bot_inst import TelegramBot

_T = TypeVar("_T", bound=TelegramBotModuleBase)

MODULE_PRIORITY_STR = "MODULE_PRIORITY"
VALID_MODULE_RANGE = (0, 256)
DEFAULT_PRIORITY = 128

_LOGGER = get_logger(__name__)


class TelegramBotModuleDesc(Generic[_T]):
    """
    A descriptor of a tgbot module (usually a class, not a py module).
    """

    def __init__(self, top_name: str, kls: Type[_T]) -> None:
        self.top_name = top_name
        self.kls = kls
        self.module_instance: Optional[_T] = None
        self._enabled = True

    @property
    def priority(self) -> int:
        return getattr(self.kls, MODULE_PRIORITY_STR, DEFAULT_PRIORITY)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def check_priority_valid(self) -> None:
        l, r = VALID_MODULE_RANGE
        priority = self.priority
        if priority < l or priority >= r:
            raise ValueError(f"{MODULE_PRIORITY_STR} of {self.top_name} is invalid, should be in [{l}, {r})")

    def do_init(self, parent: "TelegramBot") -> None:
        self.module_instance = self.kls(parent)
        self.module_instance.do_init()

    async def post_init(self, app: "Application") -> None:
        if self.module_instance is not None:
            await self.module_instance.post_init(app)

    async def do_stop(self):
        if self.module_instance is not None:
            await self.module_instance.do_stop()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def py_module(self):
        return sys.modules[self.kls.__module__]

    def __repr__(self) -> str:
        return f"TelegramBotModule: {self.top_name}"


class ModuleKeeper(object):
    _STR = 1
    _TYPE = 2

    def __init__(self) -> None:
        self._ordered_modules: List[TelegramBotModuleDesc[TelegramBotModuleBase]] = []
        self._modules_dict: Dict[str, TelegramBotModuleDesc[TelegramBotModuleBase]] = dict()
        self._class2module_dict: Dict[Type[TelegramBotModuleBase], TelegramBotModuleDesc[TelegramBotModuleBase]] = dict()
        self._disabled_modules_dict: Dict[str, TelegramBotModuleDesc[TelegramBotModuleBase]] = dict()
        self._disabled_class2module_dict: Dict[Type[TelegramBotModuleBase], TelegramBotModuleDesc[TelegramBotModuleBase]] = dict()

    def load_all(self) -> None:
        """
        Should only be called once at init.
        """
        self._sort_and_set_modules(self._import_all_modules())

    def reload_all(self) -> None:
        self.clear()
        self.load_all()

    def get_module(self, top_name: str) -> Optional[TelegramBotModuleBase]:
        py_module = self._find_module_internal(top_name, self._STR)
        if py_module is not None:
            return py_module.module_instance
        return None

    def get_module_by_class(self, cls: Type[_T]) -> Optional[_T]:
        py_module = self._find_module_internal(cls, self._TYPE)
        if py_module is not None:
            return cast(_T, py_module.module_instance)
        return None

    def get_all_enabled_modules(self) -> List[TelegramBotModuleDesc[TelegramBotModuleBase]]:
        return self._ordered_modules

    def run_over(self, func: Callable[[TelegramBotModuleDesc[TelegramBotModuleBase]], Any]):
        for module in self._ordered_modules:
            func(module)

    def disable_module(self, top_name: str) -> None:
        self._disable_module_internal(top_name, self._STR)

    def disable_module_by_class(self, cls: Type[_T]) -> None:
        self._disable_module_internal(cls, self._TYPE)

    def clear(self) -> None:
        del self._ordered_modules[:]
        self._modules_dict.clear()
        self._class2module_dict.clear()

    def _find_module_internal(self, k, _type: int) -> Optional[TelegramBotModuleDesc[TelegramBotModuleBase]]:
        if _type == self._STR:
            return self._find_module_from(self._modules_dict, self._disabled_modules_dict, k)
        return self._find_module_from(self._class2module_dict, self._disabled_class2module_dict, k)

    @staticmethod
    def _find_module_from(d1: dict, d2: dict, k) -> Optional[TelegramBotModuleDesc[TelegramBotModuleBase]]:
        py_module = d1.get(k, None)
        if py_module is not None:
            return py_module
        return d2.get(k, None)

    def _disable_module_internal(self, k, _type: int) -> None:
        if _type == self._STR:
            module = self._disable_module_from(self._modules_dict, self._disabled_modules_dict, k)
        else:
            module = self._disable_module_from(self._class2module_dict, self._disabled_class2module_dict, k)
        if module is not None:
            self._remove_from_sorted_modules(module)
        raise ValueError(f"Module {k} not found")

    @staticmethod
    def _disable_module_from(
        d1: Dict[Any, TelegramBotModuleDesc],
        d2: Dict[Any, TelegramBotModuleDesc],
        k
    ) -> Optional[TelegramBotModuleDesc[TelegramBotModuleBase]]:
        # TODO
        raise NotImplementedError
        # module = d1.get(k, None)
        # if module is not None:
        #     module.set_enabled(False)
        #     del d1[k]
        #     d2[k] = module
        #     return module
        # return None

    def _remove_from_sorted_modules(self, module: TelegramBotModuleDesc[TelegramBotModuleBase]) -> None:
        self._ordered_modules.remove(module)

    @staticmethod
    def _import_all_modules() -> Dict[str, Type[TelegramBotModuleBase]]:

        def _module_check(_module, _module_top_name: str, module_store_name: str):
            _names = _module_top_name.split("_")
            class_name = ''.join([name.capitalize() for name in _names])
            kls = getattr(_module, class_name, None)
            if not isinstance(kls, type):
                return None
            try:
                if not issubclass(kls, TelegramBotModuleBase):  # type: ignore
                    return None
            except Exception:
                _LOGGER.error("%s is not a subclass of TelegramBotModuleBase", module_store_name)
                return None
            return kls

        def _import_module(_module_full_name: str):
            try:
                if exist_module := sys.modules.get(_module_full_name):
                    exist = True
                    module = exist_module
                else:
                    exist = False
                    module = importlib.import_module(_module_full_name)
            except Exception as e:
                if read_user_cfg(AntaresBotConfig, "IGNORE_IMPORT_MODULE_ERROR"):
                    _LOGGER.error(e)
                    return None
                else:
                    raise
            return exist, module

        skip_load_formatter = "SKIP_LOAD_MODULE_{}"
        skip_load_internal_formatter = "SKIP_LOAD_INTERNAL_MODULE_{}"
        ret: Dict[str, Type[TelegramBotModuleBase]] = dict()
        cur_path = os.path.dirname(os.path.abspath(__file__))
        cur_path_folder_name = os.path.basename(cur_path)

        def _load_up(_filename: str, is_internal: bool = False, _dirname: str | None = None):
            # is_internal: e.g. internal_modules/test.py -> test
            # not is_internal: e.g. modules/test.py -> test
            # not is_internal: e.g. modules/sub_dir/sub_test.py -> sub_test
            module_top_name = _filename[:-3]
            # use cfg to control whether to load (internal) modules
            skip = read_user_cfg(AntaresBotConfig, (skip_load_internal_formatter if is_internal else skip_load_formatter).format(module_top_name.upper())) or False
            if skip:
                return
            # is_internal: e.g. internal_modules/test.py -> internal_modules.test
            # not is_internal: same as `module_top_name`
            if is_internal:
                module_store_name = "internal_modules." + module_top_name
            else:
                module_store_name = module_top_name

            if module_store_name in ret:
                _LOGGER.error("%s is duplicated", module_store_name)
                return
            if is_internal:
                # e.g. internal_modules.test -> {cur_path_folder_name}.internal_modules.test
                module_full_name = f"{cur_path_folder_name}.{module_store_name}"
            else:
                # e.g. test.py -> modules.test
                assert _dirname is not None
                module_full_name = os.path.join(_dirname, _filename).replace(os.path.sep, ".")[:-3]
            # load it
            _import_result = _import_module(module_full_name)
            if _import_result is None:
                return
            exists, module = _import_result
            # check
            kls = _module_check(module, module_top_name, module_store_name)
            if kls is None:
                return
            # finalize
            if not exists:
                _LOGGER.info("loaded module %s", module_store_name)
            # is_internal: e.g. internal_modules/test.py, internal_modules.test -> Test
            # not is_internal: e.g. modules/test.py, test -> Test
            # not is_internal: e.g. modules/sub_dir/sub_test.py, sub_test -> SubTest
            ret[module_store_name] = kls

        # first load the internal modules

        os.path.join(cur_path, "internal_modules")
        if read_user_cfg(AntaresBotConfig, "SKIP_LOAD_ALL_INTERNAL_MODULES"):
            _LOGGER.warning("SKIP_LOAD_ALL_INTERNAL_MODULES is set to True, no internal modules will be loaded")
        else:
            for filename in os.listdir(os.path.join(cur_path, "internal_modules")):
                if filename.endswith(".py") and filename != "__init__.py":
                    _load_up(filename, is_internal=True)
                    continue

        # load user modules
        for dirname, _, filenames in os.walk("modules"):
            if dirname.endswith("__pycache__"):
                continue
            for filename in filenames:
                if filename.endswith(".py") and filename != "__init__.py":
                    _load_up(filename, _dirname=dirname)
                    continue

        return ret

    @staticmethod
    def _sort_modules(klss: Dict[str, Type[TelegramBotModuleBase]]):
        modules: List[TelegramBotModuleDesc[TelegramBotModuleBase]] = []
        temp_dict: defaultdict[int, List[TelegramBotModuleDesc[TelegramBotModuleBase]]] = defaultdict(list)
        for top_name, kls in klss.items():
            module = TelegramBotModuleDesc(top_name, kls)
            module.check_priority_valid()
            temp_dict[module.priority].append(module)
        for lst in temp_dict.values():
            lst.sort(key=lambda x: x.top_name)

        for k in sorted(temp_dict.keys()):
            modules.extend(temp_dict[k])
        return modules

    def _sort_and_set_modules(self, klss: Dict[str, Type[TelegramBotModuleBase]]):
        sorted_modules = self._sort_modules(klss)
        #
        self._add_modules(sorted_modules)

    def _add_module(self, module: TelegramBotModuleDesc[TelegramBotModuleBase]):
        self._maintain_add_module_internal(module)

    def _add_modules(self, modules: List[TelegramBotModuleDesc[TelegramBotModuleBase]]):
        for module in modules:
            self._maintain_add_module_internal(module)

    def _maintain_add_module_internal(self, module: TelegramBotModuleDesc[TelegramBotModuleBase]):
        if module.enabled:
            self._ordered_modules.append(module)
            self._modules_dict[module.top_name] = module
            self._class2module_dict[module.kls] = module
        else:
            self._disabled_modules_dict[module.top_name] = module
            self._disabled_class2module_dict[module.kls] = module
