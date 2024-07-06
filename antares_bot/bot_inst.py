import asyncio
import datetime
import os
import signal
import subprocess
import sys
import time
import traceback
from logging import DEBUG as LOGLEVEL_DEBUG
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Dict, List, Optional, Tuple, Type, TypeVar, Union, cast

from telegram import MessageOriginChannel, MessageOriginChat, MessageOriginHiddenUser, MessageOriginUser, Update
from telegram.error import Conflict, NetworkError, RetryAfter, TimedOut
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler

from antares_bot.basic_language import BasicLanguage as Lang
from antares_bot.bot_base import TelegramBotBase
from antares_bot.bot_default_cfg import BasicConfig
from antares_bot.bot_logging import get_logger, get_root_logger, stop_logger
from antares_bot.callback_manager import CallbackDataManager
from antares_bot.context import ChatData, RichCallbackContext, UserData
from antares_bot.context_manager import ContextHelper, get_context
from antares_bot.error import InvalidChatTypeException, UserPermissionException, permission_exceptions
from antares_bot.framework import CallbackBase, command_callback_wrapper
from antares_bot.module_loader import ModuleKeeper
from antares_bot.patching.job_quque_ex import JobQueueEx
from antares_bot.permission_check import CheckLevel
from antares_bot.text_process import trim_spaces_before_line
from antares_bot.utils import markdown_escape, read_user_cfg, systemd_service_info


if TYPE_CHECKING:
    from telegram.ext import ExtBot

    from antares_bot.module_base import TelegramBotModuleBase

_T = TypeVar("_T", bound="TelegramBotModuleBase", covariant=True)

_LOGGER = get_logger("main")
TIME_IN_A_DAY = 24 * 60 * 60

_PROGRAM_SHUTDOWN_STARTED = False

