from typing import TYPE_CHECKING, Dict, List, Optional, Type, TypeVar, Union

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from basebot import TelegramBotBase
from bot_cfg import TOKEN
from bot_framework.context import ChatData, RichCallbackContext, UserData
from bot_framework.framework import CommandCallback, command_callback_wrapper
from module_loader import ModuleKeeper

if TYPE_CHECKING:
    from basebot import TelegramBotModuleBase

_T = TypeVar("_T", bound="TelegramBotModuleBase", covariant=True)
_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


class TelegramBot(TelegramBotBase):
    ContextType = RichCallbackContext
    ChatDataType = ChatData
    UserDataType = UserData
    BotDataType = dict

    def __init__(self) -> None:
        self._module_keeper = ModuleKeeper()
        context_types = ContextTypes(
            context=self.ContextType,
            chat_data=self.ChatDataType,
            user_data=self.UserDataType,
            bot_data=self.BotDataType  # type: ignore
        )
        self.application = Application.builder().token(TOKEN).context_types(context_types).build()

    # def get_loaded_modules(self) -> List[ModuleType]:
    #     return self._module_keeper.loaded_modules

    def start(self):
        self._module_keeper.load_all()
        for module in self._module_keeper.get_all_enabled_modules():
            module.do_init(self)

        for module in self._module_keeper.get_all_enabled_modules():
            module_inst = module.module_instance
            for command_callbacks_name in dir(module_inst):
                if command_callbacks_name.startswith("_"):
                    continue
                try:
                    func = getattr(module_inst, command_callbacks_name)
                except RuntimeError:
                    continue
                if isinstance(func, CommandCallback):
                    self.application.add_handler(CommandHandler(
                        command_callbacks_name,
                        func,
                        filters=func.filters,
                        block=func.block
                    ))
        # TODO

        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

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
