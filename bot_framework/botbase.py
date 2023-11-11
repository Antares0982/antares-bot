import threading

from telegram import Update
from telegram.ext import Filters

from bot_framework.botabc import BotAbstract, BotJobBase, BotMessageBase
from bot_framework.config import BotConfig
from bot_framework.utils import getchatid, getfromid, CommandCallbackMethod


# class BotBase(BotAbstract, BotMessageBase, BotJobBase):
#     cfg: BotConfig

#     def __init__(self) -> None:
#         pass

#     def debuginfo(self, info: str, newth: bool = True) -> None:
#         if self.debug and info != "":
#             if newth:
#                 threading.Thread(
#                     target=self.reply,
#                     args=(self.cfg.admin_id, info)
#                 ).start()
#             else:
#                 self.reply(self.cfg.admin_id, info)

#     def errorInfo(self, msg: str) -> False:
#         self.reply(text=msg)
#         return False

#     def start(self) -> None:
#         self.importHandlers()
#         self.reply(MYID, "Bot is live!")
#         self.updater.start_polling(drop_pending_updates=True)
#         self.updater.idle()

#     def readblacklist(self):
#         self.blacklist = []
#         conn = sqlite3.connect(blacklistdatabase)
#         c = conn.cursor()
#         cur = c.execute("SELECT * FROM BLACKLIST;")
#         ans = cur.fetchall()
#         conn.close()
#         for tgid in ans:
#             self.blacklist.append(tgid)

#     def addblacklist(self, id: int):
#         if id in self.blacklist:
#             return
#         self.blacklist.append(id)
#         conn = sqlite3.connect(blacklistdatabase)
#         c = conn.cursor()
#         c.execute(
#             f"""INSERT INTO BLACKLIST(TGID)
#         VALUES({id});"""
#         )
#         conn.commit()
#         conn.close()

#     def renewStatus(self, update: Update) -> "mainBot":
#         """
#         在每个command Handler前调用，是指令的前置函数。
#         renewStatus实际返回一个`fakeBotObject`，而非bot本身。
#         请参考`fakeBotObject`的文档。
#         """
#         self = fakeBotObject(self)

#         self.lastchat = getchatid(update)

#         if update.callback_query is None:
#             if ischannel(update):
#                 self.lastuser = -1
#             else:
#                 self.lastuser = getfromid(update)
#             self.lastmsgid = getmsgid(update)

#         else:
#             self.lastuser = update.callback_query.from_user.id
#             self.lastmsgid = -1
#         return self

#     @staticmethod
#     def queryError(query: CallbackQuery) -> False:
#         try:
#             query.edit_message_text(
#                 text="(*￣︿￣) 这个按钮请求已经无效了", reply_markup=None)
#         except BadRequest:
#             query.delete_message()
#         return False

#     def importHandlers(self) -> None:
#         for key in self.__dir__():
#             try:
#                 func = getattr(self, key)
#             except RuntimeError:
#                 continue
#             if type(func) is CommandCallbackMethod:
#                 print(f"Handler added: {key}")
#                 self.updater.dispatcher.add_handler(
#                     CommandHandler(key, func, run_async=True)
#                 )

#         self.updater.dispatcher.add_handler(
#             MessageHandler(
#                 Filters.text
#                 & (~Filters.command)
#                 & (~Filters.video)
#                 & (~Filters.photo)
#                 & (~Filters.sticker)
#                 & (~Filters.chat_type.channel),
#                 self.textHandler,
#                 run_async=True,
#             )
#         )

#         self.updater.dispatcher.add_handler(
#             MessageHandler(Filters.chat_type.channel, self.channelHandler)
#         )

#         self.updater.dispatcher.add_handler(
#             MessageHandler(
#                 (Filters.photo | Filters.sticker) & (
#                     ~Filters.chat_type.channel),
#                 self.photoHandler,
#                 run_async=True,
#             )
#         )

#         self.updater.dispatcher.add_handler(
#             CallbackQueryHandler(self.buttonHandler, run_async=True)
#         )

#         self.updater.dispatcher.add_error_handler(self.errorHandler)

#         self.updater.dispatcher.add_handler(
#             MessageHandler(Filters.command,
#                            self.unknowncommand, run_async=True)
#         )

#     @classmethod
#     def chatmigrate(cls, oldchat: int, newchat: int, instance: "baseBot"):
#         """Override"""
#         if cls is baseBot:
#             conn = sqlite3.connect(blacklistdatabase)
#             c = conn.cursor()
#             c.execute(
#                 f"""UPDATE BLACKLIST
#             SET TGID={newchat} WHERE TGID={oldchat}"""
#             )
#             if oldchat in instance.blacklist:
#                 instance.blacklist[instance.blacklist.index(oldchat)] = newchat

#     def beforestop(self):
#         """Override"""
#         return

#     def chatisfromme(update: Update) -> bool:
#         return getchatid(update) == self.cfg.admin_id

#     def isfromme(update: Update) -> bool:
#         """检查是否来自`MYID`"""
#         return getfromid(update) == MYID
