import asyncio
import logging
import sys
from collections import deque
from copy import deepcopy
from importlib.util import find_spec
from logging import Handler, getLevelName
from types import GenericAlias
from typing import TYPE_CHECKING, Any, Optional, cast

from antares_bot.bot_default_cfg import AntaresBotConfig, BasicConfig
from antares_bot.init_hooks import read_user_cfg

if TYPE_CHECKING:
    from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractExchange


# Sentinel pushed onto the queue to tell the consumer to drain and exit.
_SENTINEL = object()
# Upper bound for both the pre-start buffer and the live queue. Logging must
# never grow memory without bound, so records beyond this are dropped.
_MAX_BUFFER = 100000


class SustainedChannel:
    def __init__(self):
        self.conn: "AbstractConnection | None" = None
        self.channel: "AbstractChannel | None" = None

    @classmethod
    async def create(cls, **kwargs) -> "SustainedChannel":
        from aio_pika import connect_robust

        ret = cls()
        ret.conn = await connect_robust(**kwargs)
        ret.channel = await ret.conn.channel()
        return ret

    async def close(self):
        if self.channel is not None:
            await self.channel.close()
        if self.conn is not None:
            await self.conn.close()


class GlobalLoggerInstance:
    INST: "GlobalLoggerInstance | None" = None

    def __init__(self, logger_top_name: str):
        self.logger_top_name = logger_top_name
        self._root_logger: logging.Logger | None = None
        self.pika_enabled = False

    @property
    def root_logger(self) -> logging.Logger:
        return self._root_logger  # type: ignore

    def set_root_logger(self, logger: logging.Logger):
        self._root_logger = logger


class PikaGlobalLoggerInstance(GlobalLoggerInstance):
    """
    Publishes log records to RabbitMQ over a single connection on the bot's
    main event loop. It never creates an event loop of its own and never blocks
    the calling thread: ``emit`` only enqueues, and a single consumer task does
    the awaiting.

    Lifecycle:
      * at import time the instance exists but the loop is not running yet, so
        records are buffered in ``_prestart``;
      * ``start()`` (called from post-init, on the running loop) opens the
        connection, flushes the buffer and starts the consumer;
      * ``stop()`` drains the queue and closes the connection.
    """

    def __init__(self, logger_top_name: str, needs_runtime_check: bool):
        super().__init__(logger_top_name)
        self.pika_enabled = True
        self.pika_handler: PikaHandler = None  # type: ignore
        self._needs_runtime_check = needs_runtime_check
        # set once the loop is running; until then enqueue() buffers
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.Queue | None = None
        self._consumer: asyncio.Task | None = None
        self._prestart: deque[tuple[str, str]] = deque(maxlen=_MAX_BUFFER)
        self._disabled = False
        # one persistent connection/channel, with declared exchanges cached
        self._sustained: SustainedChannel | None = None
        self._channel: "AbstractChannel | None" = None
        self._exchanges: dict[str, "AbstractExchange"] = dict()

    def set_pika_handler(self, handler: "PikaHandler"):
        self.pika_handler = handler

    # ------------------------------------------------------------------ emit

    def enqueue(self, routing_key: str, msg: str):
        """Non-blocking, thread-safe hand-off. Called from any thread."""
        if self._disabled:
            return
        loop = self._loop
        if loop is None:
            # loop not ready yet (import / early start-up): buffer the record
            self._prestart.append((routing_key, msg))
            return
        if loop.is_closed():
            return
        try:
            loop.call_soon_threadsafe(self._put_nowait, routing_key, msg)
        except RuntimeError:
            # loop is shutting down
            pass

    def _put_nowait(self, routing_key: str, msg: str):
        try:
            self._queue.put_nowait((routing_key, msg))  # type: ignore[union-attr]
        except asyncio.QueueFull:
            pass

    # ------------------------------------------------------------- lifecycle

    async def start(self):
        # Optional one-shot connectivity probe when PIKA_LOGGER_ENABLED was not
        # explicitly set. Done on the running loop, so no extra loop is created.
        if self._needs_runtime_check:
            try:
                await self._ensure_channel()
            except Exception:
                print(
                    "Pika not supported due to an exception when trying to connect."
                    " Safely ignore it if you do not use pika. You can set PIKA_LOGGER_ENABLED in AntaresBotConfig to False."
                    " Check whether the rabbitmq server is setup, and the configurations are correct if you use pika.",
                    file=sys.stderr,
                )
                self._disabled = True
                self._prestart.clear()
                return

        # Atomic switch from buffering to live: no `await` between flushing the
        # buffer and publishing self._loop, so ordering is preserved.
        loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue(maxsize=_MAX_BUFFER)
        while self._prestart:
            try:
                self._queue.put_nowait(self._prestart.popleft())
            except asyncio.QueueFull:
                self._prestart.clear()
                break
        self._loop = loop
        self._consumer = loop.create_task(self._consume())

    async def stop(self):
        consumer = self._consumer
        if self._loop is not None and self._queue is not None and consumer is not None:
            self._queue.put_nowait(("", _SENTINEL))  # type: ignore[arg-type]
            try:
                await asyncio.wait_for(asyncio.shield(consumer), timeout=5)
            except Exception:
                consumer.cancel()
            self._consumer = None
        await self._close_channel()

    async def _close_channel(self):
        if self._sustained is not None:
            try:
                await self._sustained.close()
            except Exception:
                pass
        self._sustained = None
        self._channel = None
        self._exchanges.clear()

    # --------------------------------------------------------------- consume

    async def _consume(self):
        queue = cast(asyncio.Queue, self._queue)
        while True:
            routing_key, msg = await queue.get()
            if msg is _SENTINEL:
                return
            try:
                await self._publish(routing_key, msg)
            except Exception:
                # drop the record and force a reconnect on the next one
                await self._close_channel()

    async def _ensure_channel(self) -> "AbstractChannel":
        if self._channel is None:
            sc = await SustainedChannel.create(**_get_pika_connection_kw())
            self._sustained = sc
            self._channel = sc.channel
            self._exchanges.clear()
        return self._channel  # type: ignore[return-value]

    async def _publish(self, routing_key: str, msg: str | bytes):
        from aio_pika import ExchangeType, Message

        channel = await self._ensure_channel()
        exchange_name = routing_key.split(".")[0]
        exchange = self._exchanges.get(exchange_name)
        if exchange is None:
            exchange = await channel.declare_exchange(
                name=exchange_name, type=ExchangeType.TOPIC
            )
            self._exchanges[exchange_name] = exchange
        body = msg.encode() if isinstance(msg, str) else msg
        await exchange.publish(Message(body), routing_key=routing_key)


