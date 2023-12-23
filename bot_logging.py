import logging
import sys
from logging import Handler, getLevelName
from types import GenericAlias
from typing import Optional


try:
    from rabbitmq_interface import PikaMessageQueue

    __pika_msg_queue = PikaMessageQueue()
    PIKA_SUPPORTED = True
except ImportError:
    PIKA_SUPPORTED = False

__logger_top_name = "TelegramBot"

if PIKA_SUPPORTED:
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
                __pika_msg_queue.push("logging." + self.name, msg)
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


def log_start(logger_top_name: Optional[str] = None):
    if logger_top_name is not None:
        global __logger_top_name
        __logger_top_name = logger_top_name
    top_logger = logging.getLogger(logger_top_name)
    if PIKA_SUPPORTED:
        top_logger.addHandler(PikaHandler())


def get_logger(module_name: str):
    logger = logging.getLogger(__logger_top_name + "." + module_name)
    if PIKA_SUPPORTED:
        logger.addHandler(PikaHandler())
    return logger
