from configparser import ConfigParser
from typing import Generator, List, Type


class BotConfig(object):
    """
    A bot config class to load configs.
    If more config fields are needed, inherit this class and override :method:`parse` method.
    Then call :method:`load` to load your config. The config classes can be inherited more than once.

    Note:
        * Don't need to call the :method:`parse` method in subclasses. It will be called automatically.
        * Not supporting multi inheritance.
    """
    admin_id: int
    bot_token: str
    is_use_proxy: bool
    proxy_url: str
    startcommand: str
    blacklistdatabase: str

    def __init__(self) -> None:
        ...

    def parse(self, parser: ConfigParser) -> None:
        """
        Override this method to load personalized config.
        Overriding methods should not call this method; 
        this method is called automatically.
        """
        self.admin_id = parser.getint("settings", "adminid")
        self.bot_token = parser["settings"]["token"]
        self.is_use_proxy = parser.getboolean("settings", "proxy")
        self.proxy_url = parser["settings"]["proxy_url"]
        self.startcommand = parser["settings"]["startcommand"]
        self.blacklistdatabase = parser["settings"]["blacklistdatabase"]

    def load(instance, path: str) -> None:
        """
        Load config.
        The superclasses will be iterated and :method:`parse` will be called.
        """
        parser = ConfigParser()
        parser.read(path)

        klses: List[Type[BotConfig]] = list(
            BotConfig.__iterate_over_classes(type(instance))
        )

        for kls in reversed(klses):
            kls.parse(instance, parser)

    @staticmethod
    def __check_subclass(kls: type) -> None:
        if not issubclass(kls, BotConfig):
            raise TypeError(
                "Input class is not a subclass of BotConfig, or multi inheritance detected"
            )

    @staticmethod
    def __iterate_over_classes(start_class: type) -> Generator[type, None, None]:
        kls = start_class
        BotConfig.__check_subclass(kls)
        while kls != BotConfig:
            yield kls
            kls = kls.__base__
            BotConfig.__check_subclass(kls)
        yield kls
