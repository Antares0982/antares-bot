from antares_bot.bot_logging import get_logger
from antares_bot.multi_lang.context import get_default_locale, lang_context


_LOGGER = get_logger(__name__)

_CACHE_LOGGED: set[tuple[int, str | None]] = set()


class LocaleError(ValueError):
    pass


def t(d: dict[str, str], locale: str | None = None) -> str:
    """
    Translate message by language context.
    May raise if the locale augument is not `None` and invalid.
    If locale is None, we use the default language.
    If the default language does not appear in `d`, use the first
    dict value of `d`. Will not raise any error
    as long as the language dict `d` is not empty.
    """
    l_ct = lang_context() if locale is None else locale
    ans = d.get(l_ct) if l_ct is not None else None
    if ans is None:
        if locale is not None:
            # specified a locale but not found. Should raise an error
            raise LocaleError(f"Locale {locale} not found in {d}")
        default_locale = get_default_locale()
        ans = d.get(default_locale) if default_locale is not None else None
        if ans is None:
            # give the first value
            if (id(d), l_ct) not in _CACHE_LOGGED:
                _CACHE_LOGGED.add((id(d), l_ct))
                _LOGGER.warning(
                    "No text found in %s for locale %s, using the first value", d, l_ct
                )
            ans = next(iter(d.values()))
    return ans
