from bot_framework.botabc import BotAbstract, BotMessageBase, BotJobBase
import threading


class BotBase(BotAbstract, BotMessageBase, BotJobBase):
    def __init__(self) -> None:
        pass

    def debuginfo(self, info: str, newth: bool = True) -> None:
        if self.debug and info != "":
            if newth:
                threading.Thread(
                    target=self.reply,
                    args=(cfg.ADMINID, info)
                ).start()
            else:
                self.reply(cfg.ADMINID, info)

    def errorInfo(self, msg: str) -> False:
        self.reply(text=msg)
        return False
