from configparser import ConfigParser
from typing import Generator, List, Type


class BotConfig(object):
    admin_id: int
    bot_token: str
    is_use_proxy: bool
    proxy_url: str
    startcommand: str
    blacklistdatabase: str
    ##
    __parser: ConfigParser = None

    def __init__(self) -> None:
        ...

    def parse(self, parser: ConfigParser) -> None:
        """
        Override this method to load personalized config.
        """
        self.admin_id = parser.getint("settings", "adminid")
        self.bot_token = parser["settings"]["token"]
        self.is_use_proxy = parser.getboolean("settings", "proxy")
        self.proxy_url = parser["settings"]["proxy_url"]
        self.startcommand = parser["settings"]["startcommand"]
        self.blacklistdatabase = parser["settings"]["blacklistdatabase"]

    def load(instance, path: str) -> None:
        BotConfig.__parser = ConfigParser()
        BotConfig.__parser.read(path)

        klses: List[Type[BotConfig]] = list(
            BotConfig.__iterate_over_classes(type(instance))
        )

        for kls in klses:
            kls.parse(instance, BotConfig.__parser)

    @staticmethod
    def __check_subclass(kls: type) -> None:
        if not issubclass(kls, BotConfig):
            raise TypeError("registered class is not a subclass of BotConfig")

    @staticmethod
    def __iterate_over_classes(start_class: type) -> Generator[type, None, None]:
        BotConfig.__check_subclass(start_class)
        kls = start_class
        while kls != BotConfig:
            yield kls
            kls = kls.__base__
            BotConfig.__check_subclass(kls)
        yield kls
