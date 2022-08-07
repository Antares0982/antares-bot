# region import
import os
import sqlite3
import subprocess
import threading
import time
import traceback
from signal import SIGINT
from typing import Dict, List, Optional, overload

from telegram import Bot, CallbackQuery, InlineKeyboardMarkup, Update
from telegram.error import BadRequest, NetworkError, TimedOut
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)

from utils import *

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from main_bot import mainBot
# endregion

# region classes


class botLocks(object):
    """
    修改这个类的定义，确定需要的lock.
    不同的操作应当使用不同的lock，在__slots__中需要添加它对应的名称，
    或者直接删掉__slots__.
    已经定义好的:class:`delayLock`类用于在with语句结束时延迟释放锁，
    可以在此使用。
    """

    def __init__(self) -> None:
        self.filelock = threading.Lock()
        self.botlock = threading.Lock()
        # add new locks here


# endregion


class baseBot(object):
    def __init__(self) -> None:
        if proxy:
            self.updater = Updater(
                token=token, use_context=True, request_kwargs={"proxy_url": proxy_url}
            )
        else:
            self.updater = Updater(token=token, use_context=True)

        self.bot: Bot = self.updater.bot
        self.workingMethod: Dict[int, str] = {}  # key为chat_id，而非user.id

        # self.lastchat: int = MYID
        # self.lastuser: int = MYID
        # self.lastmsgid: int = -1  # 默认-1，如果是按钮响应需要调整到-1
        self.blacklist: List[int] = []
        self.readblacklist()
        self.debug = False
        self.lock = threading.Lock()
