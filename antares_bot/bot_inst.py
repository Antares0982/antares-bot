import asyncio
import datetime
import os
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import types
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from telegram import Update
from telegram.error import Conflict, NetworkError, RetryAfter, TimedOut
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler

from antares_bot.basic_language import BasicLanguage as Lang
from antares_bot.bot_base import TelegramBotBase
from antares_bot.bot_default_cfg import AntaresBotConfig, BasicConfig
from antares_bot.bot_logging import get_logger, start_logger, stop_logger
from antares_bot.callback_manager import CallbackDataManager
from antares_bot.context import ChatData, RichCallbackContext, UserData
from antares_bot.context_manager import ContextHelper, ContextReverseHelper, get_context
from antares_bot.error import (
    InvalidChatTypeException,
    UserPermissionException,
    permission_exceptions,
)
from antares_bot.format_exc import format_exception_with_local_vars, format_local_value
from antares_bot.framework import CallbackBase
from antares_bot.module_loader import ModuleKeeper
from antares_bot.patching.job_quque_ex import JobQueueEx
from antares_bot.sqlite.manager import DataBasesManager
from antares_bot.utils import (
    SYSTEM_TIME_ZONE,
    read_user_cfg,
    systemd_service_info,
)

if TYPE_CHECKING:
    from telegram.ext import ExtBot

    from antares_bot.module_base import TelegramBotModuleBase

_T = TypeVar("_T", bound="TelegramBotModuleBase", covariant=True)

_LOGGER = get_logger("main")
TIME_IN_A_DAY = 24 * 60 * 60

_PROGRAM_SHUTDOWN_STARTED = False


def format_traceback(exc, value, tb) -> str:
    return "\n".join(traceback.format_exception(exc, value, tb))


async def _leaked_permission_exception_handler(err: Exception):
    try:
        if isinstance(err, UserPermissionException):
            await get_bot_instance().reply(Lang.t(Lang.NO_PERMISSION))
        elif isinstance(err, InvalidChatTypeException):
            await get_bot_instance().reply(Lang.t(Lang.INVALID_CHAT_TYPE))
    except Exception:
        _LOGGER.error(format_traceback(type(err), err, err.__traceback__))


