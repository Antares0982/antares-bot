#!/usr/bin/python3 -O
import logging
import os


def script_init():
    DIR = os.path.dirname(os.path.realpath(__file__))
    cfg_path = os.path.join(DIR, "bot_cfg.py")
    if not os.path.exists(cfg_path):
        import shutil
        shutil.copyfile(os.path.join(DIR, "bot_default_cfg.py"), cfg_path)
    import bot_cfg as cfg
    import bot_default_cfg
    for k in bot_default_cfg.__all__:
        if not hasattr(cfg, k):
            setattr(cfg, k, getattr(bot_default_cfg, k))
    from init_hooks import generate_language
    generate_language(cfg.LOCALE)


def main():
    script_init()
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    from bot_framework import language
    print(language.STARTUP)


if __name__ == "__main__":
    main()
