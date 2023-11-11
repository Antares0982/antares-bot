# should not import anything other than python stdlib here

def generate_language(locale: str):
    from bot_default_cfg import LOCALE as default_locale
    if locale != default_locale:
        # modify the language module
        import importlib
        try:
            new_language = importlib.import_module(f"bot_framework.multi_lang.{locale}")
        except ImportError:
            import sys
            print(f"language {locale} not found! Exiting.", file=sys.stderr)
            exit(1)
        from bot_framework import language
        for k, v in new_language.__dict__.items():
            if k.upper() == k:
                setattr(language, k, v)
