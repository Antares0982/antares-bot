from typing import TYPE_CHECKING, Dict, List, Optional, Type, TypeVar, Union

from telegram import Update
from telegram.ext import Application, ContextTypes

from bot_cfg import TOKEN
from bot_framework.bot_base import TelegramBotBase
from bot_framework.context import ChatData, RichCallbackContext, UserData
from bot_framework.framework import CallbackBase
from bot_framework.patching.application_ex import ApplicationEx
from bot_logging import warn
from module_loader import ModuleKeeper


if TYPE_CHECKING:
    from bot_framework.module_base import TelegramBotModuleBase

_T = TypeVar("_T", bound="TelegramBotModuleBase", covariant=True)
# _KT = TypeVar("_KT")
# _VT = TypeVar("_VT")


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
        self.application = Application.builder()\
            .application_class(ApplicationEx)\
            .token(TOKEN)\
            .context_types(context_types)\
            .build()
        self.bot = self.application.bot
        self.updater = self.application.updater
        self.job_queue = self.application.job_queue

    def start(self):
        self._module_keeper.load_all()
        for module in self._module_keeper.get_all_enabled_modules():
            module.do_init(self)

        for module in self._module_keeper.get_all_enabled_modules():
            module_inst = module.module_instance
            module_inst.collect_handlers()
            for func in module_inst.HANDLERS:
                if isinstance(func, CallbackBase):
                    self.application.add_handler(func.to_handler())  # , group=func.group)
                else:
                    self.application.add_handler(func)
                warn(f"added handler, name: {func.__name__}")
            # for command_callbacks_name in dir(module_inst):
            #     if command_callbacks_name.startswith("_"):
            #         continue
            #     try:
            #         func = getattr(module_inst, command_callbacks_name)
            #     except RuntimeError:
            #         continue
            #     if isinstance(func, CommandCallback):
            #         self.application.add_handler(func.to_handler(command=command_callbacks_name))
            #         warn(f"added handler for {command_callbacks_name}")
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
