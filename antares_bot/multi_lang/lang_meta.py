from typing import TYPE_CHECKING

class LanguageMeta(type):
    if TYPE_CHECKING:
        SUPPORTED: tuple[str]

    def __getattribute__(cls, name: str):
        if name != '_LANG_INDEXED__':
            if name == 'SUPPORTED' or name.startswith('__'):
                return super().__getattribute__(name)
        else:
            return super().__getattribute__(name)
        if not hasattr(cls, '_LANG_INDEXED__'):
            lang_indexed = {}
            cls._LANG_INDEXED__ = lang_indexed
            for i, lang in enumerate(cls.SUPPORTED):
                lang_indexed[lang] = i
        else:
            lang_indexed = super().__getattribute__('_LANG_INDEXED__')
        index = lang_indexed.get(get_context(), 0)
        l = super().__getattribute__(name)
        if index >= len(l):
            index = 0
        ret = l[index]
        if ret is None:
            ret = l[0]
        return ret
