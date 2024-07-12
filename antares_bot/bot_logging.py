import logging
from logging import Handler, getLevelName
from types import GenericAlias
from typing import Optional, cast

from antares_bot.bot_default_cfg import BasicConfig
from antares_bot.init_hooks import read_user_cfg


try:
    from pika_interface import close_sustained_connection, send_message_nowait

    PIKA_SUPPORTED = True
    __pika_logger_stopped = False
except ImportError:
    print(
        "Pika not supported due to an ImportError."
        " Safely ignore it if you do not use pika."
        " Check whether aio-pika is installed if you use pika."
    )
    PIKA_SUPPORTED = False

_logger_top_name = "antares_bot"
__logger_inited = False
__root_logger = cast(logging.Logger, None)


if PIKA_SUPPORTED:
    import threading

    def _is_pika_logger_running():
        if not (threading.current_thread() is threading.main_thread()):
            return False
        return not __pika_logger_stopped

    class PikaHandler(Handler):
        def emit(self, record):
            if _is_pika_logger_running():
                try:
                    msg = self.format(record)
                    key = record.name
                    if not key.startswith(_logger_top_name):
                        key = _logger_top_name + "." + key
                    send_message_nowait("logging." + key, msg)
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


def _log_start(logger_top_name: Optional[str] = None) -> logging.Logger:
    global __logger_inited, __root_logger, _logger_top_name
    if __logger_inited:
        return __root_logger
    __logger_inited = True
    if logger_top_name is not None:
        _logger_top_name = logger_top_name

    __root_logger = logging.getLogger(_logger_top_name)
    if PIKA_SUPPORTED:
        handler = PikaHandler()
        __root_logger.addHandler(handler)
        # add handler to telegram internal logger
        tg_logger = logging.getLogger("telegram")
        tg_logger.addHandler(handler)
        # add handler to apscheduler internal logger
        apscheduler_logger = logging.getLogger("apscheduler")
        apscheduler_logger.addHandler(handler)
    return __root_logger


def get_logger(module_name: str):
    strip_prefix = "modules."
    if module_name.startswith(strip_prefix):
        module_name = module_name[len(strip_prefix):]
    if not __logger_inited:
        raise RuntimeError("logger not inited")
    name = _logger_top_name + "." + module_name
    logger = logging.getLogger(name)
    return logger


def add_pika_log_handler(logger: str | logging.Logger) -> bool:
    """
    Add pika handler for the logger.
    One should only add pika handler to the logger after the logger is initialized.
    The handler will take effect for the logger and all its children.
    """
    if not PIKA_SUPPORTED:
        print("Pika not supported, add_pika_log_handler has no effect.")
        return False
    if isinstance(logger, str):
        logger = logging.getLogger(logger)
    added = False
    for handler in __root_logger.handlers:
        if isinstance(handler, PikaHandler):
            logger.addHandler(handler)
            added = True
            break
    return added


def get_root_logger():
    if not __logger_inited:
        raise RuntimeError("logger not inited")
    return __root_logger


async def stop_logger():
    if PIKA_SUPPORTED:
        global __pika_logger_stopped
        __pika_logger_stopped = True
        await close_sustained_connection()


_log_start(read_user_cfg(BasicConfig, "BOT_NAME"))
