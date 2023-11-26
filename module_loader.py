import os
import sys
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable, Dict, Generic, List, Optional, Type, TypeVar, cast

from bot_framework.module_base import TelegramBotModuleBase
from bot_logging import error, warn


if TYPE_CHECKING:
    from bot_inst import TelegramBot
_T = TypeVar("_T", bound=TelegramBotModuleBase)

MODULE_PRIORITY_STR = "MODULE_PRIORITY"
MODULE_SKIP_LOAD = "MODULE_SKIP_LOAD_STR"
VALID_MODULE_RANGE = (0, 256)


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
        return getattr(self.kls, MODULE_PRIORITY_STR, 128)

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

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled


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
        module = d1.get(k, None)
        if module is not None:
            module.set_enabled(False)
            del d1[k]
            d2[k] = module
            return module
        return None

    def _remove_from_sorted_modules(self, module: TelegramBotModuleDesc[TelegramBotModuleBase]) -> None:
        self._ordered_modules.remove(module)

    @staticmethod
    def _import_all_modules() -> Dict[str, Type[TelegramBotModuleBase]]:
        ret: Dict[str, Type[TelegramBotModuleBase]] = dict()
        import importlib

        for dirname, _, filenames in os.walk("modules"):
            for i, filename in enumerate(filenames):
                if filename.endswith(".py") and filename != "__init__.py":
                    module_top_name = filename[:-3]
                    if module_top_name in ret:
                        error(f"{module_top_name} is duplicated")
                        continue
                    module_full_name = os.path.join(dirname, filename).replace(os.path.sep, ".")[:-3]
                    try:
                        if module_full_name in sys.modules:
                            # reload
                            is_reload = True
                            module = importlib.reload(sys.modules[module_full_name])
                        else:
                            is_reload = False
                            module = importlib.import_module(module_full_name)
                    except Exception as e:
                        error(e)
                        continue
                    _names = module_top_name.split("_")
                    class_name = ''.join([name.capitalize() for name in _names])
                    kls = getattr(module, class_name, None)
                    try:
                        assert kls is not None
                        if not issubclass(kls, TelegramBotModuleBase):  # type: ignore
                            continue
                    except Exception:
                        continue
                    skip = getattr(kls, MODULE_SKIP_LOAD, False)
                    if skip:
                        continue
                    #
                    _load_str = "reloaded" if is_reload else "loaded"
                    warn(f"{_load_str} module {module_top_name}")
                    ret[module_top_name] = kls

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
