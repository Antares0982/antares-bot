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

    @property
    def lastchat(self) -> int:
        raise RuntimeError("不可调用bot instance的lastchat")

    @property
    def lastuser(self) -> int:
        raise RuntimeError("不可调用bot instance的lastuser")

    @property
    def lastmsgid(self) -> int:
        raise RuntimeError("不可调用bot instance的lastmsgid")

    @lastchat.setter
    def lastchat(self, v):
        raise RuntimeError("不可为bot instance的lastchat赋值")

    @lastuser.setter
    def lastuser(self, v):
        raise RuntimeError("不可为bot instance的lastuser赋值")

    @lastmsgid.setter
    def lastmsgid(self, v):
        raise RuntimeError("不可为bot instance的lastmsgid赋值")

    def start(self) -> None:
        self.importHandlers()
        self.reply(MYID, "Bot is live!")
        self.updater.start_polling(drop_pending_updates=True)
        self.updater.idle()

    def readblacklist(self):
        self.blacklist = []
        conn = sqlite3.connect(blacklistdatabase)
        c = conn.cursor()
        cur = c.execute("SELECT * FROM BLACKLIST;")
        ans = cur.fetchall()
        conn.close()
        for tgid in ans:
            self.blacklist.append(tgid)

    def addblacklist(self, id: int):
        if id in self.blacklist:
            return
        self.blacklist.append(id)
        conn = sqlite3.connect(blacklistdatabase)
        c = conn.cursor()
        c.execute(
            f"""INSERT INTO BLACKLIST(TGID)
        VALUES({id});"""
        )
        conn.commit()
        conn.close()

    def renewStatus(self, update: Update) -> "mainBot":
        """
        在每个command Handler前调用，是指令的前置函数。
        renewStatus实际返回一个`fakeBotObject`，而非bot本身。
        请参考`fakeBotObject`的文档。
        """
        self = fakeBotObject(self)

        self.lastchat = getchatid(update)

        if update.callback_query is None:
            if ischannel(update):
                self.lastuser = -1
            else:
                self.lastuser = getfromid(update)
            self.lastmsgid = getmsgid(update)

        else:
            self.lastuser = update.callback_query.from_user.id
            self.lastmsgid = -1
        return self

    def _reply_retries(self, retries: int = 5, sleeptime: int = 5, kwargs={}) -> int:
        for i in range(retries):
            try:
                ans = self.bot.send_message(**kwargs).message_id
            except Exception as e:
                if (
                    e.__class__ is BadRequest
                    and str(e).find("Replied message not found") != -1
                ):
                    kwargs.pop("reply_to_message_id")
                    i -= 1
                    continue

                elif e.__class__ is BadRequest:
                    raise e

                elif i == retries - 1:
                    raise e

                time.sleep(sleeptime)

            else:
                break
        return ans

    @overload
    def reply(
        self,
        chat_id: int,
        text: str,
        reply_markup: InlineKeyboardMarkup,
        reply_to_message_id: int,
        parse_mode: str,
        timeout: int,
    ) -> int:
        ...

    def reply(self, *args, **kwargs) -> int:
        """
        调用send_message方法，回复或发送消息。
        支持telegram bot中`send_message`方法的keyword argument，
        如`reply_markup`，`reply_to_message_id`，`parse_mode`，`timeout`。
        返回值是message id
        """
        ans = None
        chat_id: Optional[int] = None
        text: str = None
        if len(args) > 0:
            if type(args[0]) is int:
                chat_id = args[0]
                kwargs["chat_id"] = chat_id
            elif type(args[0]) is str:
                text = args[0]
                kwargs["text"] = text

            if len(args) > 1:
                text = args[1]
                kwargs["text"] = text

        if chat_id is None and "chat_id" in kwargs:
            chat_id = kwargs["chat_id"]

        if text is None and "text" in kwargs:
            text = kwargs["text"]

        if not text:
            raise ValueError("发生错误：发送消息时没有文本")

        if chat_id is None:
            kwargs["chat_id"] = self.lastchat
            if self.lastmsgid >= 0 and "reply_to_message_id" not in kwargs:
                kwargs["reply_to_message_id"] = self.lastmsgid

        txts = text.split("\n")

        rp_markup = None
        if len(text) >= 1000:
            while len(txts) > 10 or len(text) >= 1000:
                if "reply_markup" in kwargs:
                    rp_markup = kwargs.pop("reply_markup")
                if len(txts) > 10:
                    line = 1
                    l = len(txts[0])
                    if l >= 1000:
                        kwargs["text"] = text[:1000]
                        text = text[1000:]
                        txts = text.split("\n")
                    else:
                        while line <= 10 and l < 1000:
                            l += len(txts[line])
                            line += 1
                        line -= 1
                        kwargs["text"] = "\n".join(txts[:line])
                        txts = txts[line:]
                        text = "\n".join(txts)
                else:
                    kwargs["text"] = text[:1000]
                    text = text[1000:]
                    txts = text.split("\n")

                ans = self._reply_retries(5, 5, kwargs)

        if len(text) > 0:
            kwargs["text"] = text
            if rp_markup is not None:
                kwargs["reply_markup"] = rp_markup
            ans = self._reply_retries(5, 5, kwargs)

        if ans is None:
            raise ValueError("没有成功发送消息")
        return ans

    @overload
    def reply_doc(
        self,
        chat_id: int,
        document: Any,
        filename: str,
        caption: str,
        reply_markup: InlineKeyboardMarkup,
        reply_to_message_id: int,
        parse_mode: str,
        timeout: int,
    ) -> int:
        ...

    def reply_doc(self, *args, **kwargs) -> int:
        """
        调用`send_document`方法，回复或发送消息.
        支持telegram bot中`send_document`方法的keyword argument，
        如`reply_markup`，`reply_to_message_id`，`parse_mode`，`timeout`.
        返回值是message id.

        Note:
            * 如果开头传入的参数不是keyword argument，只接受chat_id在前，
                document在后的顺序，且只支持这两个参数不使用keyword argument.
        """
        ans = None
        chat_id: Optional[int] = None
        document = None
        if len(args) > 0:
            if type(args[0]) is int:
                chat_id = args[0]
                kwargs["chat_id"] = chat_id
            else:
                document = args[0]
                kwargs["document"] = document

            if len(args) > 1:
                document = args[1]
                kwargs["document"] = document

        if document is None and "document" in kwargs:
            document = kwargs["document"]

        if document is None:
            raise ValueError("发生错误：发送消息时没有文件")

        if chat_id is None and "chat_id" in kwargs:
            chat_id = kwargs["chat_id"]

        if chat_id is None:
            kwargs["chat_id"] = self.lastchat
            if self.lastmsgid >= 0 and "reply_to_message_id" not in kwargs:
                kwargs["reply_to_message_id"] = self.lastmsgid

        if "timeout" not in kwargs:
            kwargs["timeout"] = 120

        self.debuginfo("sending document:" + str(kwargs))

        isfile = False

        with self.locks.filelock:
            if type(document) is str and os.path.exists(document):
                kwargs["document"] = open(document, "rb")
                isfile = True
            ans = self.bot.send_document(**kwargs).message_id

        if isfile:
            kwargs["document"].close()
        return ans

    @overload
    def reply_photo(
        self,
        chat_id: int,
        photo: Any,
        filename: str,
        caption: str,
        reply_markup: InlineKeyboardMarkup,
        reply_to_message_id: int,
        parse_mode: str,
        timeout: int,
    ) -> int:
        ...

    def reply_photo(self, *args, **kwargs) -> int:
        """
        调用`send_photo`方法，回复或发送消息.
        支持telegram bot中`send_photo`方法的keyword argument，
        如`reply_markup`，`reply_to_message_id`，`parse_mode`，`timeout`.
        返回值是message id.

        Note:
            * 如果开头传入的参数不是keyword argument，只接受chat_id在前，
                photo在后的顺序，且只支持这两个参数不使用keyword argument.
        """
        ans = None
        chat_id: Optional[int] = None
        photo = None
        if len(args) > 0:
            if type(args[0]) is int:
                chat_id = args[0]
                kwargs["chat_id"] = chat_id
            else:
                photo = args[0]
                kwargs["photo"] = photo

            if len(args) > 1:
                photo = args[1]
                kwargs["photo"] = photo

        if photo is None and "photo" in kwargs:
            photo = kwargs["photo"]

        if photo is None:
            raise ValueError("发生错误：发送消息时没有图像")

        if chat_id is None and "chat_id" in kwargs:
            chat_id = kwargs["chat_id"]

        if chat_id is None:
            kwargs["chat_id"] = self.lastchat
            if self.lastmsgid >= 0 and "reply_to_message_id" not in kwargs:
                kwargs["reply_to_message_id"] = self.lastmsgid

        if "timeout" not in kwargs:
            kwargs["timeout"] = 120

        self.debuginfo("sending photo:" + str(kwargs))

        isfile = False

        with self.locks.filelock:
            if type(photo) is str and os.path.exists(photo):
                kwargs["photo"] = open(photo, "rb")
                isfile = True
            ans = self.bot.send_photo(**kwargs).message_id

        if isfile:
            kwargs["photo"].close()
        return ans

    def delmsg(self, chat_id: int, msgid: int, maxTries: int = 5) -> bool:
        """尝试删除消息`maxTries`次，该方法的目的是防止网络原因删除失败时导致执行出现失误"""
        assert maxTries > 0

        for i in range(maxTries):
            try:
                self.bot.delete_message(chat_id=chat_id, message_id=msgid)
            except:
                if i == maxTries - 1:
                    return False
                continue
            break

        return True

    def debuginfo(self, info: str, newth: bool = True) -> None:
        if self.debug and info != "":
            if newth:
                threading.Thread(target=self.reply, args=(MYID, info)).start()
            else:
                self.reply(MYID, info)

    def errorInfo(self, msg: str) -> False:
        self.reply(text=msg)
        return False

    def remove_job_if_exists(self, name: str) -> bool:
        """Remove job with given name. Returns whether job was removed."""

        current_jobs = self.updater.job_queue.get_jobs_by_name(name)
        if not current_jobs:
            return False
        for job in current_jobs:
            job.schedule_removal()
        return True

    def job_exists(self, name: str) -> bool:
        current_jobs = self.updater.job_queue.get_jobs_by_name(name)
        return bool(current_jobs)

    @staticmethod
    def queryError(query: CallbackQuery) -> False:
        try:
            query.edit_message_text(text="(*￣︿￣) 这个按钮请求已经无效了", reply_markup=None)
        except BadRequest:
            query.delete_message()
        return False

    def importHandlers(self) -> None:
        for key in self.__dir__():
            try:
                func = getattr(self, key)
            except RuntimeError:
                continue
            if type(func) is commandCallbackMethod:
                print(f"Handler added: {key}")
                self.updater.dispatcher.add_handler(
                    CommandHandler(key, func, run_async=True)
                )

        self.updater.dispatcher.add_handler(
            MessageHandler(
                Filters.text
                & (~Filters.command)
                & (~Filters.video)
                & (~Filters.photo)
                & (~Filters.sticker)
                & (~Filters.chat_type.channel),
                self.textHandler,
                run_async=True,
            )
        )

        self.updater.dispatcher.add_handler(
            MessageHandler(Filters.chat_type.channel, self.channelHandler)
        )

        self.updater.dispatcher.add_handler(
            MessageHandler(
                (Filters.photo | Filters.sticker) & (~Filters.chat_type.channel),
                self.photoHandler,
                run_async=True,
            )
        )

        self.updater.dispatcher.add_handler(
            CallbackQueryHandler(self.buttonHandler, run_async=True)
        )

        self.updater.dispatcher.add_error_handler(self.errorHandler)

        self.updater.dispatcher.add_handler(
            MessageHandler(Filters.command, self.unknowncommand, run_async=True)
        )

    # 指令
    @commandCallbackMethod
    def cancel(self, update: Update, context: CallbackContext) -> None:
        if self.lastchat in self.workingMethod:
            self.workingMethod.pop(self.lastchat)
            self.reply(text="操作取消～")

    @commandCallbackMethod
    def stop(self, update: Update, context: CallbackContext) -> bool:
        if not isfromme(update):
            self.reply("你没有权限")
            return False
        try:
            self.beforestop()
        except:
            ...
        self.reply(text="主人再见QAQ")
        pid = os.getpid()
        os.kill(pid, SIGINT)
        return True

    @commandCallbackMethod
    def restart(self, update: Update, context: CallbackContext) -> bool:
        if not isfromme(update):
            self.reply("你没有权限")
            return False

        # mp = multiprocessing.Process(target=os.system, args=(startcommand,))
        # mp.start()
        msg = str(subprocess.check_output([startcommand]))
        if "Already up to date." not in msg:
            self.reply(MYID, msg)

        self.stop.__wrapped__(self, update, context)

    @commandCallbackMethod
    def getid(self, update: Update, context: CallbackContext) -> None:
        if ischannel(update):
            return
        if isgroup(update) and update.message.reply_to_message is not None:
            self.reply(
                text=f"群id：`{self.lastchat}`\n回复的消息的用户id：`{update.message.reply_to_message.from_user.id}`",
                parse_mode="MarkdownV2",
            )
        elif isgroup(update):
            self.reply(
                text=f"群id：`{self.lastchat}`\n您的id：`{self.lastuser}`",
                parse_mode="MarkdownV2",
            )
        elif isprivate(update):
            self.reply(text=f"您的id：\n{self.lastchat}", parse_mode="MarkdownV2")

    @commandCallbackMethod
    def debugmode(self, update: Update, context: CallbackContext) -> None:
        if not isfromme(update):
            self.reply("没有权限")
            return

        if self.debug:
            self.debug = False
            self.reply("Debug模式关闭")
        else:
            self.debug = True
            self.reply("Debug模式开启")

    # 非指令的handlers，供子类重写。如果需要定义别的类型的handlers，务必在此处创建虚函数

    def textHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        """Override"""
        return handlePassed

    def photoHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        """Override"""
        return handlePassed

    def channelHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        """Override"""
        return handlePassed

    def editedChannelHandler(
        self, update: Update, context: CallbackContext
    ) -> handleStatus:
        """Override"""
        return handlePassed

    def buttonHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        """Override"""
        return handlePassed

    # 错误处理
    def errorHandler(self, update: object, context: CallbackContext):
        err = context.error
        if err.__class__ in [NetworkError, OSError, TimedOut]:
            raise err

        self.reply(
            chat_id=MYID,
            text=f"哎呀，出现了未知的错误呢……\n{err.__class__}\n\
                {err}\ntraceback:{traceback.format_exc()}",
        )

    # 未知指令
    def unknowncommand(self, update: Update, context: CallbackContext):
        self = self.renewStatus(update)
        if not isfromme(update):
            self.reply("没有这个指令")
        else:
            self.reply("似乎没有这个指令呢……")

    # 聊天迁移
    @classmethod
    def chatmigrate(cls, oldchat: int, newchat: int, instance: "baseBot"):
        """Override"""
        if cls is baseBot:
            conn = sqlite3.connect(blacklistdatabase)
            c = conn.cursor()
            c.execute(
                f"""UPDATE BLACKLIST
            SET TGID={newchat} WHERE TGID={oldchat}"""
            )
            if oldchat in instance.blacklist:
                instance.blacklist[instance.blacklist.index(oldchat)] = newchat

    def beforestop(self):
        """Override"""
        return
