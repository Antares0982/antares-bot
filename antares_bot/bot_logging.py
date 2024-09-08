import asyncio
import logging
import sys
import threading
from collections import defaultdict
from copy import deepcopy
from importlib.util import find_spec
from logging import Handler, getLevelName
from types import GenericAlias
from typing import TYPE_CHECKING, Any, Optional, cast

from antares_bot.bot_default_cfg import AntaresBotConfig, BasicConfig
from antares_bot.init_hooks import read_user_cfg

if TYPE_CHECKING:
    from aio_pika.connection import AbstractChannel, AbstractConnection


class SustainedChannel:
    conn: "AbstractConnection"
    channel: "AbstractChannel"

    @classmethod
    async def create(cls, **kwargs):
        ret = cls()
        from aio_pika import connect_robust
        cls.conn = await connect_robust(**kwargs)
        cls.channel = await cls.conn.channel()
        return ret

    async def close(self):
        await self.channel.close()
        await self.conn.close()


class GlobalLoggerOptions:
    INST: "GlobalLoggerOptions | None" = None

    def __init__(self, logger_top_name: str):
        self.logger_top_name = logger_top_name
        self._root_logger: logging.Logger | None = None
        self.pika_enabled = False

    @property
    def root_logger(self) -> logging.Logger:
        return self._root_logger  # type: ignore

    def set_root_logger(self, logger: logging.Logger):
        self._root_logger = logger


