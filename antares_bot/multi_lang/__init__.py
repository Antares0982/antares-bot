from antares_bot.bot_logging import get_logger
from antares_bot.multi_lang.context import get_default_locale, lang_context


_LOGGER = get_logger(__name__)


def t(d: dict[str, str]):
    l_ct = lang_context()
    ans = d.get(l_ct, None)
    if ans is None:
        ans = d.get(get_default_locale(), None)
        if ans is None:
            # give the first value
            _LOGGER.warning("No text found in %s for locale %s, using the first value", name, l_ct)
            ans = next(iter(d.values()))
    return ans
