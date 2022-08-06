from telegram import Bot
from telegram.ext import Updater


class BotAbstract(object):
    """
    Abstracts for bot framework.
    """
    # type hints
    bot: Bot
    updater: Updater
    
    # virtual properties

    @property
    def lastchat(self) -> int:
        raise NotImplementedError("Calling abstract method")

    @property
    def lastuser(self) -> int:
        raise NotImplementedError("Calling abstract method")

    @property
    def lastmsgid(self) -> int:
        raise NotImplementedError("Calling abstract method")

    @lastchat.setter
    def lastchat(self, v):
        raise NotImplementedError("Calling abstract method")

    @lastuser.setter
    def lastuser(self, v):
        raise NotImplementedError("Calling abstract method")

    @lastmsgid.setter
    def lastmsgid(self, v):
        raise NotImplementedError("Calling abstract method")
