from configparser import ConfigParser
from typing import Type


class BotConfig(object):
    admin_id: int = None
    bot_token: str = None
    is_use_proxy: bool = None
    proxy_url: str = None
    startcommand: str = None
    blacklistdatabase: str = None
    ##
    __kls: Type['BotConfig'] = None
    __parser: ConfigParser = None

    def __init__(self):
        # TODO
        raise RuntimeError("BotConfig should not be instantiated")

    @classmethod
    def parse(kls):
        """
        Override this method to load personalized config.
        """
        if kls.__kls is None:
            kls.__kls = kls
        parser = kls.__parser
        kls.admin_id = parser.getint("settings", "adminid")
        kls.bot_token = parser["settings"]["token"]
        kls.is_use_proxy = parser.getboolean("settings", "proxy")
        kls.proxy_url = parser["settings"]["proxy_url"]
        kls.startcommand = parser["settings"]["startcommand"]
        kls.blacklistdatabase = parser["settings"]["blacklistdatabase"]

    @staticmethod
    def register_config_class(kls: Type['BotConfig'], *args, **kwargs):
        """Call this to support customized config class."""
        BotConfig.__kls = kls
        
    @staticmethod
    def load(path: str):
        __parser = ConfigParser()
        __parser.read(path)
        BotConfig.__kls.load()

# inheritance usage
# class xxx(BotConfig):
# @classmethod
# def parse(kls):
#     super().parse()