class PikaHandler(Handler):
    def emit(self, record):
        inst = GlobalLoggerInstance.INST
        if inst is None or not inst.pika_enabled:
            return
        try:
            msg = self.format(record)
            key = record.name
            pika_global_opt = cast(PikaGlobalLoggerInstance, inst)
            logger_top_name = pika_global_opt.logger_top_name
            if not key.startswith(logger_top_name):
                key = logger_top_name + "." + key
            pika_global_opt.enqueue("logging." + key, msg)
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
            name += " "
        return "<%s %s(%s)>" % (self.__class__.__name__, name, level)

    __class_getitem__ = classmethod(GenericAlias)  # type: ignore


def _get_pika_connection_kw() -> dict[str, Any]:
    pika_config: dict | None = read_user_cfg(AntaresBotConfig, "PIKA_CONFIG")
    if pika_config is not None:
        return deepcopy(pika_config)
    else:
        return dict()


def _pika_importable() -> bool:
    if find_spec("aio_pika") is None:
        print(
            "Pika not supported due to an ImportError."
            " Safely ignore it if you do not use pika. You can set PIKA_LOGGER_ENABLED in AntaresBotConfig to False."
            " Check whether aio-pika is installed if you use pika.",
            file=sys.stderr,
        )
        return False
    return True


def _log_start(logger_top_name: Optional[str] = None) -> logging.Logger:
    """
    The main entrance of creating logger.
    """
    if GlobalLoggerInstance.INST is not None:
        return GlobalLoggerInstance.INST.root_logger
    if logger_top_name is None:
        logger_top_name = "antares_bot"

    pika_enabled_cfg: bool | None = read_user_cfg(
        AntaresBotConfig, "PIKA_LOGGER_ENABLED"
    )
    if pika_enabled_cfg is False:
        pika_enabled = False
        needs_runtime_check = False
    elif not _pika_importable():
        pika_enabled = False
        needs_runtime_check = False
    else:
        # explicit True -> trust it; None -> probe the connection in start()
        pika_enabled = True
        needs_runtime_check = pika_enabled_cfg is None

    if pika_enabled:
        logger_options_inst: GlobalLoggerInstance = PikaGlobalLoggerInstance(
            logger_top_name, needs_runtime_check
        )
    else:
        logger_options_inst = GlobalLoggerInstance(logger_top_name)
    GlobalLoggerInstance.INST = logger_options_inst

    root_logger = logging.getLogger(logger_top_name)
    logger_options_inst.set_root_logger(root_logger)

    if pika_enabled:
        handler = PikaHandler()
        cast(PikaGlobalLoggerInstance, logger_options_inst).set_pika_handler(handler)
        root_logger.addHandler(handler)
        # add handler to telegram internal logger
        logging.getLogger("telegram").addHandler(handler)
        # add handler to apscheduler internal logger
        logging.getLogger("apscheduler").addHandler(handler)
    return root_logger


def get_logger(module_name: str):
    strip_prefix = "modules."
    if module_name.startswith(strip_prefix):
        module_name = module_name[len(strip_prefix) :]
    if GlobalLoggerInstance.INST is None:
        raise RuntimeError("logger not inited")
    logger_top_name = GlobalLoggerInstance.INST.logger_top_name
    name = logger_top_name + "." + module_name
    logger = logging.getLogger(name)
    return logger


def add_pika_log_handler(logger: str | logging.Logger) -> bool:
    """
    Add pika handler for the logger.
    One should only add pika handler to the logger after the logger is initialized.
    The handler will take effect for the logger and all its children.
    """
    inst = GlobalLoggerInstance.INST
    if not inst:
        raise RuntimeError("logger not inited")
    if not inst.pika_enabled:
        print("Pika not supported, add_pika_log_handler has no effect.")
        return False
    if isinstance(logger, str):
        logger = logging.getLogger(logger)
    handler = cast(PikaGlobalLoggerInstance, inst).pika_handler
    logger.addHandler(handler)
    return True


def get_root_logger():
    if GlobalLoggerInstance.INST is None:
        raise RuntimeError("root logger not inited")
    return GlobalLoggerInstance.INST.root_logger


async def start_logger():
    """Bring the pika logger online. Call once the main event loop is running."""
    inst = GlobalLoggerInstance.INST
    if inst is None or not inst.pika_enabled:
        return
    await cast(PikaGlobalLoggerInstance, inst).start()


async def stop_logger():
    inst = GlobalLoggerInstance.INST
    if inst is None:
        return
    GlobalLoggerInstance.INST = None
    if inst.pika_enabled:
        await cast(PikaGlobalLoggerInstance, inst).stop()


_log_start(read_user_cfg(BasicConfig, "BOT_NAME"))