# note that wildcard import is only allowed at module level
_INTERNAL_TEST_EXEC_COMMAND_PREFIX = """\
from antares_bot.test_commands import *
from bot_cfg import BasicConfig
MASTER_ID = BasicConfig.MASTER_ID
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
        text = Lang.t(Lang.UNKNOWN_ERROR) + f"\n{err.__class__}: {err}"
        await get_bot_instance().send_to(TelegramBot.get_master_id(), text)
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
        self.application = cast(
            "Application[ExtBot[None], self.ContextType, self.UserDataType, self.ChatDataType, self.BotDataType, JobQueueEx]",
            Application.builder()
            # .application_class(ApplicationEx)
            .token(read_user_cfg(BasicConfig, "TOKEN"))
            .context_types(context_types)
            .job_queue(JobQueueEx())
            .post_init(self._do_post_init)
            .post_stop(self._do_post_stop)
            .build()
        )
        self.bot = self.application.bot
        assert self.application.updater is not None
        self.updater = self.application.updater
        assert self.application.job_queue is not None
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
        self._custom_finalize_task: Callable[[], Any] | None = None
        self._normal_exit_flag = False
        self.handler_docs: dict[str, str] = {}
        self._exit_fast = False
        # some pre-checks
        if self._is_debug_level():
            _LOGGER.debug("Warning: the initial logging level is DEBUG. The built-in /debug_mode command will not work.")

    @property
    def bot_id(self):
        return self.bot.bot.id

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
        task_send_exit_msg = self.send_to(self.get_master_id(), "主人再见QAQ")
        await asyncio.gather(*(module.do_stop() for module in self._module_keeper.get_all_enabled_modules()))
        from antares_bot.sqlite.manager import DataBasesManager
        task_stop_db = DataBasesManager.get_inst().shutdown()
        # pull the repo if _post_stop_gitpull_flag is set.
        # if exit_fast (SIGTERM, SIGABRT), do not pull
        additional_tasks = []
        if self._post_stop_gitpull_flag and not self._exit_fast:
            # create a subprocess to git pull
            try:
                msg = str(subprocess.check_output(
                    ["git", "pull", "--ff-only"],
                    encoding='utf-8')
                )
                if msg and "Already up to date." not in msg and "not a git repository" not in msg:
                    additional_tasks.append(self.send_to(self.get_master_id(), msg))
            except Exception:
                additional_tasks.append(self.send_to(self.get_master_id(), "git pull failed!"))
        task_stop_logger = stop_logger()
        await asyncio.gather(task_send_exit_msg, task_stop_db, task_stop_logger, *additional_tasks)

    def custom_post_init(self, task: Coroutine[Any, Any, Any]):
        self._custom_post_init_task = task

    def custom_post_stop(self, task: Coroutine[Any, Any, Any]):
        self._custom_post_stop_task = task

    def custom_restart_command(self, command: str | list[str]):
        self._custom_restart_command = command

    def custom_finalize(self, finalize_task: Callable[[], Any]):
        self._custom_finalize_task = finalize_task

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
                        _doc = func.__doc__
                        self.handler_docs[command] = _doc if _doc else "No doc"
                elif isinstance(handler, ConversationHandler):
                    entry = handler.entry_points
                    for entry_point in entry:
                        if isinstance(entry_point, CommandHandler):
                            for command in entry_point.commands:
                                _doc = entry_point.callback.__doc__
                                self.handler_docs[command] = _doc if _doc else "No doc"
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
                self.handler_docs[command] = method.__doc__ if method.__doc__ else "No doc"
            _LOGGER.info(f"added handler: {handler}")

        self.handler_docs["cancel"] = """
        cancel - cancel the current operation
        `/cancel`: Cancel the current operation.
        """

        self.application.add_error_handler(exception_handler)

        self.job_queue.run_daily(self._daily_job, time=datetime.time(hour=0, minute=0), name="daily_job")

        signal.signal(signal.SIGINT, self.signal_stop)
        signal.signal(signal.SIGTERM, self.signal_stop)
        signal.signal(signal.SIGABRT, self.signal_stop)

        # use eager factory
        if sys.version_info >= (3, 12):
            asyncio.get_event_loop().set_task_factory(asyncio.eager_task_factory)

        try:
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                stop_signals=(),
            )
        except NetworkError:
            # catches the NetworkError when the bot is turned off.
            # we don't care about that when normal exit
            if not self._normal_exit_flag:
                raise

        # post run
        self._post_run()

    def _post_run(self):
        global _PROGRAM_SHUTDOWN_STARTED
        if self._custom_finalize_task is not None:
            print("Running custom finalize task...")
            self._custom_finalize_task()

        if self._post_stop_restart_flag and not _PROGRAM_SHUTDOWN_STARTED:
            _PROGRAM_SHUTDOWN_STARTED = True
            systemd_service_name, is_root = systemd_service_info()
            if systemd_service_name is not None:
                restart_command = ["systemctl"] + (["--user"] if not is_root else []) + ["restart", systemd_service_name]
                restart_command = ' '.join(restart_command)
            else:
                # create a detached subprocess to restart the bot
                restart_command = self._custom_restart_command if self._custom_restart_command is not None else sys.orig_argv
                if isinstance(restart_command, list):
                    import shlex
                    restart_command = shlex.join(restart_command)
                restart_command = f"{restart_command} & disown"
            try:
                subprocess.Popen(restart_command, shell=True)
                print(f"Restarting the bot with command: {restart_command}")
            except Exception:
                # cannot use logger here, the logger is stopped
                print(f"Failed to restart the bot with command: {restart_command}", file=sys.stderr)
                raise

        if self._normal_exit_flag:
            print("Stopped gracefully.")
            # shutdown the stdout and stderr since the aiormq will still be printing rabbish
            sys.stdout.close()
            sys.stderr.close()
        else:
            print("Stopped unexpectedly.", file=sys.stderr)

    def true_stop(self, *args, **kwargs):
        self._normal_exit_flag = True
        self.application.stop_running()

    def signal_stop(self, sig, *args, **kwargs):
        global _PROGRAM_SHUTDOWN_STARTED
        if _PROGRAM_SHUTDOWN_STARTED:
            return
        _PROGRAM_SHUTDOWN_STARTED = True
        if sig == signal.SIGTERM or sig == signal.SIGABRT:
            self._exit_fast = True
        self.true_stop()

    @command_callback_wrapper
    async def stop(self, u, c):
        """
        stop - stop the bot
        Stop the bot.
        """
        self.check(CheckLevel.MASTER)
        self.true_stop()

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
        debug_mode - switch debug mode on or off
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
        exec - execute python code
        Execute python code.
        `antares_bot.test_commands` is wildcard imported by default.
        You can use `self` to refer to the bot instance.
        """
        self.check(CheckLevel.MASTER)
        if context.args is None or len(context.args) == 0:
            # if is a reply
            try:
                reply_to = update.message.reply_to_message.text.strip()  # type: ignore
            except AttributeError:
                await self.error_info("没有接收到命令诶")
                return
            await self._internal_exec(reply_to)
            return
        assert update.message is not None and update.message.text is not None
        command = self.get_message_after_command(update)
        await self._internal_exec(command)

    def data_dir(self):
        return os.path.join(os.path.curdir, read_user_cfg(BasicConfig, "DATA_DIR"))

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
        get_id - get the user id / chat id
        Get the user id / chat id.
        If replying to a forwarded message, get the id information of the forward prigin.
        Otherwise:
        - In a group chat:
          - If replying to a message, get the user id of the replied message;
          - otherwise, get the id of you and the group.
        - In a private chat: get your id.
        """
        if update.message is not None and update.message.reply_to_message is not None:
            message = update.message.reply_to_message
            forward_origin = message.forward_origin
            if forward_origin is not None:
                if forward_origin.type == forward_origin.CHANNEL:
                    forward_origin_channel = cast(MessageOriginChannel, forward_origin)
                    return await self.reply(
                        f"转发消息的来源频道id：`{forward_origin_channel.chat.id}`",
                        parse_mode="MarkdownV2"
                    )
                elif forward_origin.type == forward_origin.CHAT:
                    forward_origin_chat = cast(MessageOriginChat, forward_origin)
                    return await self.reply(
                        f"转发消息的来源群id：`{forward_origin_chat.sender_chat.id}`",
                        parse_mode="MarkdownV2"
                    )
                elif forward_origin.type == forward_origin.USER:
                    forward_origin_user = cast(MessageOriginUser, forward_origin)
                    return await self.reply(
                        f"转发消息的来源用户id：`{forward_origin_user.sender_user.id}`",
                        parse_mode="MarkdownV2"
                    )
                elif forward_origin.type == forward_origin.HIDDEN_USER:
                    return await self.reply(f"转发消息的来源用户已隐藏")
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
        for command, doc in self.handler_docs.items():
            ret += f"`/help {command}`\n"
        await self.success_info(ret, parse_mode="Markdown")

    @classmethod
    def _match_helpdoc_line0_command_list_format(cls, command: str, doc: str, is_extract=True):
        doc = doc.strip()
        _left, _, _right = doc.partition("\n")
        line0 = _left
        command_prefix = command + " - "
        if line0.startswith(command_prefix):
            return line0 if is_extract else _right
        return None if is_extract else doc

    def _internal_generate_command_list(self) -> str:
        content = []
        for command, doc in self.handler_docs.items():
            tmp = self._match_helpdoc_line0_command_list_format(command, doc)
            if tmp is not None:
                content.append(tmp)
        if len(content) == 0:
            return ""
        content.sort()
        content = ["```"] + content + ["```"]
        return '\n'.join(content)

    @command_callback_wrapper
    async def help(self, update: Update, context: RichCallbackContext):
        """
        help - show command helps
        `/help [command]`: get the docstring for commands.
        `/help to-command-list`: get the command list for setting up at BotFather.
        """
        assert context.args is not None
        if len(context.args) == 0:
            return await self._internal_full_help(context)

        command = context.args[0]
        if command == "to-command-list":
            content = self._internal_generate_command_list()
            if content:
                return await self.reply(content, parse_mode="Markdown")
            else:
                return await self.error_info("No command list available")
        doc = self.handler_docs.get(command)
        if doc is None:
            return await self.error_info(f"没有找到命令：{command}")
        doc = self._match_helpdoc_line0_command_list_format(command, doc, is_extract=False)
        if doc is not None:
            doc = trim_spaces_before_line(doc)
        if not doc:
            doc = "No doc"
        return await self.success_info(f"/{markdown_escape(command)}:\n{doc}", parse_mode="Markdown")

    @command_callback_wrapper
    async def restart(self, update: Update, context: RichCallbackContext):
        """
        Restart the bot.
        """
        self.check(CheckLevel.MASTER)
        self._post_stop_restart_flag = True
        self.true_stop()

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
