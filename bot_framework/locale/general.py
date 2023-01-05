import importlib
import sys
from typing import Type


class Locale:
    locale: Type["Locale"] = None
    button_invalid: str
    welcome: str

    @staticmethod
    def setCurrentLocale(mod):
        importlib.reload(mod)

    @classmethod
    def internalSetLocale(kls):
        if kls == Locale:
            raise TypeError("Cannot set base locale")
        Locale.locale = kls

    def __getattr__(self, name):
        return getattr(Locale.locale, name)


locale = Locale()


if __name__ != "__main__":
    if Locale.locale is None:
        try:
            import bot_framework.locale.zh_CN  # default
        except Exception:
            ...
