#!/usr/bin/python3 -O
import logging

from telegram.ext import CallbackContext

from example1 import exampleBot1
from example2 import exampleBot2
from utils import *


@final
class finalBot(exampleBot1, exampleBot2):  # 继承的功能类,handle时从左到右优先级逐次降低
    def __init__(self) -> None:
        print("subclasses init")
        for cls in self.__class__.__bases__:
            cls.__init__(self)
        print("all subclasses init finished")

    @commandCallbackMethod
    def exec(self, update: Update, context: CallbackContext) -> None:
        if not isfromme(update):
            self.errorInfo("没有权限")
            return

        if len(context.args) == 0:
            self.errorInfo("没有接收到命令诶")
            return
        try:
            needReturn = False
            txt = update.message.text
            if context.args[0] == 'r':
                needReturn = True
                command = txt[txt.find("r ")+2:]
            else:
                command = ' '.join(context.args)

            if not command:
                raise ValueError

            if not needReturn:
                try:
                    exec(command)
                except Exception as e:
                    self.reply(text="执行失败……")
                    raise e
                self.reply(text="执行成功～")
            else:
                try:
                    exec("t="+command)
                    ans = locals()['t']
                except Exception as e:
                    self.reply(text="执行失败……")
                    raise e
                self.reply(text=f"执行成功，返回值：{ans}")
        except (TypeError, ValueError):
            self.reply(text="唔……似乎参数不对呢")
        except Exception as e:
            raise e

    def textHandler(self, update: Update, context: CallbackContext) -> bool:
        self.renewStatus(update)
        if any(x in self.blacklist for x in (self.lastuser, self.lastchat)):
            return self.errorInfo("你在黑名单中，无法使用任何功能")
        for cls in self.__class__.__bases__:
            status: handleStatus = cls.textHandler(self, update, context)
            if status.blocked():
                return status.normal

        return False

    def buttonHandler(self, update: Update, context: CallbackContext) -> bool:
        self.renewStatus(update)
        if any(x in self.blacklist for x in (self.lastuser, self.lastchat)):
            return self.queryError(update.callback_query)

        for cls in self.__class__.__bases__:
            status: handleStatus = cls.buttonHandler(self, update, context)
            if status.blocked():
                return status.normal

        return self.queryError(update.callback_query)

    def photoHandler(self, update: Update, context: CallbackContext) -> bool:
        self.renewStatus(update)
        if self.lastchat in self.blacklist:
            return self.errorInfo("你在黑名单中，无法使用任何功能")

        for cls in self.__class__.__bases__:
            status: handleStatus = cls.photoHandler(self, update, context)
            if status.blocked():
                return status.normal

        return False

    def channelHandler(self, update: Update, context: CallbackContext) -> bool:
        self.renewStatus(update)
        if self.lastchat in self.blacklist:
            return False

        for cls in self.__class__.__bases__:
            if update.channel_post is not None:
                status: handleStatus = cls.channelHandler(
                    self, update, context)
            elif update.edited_channel_post is not None:
                status: handleStatus = cls.editedChannelHandler(
                    self, update, context)
            else:
                status = handlePassed
            if status.blocked():
                return status.normal

        return False


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    global finalbot
    finalbot = finalBot()
    finalbot.start()


if __name__ == "__main__":
    main()
