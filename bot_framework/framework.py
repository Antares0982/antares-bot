import logging
from typing import List, Type, Union

from bot_framework.botbase import BotBase


class BotFramework(object):
    def __init__(self, modules: Union[str, List[Union[str, Type[BotBase]]]]) -> None:
        """
        Initialize the bot framework.
        :param modules: A list of modules to be loaded.
        """
        self.bot = None

    def load_modules(self, modules: List[Union[str, Type[BotBase]]]) -> None:
        """
        Load modules.
        :param modules: A list of modules to be loaded.
        """
        for module in modules:
            # TODO
            pass

    def start(self) -> None:
        self.bot.start()


def BotMain(kls: Type[BotFramework], *args, **kwargs):
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    bot = kls(*args, **kwargs)
    bot.start()
