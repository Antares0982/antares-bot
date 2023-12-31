import traceback
from logging import DEBUG as LOGLEVEL_DEBUG
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type, TypeVar, Union

from telegram import Update
from telegram.error import Conflict, NetworkError, RetryAfter, TimedOut
from telegram.ext import Application, ContextTypes

from bot_cfg import MASTER_ID, TOKEN
from bot_framework.bot_base import TelegramBotBase
from bot_framework.bot_logging import get_logger, get_root_logger
from bot_framework.callback_manager import CallbackDataManager
from bot_framework.context import ChatData, RichCallbackContext, UserData
from bot_framework.error import UserPermissionException
from bot_framework.framework import CallbackBase, command_callback_wrapper
from bot_framework.module_loader import ModuleKeeper
from bot_framework.patching.application_ex import ApplicationEx
from bot_framework.patching.job_quque_ex import JobQueueEx
from bot_framework.permission_check import CheckLevel
from bot_framework.context_manager import get_context

if TYPE_CHECKING:
    from bot_framework.module_base import TelegramBotModuleBase

_T = TypeVar("_T", bound="TelegramBotModuleBase", covariant=True)

_LOGGER = get_logger("main")


def format_traceback(err: Exception) -> str:
    return '\n'.join(traceback.format_tb(err.__traceback__))


async def exception_handler(update, context: RichCallbackContext):
    try:
        err = context.error
        if err is None or err.__class__ in (NetworkError, OSError, TimedOut, ConnectionError, Conflict, RetryAfter):
            return  # 直接吃掉
        if err.__class__ is UserPermissionException:
            if get_context() is None:
                _LOGGER.error("No context found")
                return
            await get_bot_instance().reply("你没有权限哦")
            return
        tb = format_traceback(err)
        log_text = f"{err.__class__}\n{err}\ntraceback:\n{tb}"
        _LOGGER.error(log_text)
        text = f"哎呀，出现了未知的错误呢……"
        await get_bot_instance().send_to(MASTER_ID, text)
    except Exception as _e:
        try:
            _LOGGER.error(format_traceback(_e))
        except Exception:
            pass


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
            .job_queue(JobQueueEx())\
            .build()
        self.bot = self.application.bot
        self.updater = self.application.updater
        assert self.application.job_queue
        self.job_queue = self.application.job_queue
        #
        self.callback_manager = CallbackDataManager()
        self.callback_key_dict: Dict[Tuple[int, int], List[str]] = dict()
        self._old_log_level = None

    def run(self):
        self._module_keeper.load_all()
        for module in self._module_keeper.get_all_enabled_modules():
            module.do_init(self)

        for module in self._module_keeper.get_all_enabled_modules():
            module_inst = module.module_instance
            for func in module_inst.collect_handlers():
                if isinstance(func, CallbackBase):
                    self.application.add_handler(func.to_handler())  # , group=func.group)
                else:
                    self.application.add_handler(func)
                # try get module logger
                py_module = module.py_module()
                if hasattr(py_module, "_LOGGER"):
                    logger = getattr(py_module, "_LOGGER")
                else:
                    logger = get_logger(module.top_name)
                    setattr(py_module, "_LOGGER", logger)
                logger.warn(f"added handler: {func}")

        main_handlers = [
            self.stop,
            self.debug_mode
        ]

        for handler in main_handlers:
            self.application.add_handler(handler.to_handler())
            _LOGGER.warn(f"added handler: {handler}")

        self.application.add_error_handler(exception_handler)

        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    @command_callback_wrapper
    async def stop(self, u, c):
        self.check(CheckLevel.MASTER)
        self.application.stop_running()

    def get_module(self, top_name_or_clsss: Union[str, Type[_T]]) -> Optional[_T]:
        if isinstance(top_name_or_clsss, str):
            return self._module_keeper.get_module(top_name_or_clsss)  # type: ignore
        return self._module_keeper.get_module_by_class(top_name_or_clsss)

    def remove_job_if_exists(self, name: str) -> bool:
        """Remove job with given name. Returns whether job was removed."""
        current_jobs = self.job_queue.get_jobs_by_name(name)
        if not current_jobs:
            return False
        for job in current_jobs:
            job.schedule_removal()
        return True

    @command_callback_wrapper
    async def debug_mode(self, update, context):
        self.check(CheckLevel.MASTER)
        root_logger = get_root_logger()
        old_level = root_logger.level
        if old_level == LOGLEVEL_DEBUG:
            root_logger.setLevel(self._old_log_level)
            self._old_log_level = None
        else:
            self._old_log_level = old_level
            root_logger.setLevel(LOGLEVEL_DEBUG)
        await self.reply

    @command_callback_wrapper
    async def exec(self, update, context):
        self.check(CheckLevel.MASTER)
        try:
            exec(context.args[0])
        except Exception as e:
            await self.reply(f"执行失败：{e}")
        else:
            await self.reply("执行成功")


__bot_singleton = None


def destroy_bot_instance():
    global __bot_singleton
    if __bot_singleton is not None:
        __bot_singleton.stop()
        __bot_singleton = None


def get_bot_instance() -> TelegramBot:
    global __bot_singleton
    if __bot_singleton is None:
        __bot_singleton = TelegramBot()
    return __bot_singleton