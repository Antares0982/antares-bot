from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Type, Union

if TYPE_CHECKING:
    from bot_inst import TelegramBot


class TelegramBotBase(object):
    pass


class TelegramBotModuleBase(TelegramBotBase):
    def __init__(self, parent: "TelegramBot") -> None:
        self.parent = parent

    def do_init(self) -> None:
        raise NotImplementedError("Should be implemented in subclass")

    def __getattr__(self, name: str):
        return getattr(self.parent, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "parent":
            super().__setattr__(name, value)
        else:
            setattr(self.parent, name, value)
