class Locale:
    locale: "Locale" = None
    button_invalid: str
    welcome: str

    @classmethod
    def setCurrentLocale(kls):
        if kls == Locale:
            raise TypeError("Cannot set base locale")
        Locale.locale = kls


def _locale_getattr(k, name):
    if Locale.locale is None:
        raise RuntimeError("locale not set")
    return getattr(Locale.locale, name)


if __name__ != "__main__":
    if Locale.locale is None:
        import bot_framework.locale.zh_CN  # default
        setattr(Locale, "__getattr__", _locale_getattr)
    if Locale.locale is None:
        raise ImportError("Error when setting locale")
