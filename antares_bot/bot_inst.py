import asyncio
import datetime
import os
import subprocess
import sys
import time
import traceback
from logging import DEBUG as LOGLEVEL_DEBUG
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Dict, List, Optional, Tuple, Type, TypeVar, Union, cast

from telegram import Update
from telegram.error import Conflict, NetworkError, RetryAfter, TimedOut
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler

from bot_cfg import DEFAULT_DATA_DIR, MASTER_ID, TOKEN
from antares_bot.bot_base import TelegramBotBase
from antares_bot.bot_logging import get_logger, get_root_logger, stop_logger
from antares_bot.callback_manager import CallbackDataManager
from antares_bot.context import ChatData, RichCallbackContext, UserData
from antares_bot.context_manager import ContextHelper, get_context
from antares_bot.error import InvalidChatTypeException, UserPermissionException, permission_exceptions
from antares_bot.framework import CallbackBase, command_callback_wrapper
from antares_bot.module_loader import ModuleKeeper
from antares_bot.patching.application_ex import ApplicationEx
from antares_bot.patching.job_quque_ex import JobQueueEx
from antares_bot.permission_check import CheckLevel
from antares_bot.utils import markdown_escape


if TYPE_CHECKING:
    from antares_bot.module_base import TelegramBotModuleBase

_T = TypeVar("_T", bound="TelegramBotModuleBase", covariant=True)

_LOGGER = get_logger("main")
TIME_IN_A_DAY = 24 * 60 * 60

# note that wildcard import is only allowed at module level
_INTERNAL_TEST_EXEC_COMMAND_PREFIX = """\
from antares_bot.test_commands import *
from bot_cfg import *
async def __t():
    self = get_bot_instance()
"""


def format_traceback(err: Exception) -> str:
    return '\n'.join(traceback.format_tb(err.__traceback__))


async def _leaked_permission_exception_handler(err: Exception):
    try:
        if isinstance(err, UserPermissionException):
            await get_bot_instance().reply("你没有权限哦")
        elif isinstance(err, InvalidChatTypeException):
            await get_bot_instance().reply("不能在这里使用哦")
    except Exception:
        pass


