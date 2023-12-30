# should not import anything other than python stdlib here
import os
import shutil


def hook_cfg():
    DIR = os.path.dirname(os.path.realpath(__file__))
    cfg_path = os.path.join(DIR, "bot_cfg.py")
    if not os.path.exists(cfg_path):
        shutil.copyfile(os.path.join(DIR, "bot_default_cfg.py"), cfg_path)
    import bot_cfg as cfg
    import bot_default_cfg
    for k in bot_default_cfg.__all__:
        if not hasattr(cfg, k):
            setattr(cfg, k, getattr(bot_default_cfg, k))


def init_pika():
    command = 'curl https://api.github.com/repos/Antares0982/RabbitMQInterface/contents/rabbitmq_interface.py | jq -r ".content" | base64 --decode > rabbitmq_interface.py'
    import subprocess
    code = subprocess.call(command, shell=True)
    if code != 0:
        import sys
        print("failed to download rabbitmq_interface.py", file=sys.stderr)


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
