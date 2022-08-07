import os
from signal import SIGINT
from typing import TYPE_CHECKING

from bot_framework.utils.command_callback import CommandCallbackMethod
from telegram import Update
from telegram.ext import CallbackContext

if TYPE_CHECKING:
    from bot_framework.botbase import BotBase


class BotCommandABC(object):
    # 指令
    @CommandCallbackMethod
    def cancel(self: "BotBase", update: Update, context: CallbackContext) -> None:
        if self.lastchat in self.workingMethod:
            self.workingMethod.pop(self.lastchat)
            self.reply(text="操作取消～")

    @CommandCallbackMethod
    def stop(self: "BotBase", update: Update, context: CallbackContext) -> bool:
        if not self.isfromme(update):
            self.reply("You are not authorized.")
            return False
        try:
            self.beforestop()
        except:
            ...
        self.reply(text="Bot stopping...")
        pid = os.getpid()
        os.kill(pid, SIGINT)
        return True

    @CommandCallbackMethod
    def restart(self: "BotBase", update: Update, context: CallbackContext) -> bool:
        if not isfromme(update):
            self.reply("你没有权限")
            return False

        # mp = multiprocessing.Process(target=os.system, args=(startcommand,))
        # mp.start()
        msg = str(subprocess.check_output([startcommand]))
        if "Already up to date." not in msg:
            self.reply(MYID, msg)

        self.stop.__wrapped__(self, update, context)

    @CommandCallbackMethod
    def getid(self: "BotBase", update: Update, context: CallbackContext) -> None:
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

    @CommandCallbackMethod
    def debugmode(self: "BotBase", update: Update, context: CallbackContext) -> None:
        if not self.isfromme(update):
            self.reply("没有权限")
            return

        if self.debug:
            self.debug = False
            self.reply("Debug模式关闭")
        else:
            self.debug = True
            self.reply("Debug模式开启")