async def exception_handler(update: Any, context: RichCallbackContext):
    try:
        err = context.error
        if err is None or err.__class__ in (NetworkError, OSError, TimedOut, ConnectionError, Conflict, RetryAfter):
            return  # ignore them
        permission_exception_types = permission_exceptions()
        if isinstance(err, permission_exception_types):
            # in case of didn't catching permission exceptions properly
            # generally, catching permission exception here greatly affects the performance
            if get_context() is None:
                _LOGGER.error("No context found")
                return
            with ContextHelper(context):
                await _leaked_permission_exception_handler(err)
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
        self.application = cast(ApplicationEx, Application.builder()
                                .application_class(ApplicationEx)
                                .token(TOKEN)
                                .context_types(context_types)
                                .job_queue(JobQueueEx())
                                .post_init(self._do_post_init)
                                .post_stop(self._do_post_stop)
                                .build())
        self.bot = self.application.bot
        self.updater = self.application.updater
        assert self.application.job_queue
        self.job_queue = self.application.job_queue
        #
        self.callback_manager = CallbackDataManager()
        self.callback_key_dict: Dict[Tuple[int, int], List[str]] = dict()
        self._old_log_level = None
        self.registered_daily_jobs: Dict[str, Callable[[RichCallbackContext], Coroutine[Any, Any, Any]]] = dict()
        self._custom_post_init_task: Coroutine[Any, Any, Any] | None = None
        self._custom_post_stop_task: Coroutine[Any, Any, Any] | None = None
        # TODO do a flags check at the end of the run. move the flags into a new class
        self._post_stop_restart_flag = False
        self._post_stop_gitpull_flag = False
        self._custom_restart_command: str | list[str] | None = None
        # some pre-checks
        if self._is_debug_level():
            _LOGGER.debug("Warning: the initial logging level is DEBUG. The built-in /debug_mode command will not work.")

    async def _do_post_init(self, app: Application):
        tasks = [module.post_init(app) for module in self._module_keeper.get_all_enabled_modules()]
        if self._custom_post_init_task is not None:
            tasks.append(self._custom_post_init_task)
            self._custom_post_init_task = None
        await asyncio.gather(*tasks)

    async def _do_post_stop(self, app: Application):
        if self._custom_post_stop_task is not None:
            await self._custom_post_stop_task
            self._custom_post_stop_task = None
        await self.send_to(MASTER_ID, "主人再见QAQ")
        await asyncio.gather(*(module.do_stop() for module in self._module_keeper.get_all_enabled_modules()))
        if self._post_stop_gitpull_flag:
            # create a subprocess to git pull
            try:
                msg = str(subprocess.check_output(["git", "pull"], encoding='utf-8'))
                if msg:
                    if "Already up to date." not in msg:
                        await self.send_to(MASTER_ID, msg)
            except Exception:
                await self.send_to(MASTER_ID, "git pull failed!")
        await stop_logger()

    def custom_post_init(self, task: Coroutine[Any, Any, Any]):
        self._custom_post_init_task = task

    def custom_post_stop(self, task: Coroutine[Any, Any, Any]):
        self._custom_post_stop_task = task

    def custom_restart_command(self, command: str | list[str]):
        self._custom_restart_command = command

    def run(self):
        self._module_keeper.load_all()
        for module in self._module_keeper.get_all_enabled_modules():
            module.do_init(self)

        for module in self._module_keeper.get_all_enabled_modules():
            module_inst = module.module_instance
            for func in module_inst.collect_handlers():
                if isinstance(func, CallbackBase):
                    handler = func.to_handler()
                else:
                    handler = func
                if isinstance(handler, CommandHandler):
                    for command in handler.commands:
                        self.application.handler_docs[command] = func.__doc__ if func.__doc__ else "No doc"
                elif isinstance(handler, ConversationHandler):
                    entry = handler.entry_points
                    for entry_point in entry:
                        if isinstance(entry_point, CommandHandler):
                            for command in entry_point.commands:
                                self.application.handler_docs[command] = func.__doc__ if func.__doc__ else "No doc"
                self.application.add_handler(handler)
                # try get module logger
                py_module = module.py_module()
                if hasattr(py_module, "_LOGGER"):
                    logger = getattr(py_module, "_LOGGER")
                else:
                    logger = get_logger(module.top_name)
                    setattr(py_module, "_LOGGER", logger)
                logger.info(f"added handler: {func}")

        main_handlers = [
            self.stop,
            self.restart,
            self.debug_mode,
            self.exec,
            self.get_id,
            self.help,
        ]

        for method in main_handlers:
            handler = method.to_handler()
            self.application.add_handler(handler)
            for command in handler.commands:
                self.application.handler_docs[command] = method.__doc__ if method.__doc__ else "No doc"
            _LOGGER.info(f"added handler: {handler}")

        self.application.handler_docs["cancel"] = """
        Cancel the current operation.
        """

        self.application.add_error_handler(exception_handler)

        self.job_queue.run_daily(self._daily_job, time=datetime.time(hour=0, minute=0), name="daily_job")

        try:
            self.application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        except NetworkError:  # catches the NetworkError when the bot is turned off. we don't care about that
            pass

        # post run
        self._post_run()

    def _post_run(self):
        if self._post_stop_restart_flag:
            # create a detached subprocess to restart the bot
            restart_command = self._custom_restart_command if self._custom_restart_command is not None else sys.orig_argv
            if isinstance(restart_command, list):
                import shlex
                restart_command = shlex.join(restart_command)
            restart_command = f"{restart_command} & disown"
            try:
                subprocess.run(restart_command, shell=True)
                print(f"Restarting the bot with command: {restart_command}")
            except Exception as e:
                # cannot use logger here, the logger is stopped
                print(f"Failed to restart the bot with command: {restart_command}", file=sys.stderr)
                raise

    @command_callback_wrapper
    async def stop(self, u, c):
        """
        Stop the bot.
        """
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
        """
        Switch debug mode on/off.
        """
        self.check(CheckLevel.MASTER)
        root_logger = get_root_logger()
        old_level = root_logger.level
        if old_level == LOGLEVEL_DEBUG:
            if self._old_log_level is None:
                raise RuntimeError("Invalid state: maybe default debug level is DEBUG!")
            self.debug_info("debug off")
            root_logger.setLevel(self._old_log_level)
            self._old_log_level = None
            await self.reply("已关闭debug模式")
        else:
            self._old_log_level = old_level
            root_logger.setLevel(LOGLEVEL_DEBUG)
            self.debug_info("debug on")
            await self.reply("已开启debug模式")

    async def _internal_exec(self, command: str):
        if not command:
            await self.error_info("没有接收到命令诶")
            return
        codes = command.split("\n")
        try:
            code_string = _INTERNAL_TEST_EXEC_COMMAND_PREFIX + ''.join(f'\n    {l}' for l in codes)
            _LOGGER.warning(f"executing: {code_string}")
            exec(code_string)
            ans = await locals()["__t"]()
        except Exception:
            asyncio.get_running_loop().create_task(self.reply("执行失败……"))
            raise
        await self.reply(f"执行成功，返回值：{ans}")

    @command_callback_wrapper
    async def exec(self, update: Update, context: RichCallbackContext):
        """
        Execute python code.
        `antares_bot.test_commands` and `bot_cfg` are wildcard imported by default.
        You can use `self` to refer to the bot instance.
        """
        self.check(CheckLevel.MASTER)
        assert context.args is not None
        if len(context.args) == 0:
            await self.error_info("没有接收到命令诶")
            return
        assert update.message is not None and update.message.text is not None
        command = update.message.text
        if command.startswith("/exec"):
            command = command[5:]
        command = command.strip()
        await self._internal_exec(command)

    def data_dir(self):
        return os.path.join(os.path.curdir, DEFAULT_DATA_DIR)

    async def _daily_job(self, context: RichCallbackContext):
        is_debug = self._is_debug_level()
        if is_debug:
            _debug_ids = []
        for old_id in self.callback_manager.history.pop_before_keys(time.time() - TIME_IN_A_DAY):
            self.callback_manager.pop_data(old_id)
            if is_debug:
                _debug_ids.append(old_id)
        if is_debug:
            _LOGGER.debug(f"Daily job: removed {_debug_ids} keys from callback manager")
        #
        _LOGGER.debug(f"Start running daily jobs for each module")
        await asyncio.gather(*(job(context) for job in self.registered_daily_jobs.values()))

    @command_callback_wrapper
    async def get_id(self, update: Update, context: RichCallbackContext):
        """
        Get the user id / chat id.
        In a group chat, if replying to a message, get the user id of the replied message.
        """
        if context.is_group_chat() and update.message is not None and update.message.reply_to_message is not None and update.message.reply_to_message.from_user is not None:
            return await self.reply(
                f"群id：`{context.chat_id}`\n回复的消息的用户id：`{update.message.reply_to_message.from_user.id}`",
                parse_mode="MarkdownV2"
            )
        elif context.is_group_chat():
            return await self.reply(
                f"群id：`{context.chat_id}`\n您的id：`{context.user_id}`",
                parse_mode="MarkdownV2"
            )
        else:
            return await self.reply(
                f"您的id：\n`{context.user_id}`",
                parse_mode="MarkdownV2"
            )

    async def _internal_full_help(self, context: RichCallbackContext):
        ret = ""
        for command, doc in self.application.handler_docs.items():
            ret += f"`/help {command}`\n"
        await self.success_info(ret, parse_mode="Markdown")

    @command_callback_wrapper
    async def help(self, update: Update, context: RichCallbackContext):
        """
        `/help [command]`: get the docstring for commands
        """
        assert context.args is not None
        if len(context.args) == 0:
            return await self._internal_full_help(context)
        command = context.args[0]
        doc = self.application.handler_docs.get(command)
        if doc is None:
            return await self.error_info(f"没有找到命令：{command}")
        return await self.success_info(f"/{markdown_escape(command)}: {doc}", parse_mode="Markdown")

    @command_callback_wrapper
    async def restart(self, update: Update, context: RichCallbackContext):
        """
        Restart the bot.
        """
        self.check(CheckLevel.MASTER)
        self._post_stop_restart_flag = True
        await self.stop.__wrapped__(self, update, context)

    def pull_when_stop(self, flag: bool = True):
        self._post_stop_gitpull_flag = flag


__bot_singleton = None


def destroy_bot_instance():
    global __bot_singleton
    if __bot_singleton is not None:
        __bot_singleton.stop()
        __bot_singleton = None


__REGISTERED_BOT_CLASS = TelegramBot


def register_bot_class(cls: Type[TelegramBot]):
    if issubclass(cls, TelegramBot):
        global __REGISTERED_BOT_CLASS
        __REGISTERED_BOT_CLASS = cls
    else:
        raise RuntimeError("Invalid bot class")


def get_bot_instance() -> TelegramBot:
    global __bot_singleton
    if __bot_singleton is None:
        __bot_singleton = __REGISTERED_BOT_CLASS()
    return __bot_singleton
