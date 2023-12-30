import logging
import threading
from logging import Handler, getLevelName
from types import GenericAlias
from typing import Optional, cast


try:
    from rabbitmq_interface import PikaMessageQueue

    PIKA_SUPPORTED = True
except ImportError:
    PIKA_SUPPORTED = False

__logger_top_name = "TelegramBot"
__logger_inited = False
__root_logger = None


if PIKA_SUPPORTED:
    _pika_msg_queue = PikaMessageQueue()

    class PikaHandler(Handler):
        def emit(self, record):
            """
            Emit a record.

            If a formatter is specified, it is used to format the record.
            The record is then written to the stream with a trailing newline.  If
            exception information is present, it is formatted using
            traceback.print_exception and appended to the stream.  If the stream
            has an 'encoding' attribute, it is used to determine how to do the
            output to the stream.
            """
            try:
                msg = self.format(record)
                _pika_msg_queue.push("logging." + self.name, msg)
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


def log_start(logger_top_name: Optional[str] = None) -> logging.Logger:
    global __logger_inited, __root_logger
    if __logger_inited:
        return cast(logging.Logger, __root_logger)
    __logger_inited = True
    if logger_top_name is not None:
        global __logger_top_name
        __logger_top_name = logger_top_name

    __root_logger = logging.getLogger(__logger_top_name)
    if PIKA_SUPPORTED:
        threading.Thread(target=_pika_msg_queue.run).start()
    return __root_logger


def get_logger(module_name: str):
    if not __logger_inited:
        raise RuntimeError("logger not inited")
    name = __logger_top_name + "." + module_name
    logger = logging.getLogger(name)
    if PIKA_SUPPORTED:
        handler = PikaHandler()
        handler.name = name
        logger.addHandler(handler)
    return logger


def get_root_logger():
    if not __logger_inited:
        raise RuntimeError("logger not inited")
    return __root_logger


def stop_logger():
    if PIKA_SUPPORTED:
        _pika_msg_queue.stop()
