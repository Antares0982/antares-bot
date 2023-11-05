from types import ModuleType
from typing import TYPE_CHECKING, List, Optional, Type, TypeVar, Union

from basebot import TelegramBotBase
from module_loader import ModuleKeeper

if TYPE_CHECKING:
    from basebot import TelegramBotModuleBase

_T = TypeVar("_T", bound="TelegramBotModuleBase", covariant=True)


class TelegramBot(TelegramBotBase):
    def __init__(self) -> None:
        self._module_keeper = ModuleKeeper()

    # def get_loaded_modules(self) -> List[ModuleType]:
    #     return self._module_keeper.loaded_modules

    def start(self):
        self._module_keeper.load_all()
        for module in self._module_keeper.get_all_enabled_modules():
            module.do_init(self)

    def get_module(self, top_name_or_clsss: Union[str, Type[_T]]) -> Optional[_T]:
        if isinstance(top_name_or_clsss, str):
            return self._module_keeper.get_module(top_name_or_clsss)  # type: ignore
        return self._module_keeper.get_module_by_class(top_name_or_clsss)


class MainBotApp(object):
    def __init__(self, **kwargs) -> None:
        self.bot_instance = TelegramBot(**kwargs)
        self.bot_instance.start()


__bot_app_singleton = None


def get_bot_app_instance() -> MainBotApp:
    global __bot_app_singleton
    if __bot_app_singleton is None:
        __bot_app_singleton = MainBotApp()
    return __bot_app_singleton


def destroy_bot_app_instance():
    global __bot_app_singleton
    if __bot_app_singleton is not None:
        __bot_app_singleton.stop()
        __bot_app_singleton = None