async def exception_handler(update: Any, context: RichCallbackContext):
    try:
        err = context.error
        if err is None or err.__class__ in (
            NetworkError,
            OSError,
            TimedOut,
            ConnectionError,
            Conflict,
            RetryAfter,
        ):
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
        tb = format_traceback(type(err), err, err.__traceback__)
        log_text = f"{err.__class__}\n{err}\ntraceback:\n{tb}"
        _LOGGER.error(log_text)
        text = Lang.t(Lang.UNKNOWN_ERROR) + f"\n{err.__class__}: {err}"
        await get_bot_instance().send_to(TelegramBot.get_master_id(), text)
    except Exception as _e:
        try:
            _LOGGER.error(format_traceback(type(_e), _e, _e.__traceback__))
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
            bot_data=self.BotDataType,  # type: ignore
        )
        from telegram.ext import Defaults

        defaults = Defaults(tzinfo=SYSTEM_TIME_ZONE)
        self.application = cast(
            "Application[ExtBot[None], RichCallbackContext, UserData, ChatData, dict, JobQueueEx]",
            Application.builder()
            # .application_class(ApplicationEx)
            .token(read_user_cfg(BasicConfig, "TOKEN"))
            .context_types(context_types)
            .job_queue(JobQueueEx())
            .post_init(self._do_post_init)
            .post_stop(self._do_post_stop)
            .defaults(defaults)
            .build(),
        )
        self.bot = self.application.bot
        assert self.application.updater is not None
        self.updater = self.application.updater
        assert self.application.job_queue is not None
        self.job_queue = self.application.job_queue
        #
        self.callback_manager = CallbackDataManager()
        self.callback_key_dict: Dict[Tuple[int, int], List[str]] = dict()
        self._custom_post_init_task: Awaitable | None = None
        self._custom_post_stop_task: Awaitable | None = None
        # TODO do a flags check at the end of the run. move the flags into a new class
        self._post_stop_restart_flag = False
        self._post_stop_gitpull_flag = bool(
            read_user_cfg(AntaresBotConfig, "PULL_WHEN_STOP")
        )
        self._custom_restart_command: str | list[str] | None = None
        self._custom_finalize_task: Callable[[], Any] | None = None
        self._normal_exit_flag = False
        self.handler_docs: dict[str, str] = {}
        self._exit_fast = False
        _patch_traceback = bool(read_user_cfg(AntaresBotConfig, "PATCH_TRACEBACK"))
        self._patch_traceback = _patch_traceback
        if _patch_traceback:
            traceback.format_exception = format_exception_with_local_vars
        self._show_stack_on_sigint = bool(
            read_user_cfg(AntaresBotConfig, "SHOW_STACK_ON_SIGINT")
        )
        # some pre-checks
        if self._is_debug_level():
            _LOGGER.debug(
                "Warning: the initial logging level is DEBUG. The built-in /debug_mode command will not work."
            )

    @property
    def bot_id(self):
        return self.bot.bot.id

    async def _do_post_init(self, app: Application):
        # use eager factory for python 3.12+
        if sys.version_info >= (3, 12):
            asyncio.get_running_loop().set_task_factory(asyncio.eager_task_factory)

        # bring the (pika) logger online and flush records buffered at import time
        await start_logger()

        await self.send_to(self.get_master_id(), Lang.t(Lang.STARTUP_PENDING))

        time0 = time.time()
        module_timings: dict[str, float] = {}

        async def timed_post_init(module_desc):
            t0 = time.time()
            await module_desc.post_init(app)
            t1 = time.time()
            module_timings[module_desc.top_name] = t1 - t0

        tasks: list[Awaitable] = [
            timed_post_init(module)
            for module in self._module_keeper.get_all_enabled_modules()
        ]
        if self._custom_post_init_task is not None:
            tasks.append(self._custom_post_init_task)
            self._custom_post_init_task = None

        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            try:
                _LOGGER.critical("Error when running post init: %s", str(e))
                _LOGGER.critical(format_traceback(type(e), e, e.__traceback__))
                await asyncio.sleep(3)
                self.signal_stop(signal.SIGABRT)
            except Exception:
                sys.exit(-1)
            return

        time1 = time.time()

        await self.send_to(self.get_master_id(), Lang.t(Lang.STARTUP_COMPLETE))
        total_time = time1 - time0
        timing_lines = "\n".join(
            f"  {name}: {elapsed:.3f}s"
            for name, elapsed in sorted(
                module_timings.items(), key=lambda x: x[1], reverse=True
            )
        )
        _LOGGER.warning("Post init time (total: %.3fs):\n%s", total_time, timing_lines)

    async def _do_post_stop(self, app: Application):
        _LOGGER.warning("Started post stop...")
        time0 = time.time()
        if self._custom_post_stop_task is not None:
            await self._custom_post_stop_task
            self._custom_post_stop_task = None
        task_send_exit_msg = self.send_to(
            self.get_master_id(), Lang.t(Lang.SHUTDOWN_GOODBYTE)
        )
        module_timings: dict[str, float] = {}

        async def timed_do_stop(module_desc):
            t0 = time.time()
            await module_desc.do_stop()
            t1 = time.time()
            module_timings[module_desc.top_name] = t1 - t0

        try:
            await asyncio.gather(
                *(
                    timed_do_stop(module)
                    for module in self._module_keeper.get_all_enabled_modules()
                )
            )
        except Exception as e:
            try:
                _LOGGER.critical("Error when running post stop: %s", str(e))
                _LOGGER.critical(format_traceback(type(e), e, e.__traceback__))
                time.sleep(3)
            except Exception:
                pass
            sys.exit(-1)
        time1 = time.time()
        total_time = time1 - time0
        timing_lines = "\n".join(
            f"  {name}: {elapsed:.3f}s"
            for name, elapsed in sorted(
                module_timings.items(), key=lambda x: x[1], reverse=True
            )
        )
        _LOGGER.warning("Post stop time (total: %.3fs):\n%s", total_time, timing_lines)
        task_stop_db = DataBasesManager.get_inst().shutdown()
        # pull the repo if _post_stop_gitpull_flag is set.
        # if exit_fast (SIGTERM, SIGABRT), do not pull
        additional_tasks = []
        if self._post_stop_gitpull_flag and not self._exit_fast:
            # create a subprocess to git pull
            msg = None
            try:
                msg = str(
                    subprocess.check_output(
                        ["git", "pull", "--ff-only"], encoding="utf-8"
                    )
                )
                if (
                    msg
                    and "Already up to date." not in msg
                    and "not a git repository" not in msg
                ):
                    additional_tasks.append(self.send_to(self.get_master_id(), msg))
            except Exception:
                _LOGGER.error("Error when running pull when post stop: %s", str(msg))
                additional_tasks.append(
                    self.send_to(self.get_master_id(), "git pull failed!")
                )
        # wait for all tasks to finish
        time0 = time.time()
        await asyncio.gather(task_send_exit_msg, task_stop_db, *additional_tasks)
        time1 = time.time()
        _LOGGER.warning("Finalize time: %.3fs", time1 - time0)
        await stop_logger()

    def custom_post_init(self, task: Awaitable):
        self._custom_post_init_task = task

    def custom_post_stop(self, task: Awaitable):
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
                logger.info("added handler: %s", func)

        self.handler_docs["cancel"] = """
        cancel - cancel the current operation
        `/cancel`: Cancel the current operation.
        """

        self.application.add_error_handler(exception_handler)

        self.job_queue.run_daily(
            self._daily_job,
            time=datetime.time(hour=0, minute=0, tzinfo=SYSTEM_TIME_ZONE),
            name="daily_job",
        )

        signal.signal(signal.SIGINT, self.signal_stop)
        signal.signal(signal.SIGTERM, self.signal_stop)
        signal.signal(signal.SIGABRT, self.signal_stop)

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
        except Exception:
            print("Fatal error occured, exiting!")
            traceback.print_exc()
            sys.exit(1)

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
                restart_command = (
                    ["systemctl"]
                    + (["--user"] if not is_root else [])
                    + ["restart", systemd_service_name]
                )
                restart_command = " ".join(restart_command)
            else:
                # create a detached subprocess to restart the bot
                restart_command = (
                    self._custom_restart_command
                    if self._custom_restart_command is not None
                    else sys.orig_argv
                )
                if isinstance(restart_command, list):
                    import shlex

                    restart_command = shlex.join(restart_command)
                restart_command = f"{restart_command} & disown"
            try:
                subprocess.Popen(restart_command, shell=True)
                print(f"Restarting the bot with command: {restart_command}")
            except Exception:
                # cannot use logger here, the logger is stopped
                print(
                    f"Failed to restart the bot with command: {restart_command}",
                    file=sys.stderr,
                )
                raise
            self._exit_fast = True

        if self._normal_exit_flag:
            print("Stopped gracefully.")
            if self._exit_fast:
                print("Exiting immediately since exit_fast flag is set.")
                sys.stdout.close()
                sys.stderr.close()
                sys.exit(0)
            # shutdown the stdout and stderr since the aiormq will still be printing rabbish
            sys.stdout.close()
            sys.stderr.close()
        else:
            print("Stopped unexpectedly.", file=sys.stderr)
            if self._exit_fast:
                print(
                    "Exiting immediately with error code 1 since exit_fast flag is set."
                )
                sys.exit(1)

    def true_stop(self, *args, **kwargs):
        self._normal_exit_flag = True
        self._guard_stop()
        self.application.stop_running()

    def signal_stop(self, sig, *args, **kwargs):
        global _PROGRAM_SHUTDOWN_STARTED
        if _PROGRAM_SHUTDOWN_STARTED:
            print("Shutdown requested repeatedly, exit now!")
            sys.exit(0 if self._normal_exit_flag else 1)
        _PROGRAM_SHUTDOWN_STARTED = True
        _LOGGER.warning(
            "Application received stop signal %s. Shutting down.",
            signal.Signals(sig).name,
        )
        if sig in (signal.SIGTERM, signal.SIGABRT):
            self._exit_fast = True
        elif sig == signal.SIGINT and self._show_stack_on_sigint:
            # remove current frame by default
            self.log_stacktrace(remove_stack_depth=1)
        self.true_stop()

    def _get_log_stacktrace(self, remove_stack_depth=2) -> list[str]:
        stacktrace_lst: list[types.FrameType] = []
        f = sys._getframe().f_back  # pylint: disable=W0212
        while f is not None:
            stacktrace_lst.append(f)
            f = f.f_back
        stacktrace_lst.reverse()
        #
        if len(stacktrace_lst) >= remove_stack_depth:
            stacktrace_lst = stacktrace_lst[:-remove_stack_depth]
        stop_index = None
        for i, f in enumerate(stacktrace_lst):
            funcname = f.f_code.co_name
            if funcname == "run_polling":
                stop_index = i - 1
        if stop_index is not None and stop_index > 0:
            stacktrace_lst = stacktrace_lst[stop_index:]
        del stop_index
        #
        log_lines: list[str] = ["[_get_log_stacktrace] Printing frames:"]
        for f in stacktrace_lst:
            lineno = f.f_lineno
            filename = f.f_code.co_filename
            funcname = f.f_code.co_name
            log_lines.append(
                '  File "{}", line {}, in {}'.format(filename, lineno, funcname)
            )
            if self._patch_traceback:
                frame_locals = f.f_locals
                if frame_locals and len(frame_locals) > 0:
                    log_lines.append("    Local variables:")
                for k, v in frame_locals.items():
                    log_lines.append("      " + format_local_value(k, v))
        return log_lines

    def log_stacktrace(self, remove_stack_depth=1):
        try:
            log_stacktrace_content = self._get_log_stacktrace(remove_stack_depth + 1)
        except Exception as e:
            _LOGGER.error("Call _get_log_stacktrace() failed with exception: %s", e)
            return
        _LOGGER.warning("\n".join(log_stacktrace_content))

    @staticmethod
    def _guard_stop():
        pid = os.getpid()
        start_time = int(
            subprocess.check_output(
                "awk '{print $22}' " + f"/proc/{pid}/stat", shell=True, encoding="utf-8"
            )
        )
        sub_pid = os.fork()
        if sub_pid == 0:
            execute_shell = """
            sleep 10
            start_time=$(awk '{print $22}' /proc/%s/stat 2>/dev/null)
            if [ -n "$start_time" ] && [ $start_time -eq %s ]; then
                echo "process still running, kill with SIGKILL"
                kill -KILL %s
            fi
            rm "%s"
            """
            os.setsid()
            fd, name = tempfile.mkstemp()
            os.write(fd, (execute_shell % (pid, start_time, pid, name, name)).encode())
            os.close(fd)
            os.execvp("bash", ["bash", name])

    @property
    def exit_fast(self):
        return self._exit_fast

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

    @classmethod
    def data_dir(cls):
        return os.path.join(os.path.curdir, read_user_cfg(BasicConfig, "DATA_DIR"))

    async def _daily_job(self, context: RichCallbackContext):
        is_debug = self._is_debug_level()
        if is_debug:
            _debug_ids = []
        for old_id in self.callback_manager.history.pop_before_keys(
            time.time() - TIME_IN_A_DAY
        ):
            self.callback_manager.pop_data(old_id)
            if is_debug:
                _debug_ids.append(old_id)
        if is_debug:
            _LOGGER.debug(
                "Daily job: removed %s keys from callback manager", _debug_ids
            )
        #
        _LOGGER.warning("Start running daily jobs for each module")
        with ContextReverseHelper():
            await asyncio.gather(
                *(
                    module.module_instance.daily_job()
                    for module in self._module_keeper.get_all_enabled_modules()
                    if module.module_instance is not None
                )
            )


__bot_singleton = None


def destroy_bot_instance():
    global __bot_singleton
    if __bot_singleton is not None:
        __bot_singleton.true_stop()
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