class PikaGlobalLoggerOptions(GlobalLoggerOptions):
    def __init__(self, logger_top_name: str):
        super().__init__(logger_top_name)
        self.pika_enabled = True
        self.pika_handler: PikaHandler = None  # type: ignore
        #
        self.loops_lock = threading.Lock()
        self.running_channels_lock: defaultdict[asyncio.AbstractEventLoop, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.running_channels: dict[asyncio.AbstractEventLoop, SustainedChannel] = dict()

    def set_pika_handler(self, handler: "PikaHandler"):
        self.pika_handler = handler

    async def _get_channel(self):
        loop = asyncio.get_running_loop()
        with self.loops_lock:
            cur_lock = self.running_channels_lock[loop]
            chan = self.running_channels.get(loop)
        if chan is None:
            # this does not happen frequently
            async with cur_lock:  # this prevents dead lock on acquiring self.loops_lock
                with self.loops_lock:
                    # get again to avoid competition between threads
                    chan = self.running_channels.get(loop)
                    # release immediately to avoid blocking other threads
                if chan is None:
                    # since cur_lock is locked, no other _get_channel() call on current thread will enter here
                    kw = _get_pika_connection_kw()
                    chan = await SustainedChannel.create(**kw)
                    with self.loops_lock:
                        self.running_channels[loop] = chan
        return chan.channel

    async def send_message(
        self,
        routing_key: str,
        message: str | bytes,
    ):
        from aio_pika import ExchangeType, Message
        from aio_pika.channel import ChannelInvalidStateError
        channel = await self._get_channel()
        #
        exchange_name = routing_key.split('.')[0]
        exchange = await channel.declare_exchange(name=exchange_name, type=ExchangeType.TOPIC)
        try:
            await exchange.publish(
                Message(message.encode() if isinstance(message, str) else message),
                routing_key=routing_key
            )
        except ChannelInvalidStateError:
            pass

    def send_message_nowait(
        self,
        routing_key: str,
        message: str | bytes,
    ):
        """
        Send a message, without blocking wait.
        If `channel` is not passed, use the global connection to get channel.
        If `loop` is not passed, use the running loop.
        """
        asyncio.get_running_loop().create_task(self.send_message(routing_key, message))


class PikaHandler(Handler):
    def emit(self, record):
        if _is_pika_logger_running():
            try:
                msg = self.format(record)
                key = record.name
                pika_global_opt = cast(PikaGlobalLoggerOptions, GlobalLoggerOptions.INST)
                logger_top_name = pika_global_opt.logger_top_name
                if not key.startswith(logger_top_name):
                    key = logger_top_name + "." + key
                pika_global_opt.send_message_nowait("logging." + key, msg)
            except RecursionError:  # See issue 36272
                raise
            except Exception:
                self.handleError(record)

    def __repr__(self):
        level = getLevelName(self.level)
        name = self.name
        #  bpo-36015: name can be an int
        name = str(name)
        if name:
            name += ' '
        return '<%s %s(%s)>' % (self.__class__.__name__, name, level)

    __class_getitem__ = classmethod(GenericAlias)  # type: ignore


def _get_pika_connection_kw() -> dict[str, Any]:
    pika_config: dict | None = read_user_cfg(AntaresBotConfig, "PIKA_CONFIG")
    if pika_config is not None:
        return deepcopy(pika_config)
    else:
        return dict()


def _check_enable_pika() -> bool:
    if find_spec("aio_pika") is None:
        print(
            "Pika not supported due to an ImportError."
            " Safely ignore it if you do not use pika. You can set PIKA_LOGGER_ENABLED in AntaresBotConfig to False."
            " Check whether aio-pika is installed if you use pika.",
            file=sys.stderr
        )
        return False

    # aio_pika can be imported.
    # Check if connection can be established
    kw = _get_pika_connection_kw()

    loop = asyncio.new_event_loop()
    chan = None
    try:
        chan = loop.run_until_complete(SustainedChannel.create(**kw))
        print(
            "Test RabbitMQ connection established successfully."
            " You can set PIKA_LOGGER_ENABLED to True to avoid this costly runtime check.",
            file=sys.stderr
        )
        return True
    except Exception:
        print(
            "Pika not supported due to an exception when trying to connect."
            " Safely ignore it if you do not use pika. You can set PIKA_LOGGER_ENABLED in AntaresBotConfig to False."
            " Check whether the rabbitmq server is setup, and the configurations are correct if you use pika.",
            file=sys.stderr
        )
        return False
    finally:
        if chan is not None:
            try:
                loop.run_until_complete(chan.close())
            except Exception:
                pass
            chan = None
        loop.close()


def _is_pika_logger_running():
    return GlobalLoggerOptions.INST is not None


def _log_start(logger_top_name: Optional[str] = None) -> logging.Logger:
    """
    The main entrance of creating logger.
    """
    # global __logger_inited, __root_logger, _logger_top_name
    if GlobalLoggerOptions.INST is not None:
        return GlobalLoggerOptions.INST.root_logger
    if logger_top_name is None:
        logger_top_name = "antares_bot"

    pika_enabled: bool | None = read_user_cfg(AntaresBotConfig, "PIKA_LOGGER_ENABLED")
    if pika_enabled is None:
        pika_enabled = _check_enable_pika()
    # if PIKA_LOGGER_ENABLED is specified to `True` or `False`, skip runtime checking

    if pika_enabled:
        logger_options_inst: GlobalLoggerOptions = PikaGlobalLoggerOptions(logger_top_name)
    else:
        logger_options_inst = GlobalLoggerOptions(logger_top_name)
    GlobalLoggerOptions.INST = logger_options_inst

    root_logger = logging.getLogger(logger_top_name)
    logger_options_inst.set_root_logger(root_logger)

    if pika_enabled:
        handler = PikaHandler()
        cast(PikaGlobalLoggerOptions, logger_options_inst).set_pika_handler(handler)
        root_logger.addHandler(handler)
        # add handler to telegram internal logger
        logging.getLogger("telegram").addHandler(handler)
        # add handler to apscheduler internal logger
        logging.getLogger("apscheduler").addHandler(handler)
    return root_logger


def get_logger(module_name: str):
    strip_prefix = "modules."
    if module_name.startswith(strip_prefix):
        module_name = module_name[len(strip_prefix):]
    if GlobalLoggerOptions.INST is None:
        raise RuntimeError("logger not inited")
    logger_top_name = GlobalLoggerOptions.INST.logger_top_name
    name = logger_top_name + "." + module_name
    logger = logging.getLogger(name)
    return logger


def add_pika_log_handler(logger: str | logging.Logger) -> bool:
    """
    Add pika handler for the logger.
    One should only add pika handler to the logger after the logger is initialized.
    The handler will take effect for the logger and all its children.
    """
    inst = GlobalLoggerOptions.INST
    if not inst:
        raise RuntimeError("logger not inited")
    if not inst.pika_enabled:
        print("Pika not supported, add_pika_log_handler has no effect.")
        return False
    if isinstance(logger, str):
        logger = logging.getLogger(logger)
    handler = cast(PikaGlobalLoggerOptions, inst).pika_handler
    logger.addHandler(handler)
    return True


def get_root_logger():
    if GlobalLoggerOptions.INST is None:
        raise RuntimeError("root logger not inited")
    return GlobalLoggerOptions.INST.root_logger


def stop_logger():
    if GlobalLoggerOptions.INST is None:
        return
    inst = GlobalLoggerOptions.INST
    GlobalLoggerOptions.INST = None
    if inst.pika_enabled:
        inst_pika = cast(PikaGlobalLoggerOptions, inst)
        for loop, chan in inst_pika.running_channels.items():
            try:
                loop.create_task(chan.close())
            except Exception:
                pass
        inst_pika.running_channels.clear()


_log_start(read_user_cfg(BasicConfig, "BOT_NAME"))
