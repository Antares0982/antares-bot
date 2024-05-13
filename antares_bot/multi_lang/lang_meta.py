# from typing import TYPE_CHECKING

from antares_bot.bot_logging import get_logger
from antares_bot.multi_lang.context import lang_context


_LOGGER = get_logger(__name__)


class LanguageMeta(type):
    def __getattribute__(cls, name: str):
        ans_default = super().__getattribute__(name)
        if name.startswith('__'):
            return ans_default

        if isinstance(ans_default, dict):
            if len(ans_default) == 0:
                raise KeyError(f"No multi-language text provided by {name}")
            l_ct = lang_context()
            ans = ans_default.get(l_ct, None)
            if ans is None:
                from antares_bot.multi_lang.context import get_default_locale
                ans = ans_default.get(get_default_locale(), None)
                if ans is None:
                    # give the first value
                    _LOGGER.warning("No text found in %s for locale %s, using the first value", name, l_ct)
                    ans = next(iter(ans_default.values()))
            return ans
        return ans_default

    def get_original(cls, name):
        return object.__getattribute__(cls, name)

    def yield_language(cls):
        for k, v in cls.__dict__.items():
            if not k.startswith('__') and isinstance(v, dict):
                yield k, v

    def merge_language_class(cls, kls):
        if type(kls) is not LanguageMeta:
            raise TypeError(f"Expecting BaseLanguage, got {kls}")
        for k, v in kls.yield_language():
            try:
                lang = cls.get_original(k)
            except AttributeError:
                # simply merge it
                setattr(cls, k, v)
            else:
                # duplicate, merge them
                for lang_k, lang_v in v.items():
                    lang[lang_k] = lang_v
