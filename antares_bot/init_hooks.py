# should not import anything other than python stdlib here
import os
import sys


_BLANK_CFG = \
    """\"\"\"Naming convention: as long as the config item can be retrieved like:
```
bot_cfg.<SectionName>.<ITEM_NAME>
```
it is valid. For example: `bot_cfg.BasicConfig.TOKEN`
The `BasicConfig` and `AntaresBotConfig` are required.
\"\"\"


class BasicConfig:
    \"\"\"
    Basic sample config.
    TOKEN and MASTER_ID must be provided.
    For more details, refers to bot_default_cfg.py.
    \"\"\"
    # LOCALE = 'en'
    # DATA_DIR = "data"
    TOKEN = "abcdef:123456"
    MASTER_ID = 123456789
    # BOT_NAME = "my_bot"  # mostly used in logging


class AntaresBotConfig:
    \"\"\"
    Config to control the bot behavior. They are all optional.
    For more details, refers to bot_default_cfg.py.
    \"\"\"
    PULL_WHEN_STOP = True  # enable pulling when bot stops
    # JOB_QUEUE_CONFIG = {
    #     "job_defaults" : {
    #         "misfire_grace_time": 30  # default is 60
    #     }
    # }
    # SKIP_PIKA_SETUP = True
    # SKIP_LOAD_ALL_INTERNAL_MODULES = True
    # SKIP_LOAD_ALL_MODULES = True
    # SKIP_LOAD_INTERNAL_MODULE_{module_name_upper_case} = True
    # SKIP_LOAD_MODULE_{module_name_upper_case} = True
    # OBJGRAPH_TRACE_AT_START = True
    # SYSTEMD_SERVICE_NAME = "antares_bot.service"
    # IGNORE_IMPORT_MODULE_ERROR = True
"""


def _hook_cfg():
    try:
        import bot_cfg as cfg  # type: ignore
    except ImportError:
        print(
            "./bot_cfg.py not found or cannot be imported, I will try to create one for you.",
            file=sys.stderr
        )
        create_blank_cfg()
        exit(1)
    except SyntaxError:
        print(
            "./bot_cfg.py has syntax error, please fix it before running.",
        )
        exit(1)
    from antares_bot import bot_default_cfg
    BaseConfig = bot_default_cfg.BaseConfig
    # start checking
    for k in dir(bot_default_cfg):
        default_config_class = getattr(bot_default_cfg, k)
        empty_checklist = getattr(default_config_class, 'non_empty', [])
        if isinstance(default_config_class, type) and issubclass(default_config_class, BaseConfig) and default_config_class != BaseConfig:
            if not hasattr(cfg, k):
                if len(empty_checklist) != 0:
                    print(
                        f"Please create {default_config_class.__name__} in bot_cfg.py and fill in the required fields first."
                        " See bot_default_cfg.py for more details."
                        " Or, you can remove the bot_cfg.py and run again to create a new one",
                        file=sys.stderr
                    )
                    exit(1)
                setattr(cfg, k, default_config_class)
                config_class = default_config_class
            else:
                config_class = getattr(cfg, k)
                for attr in default_config_class.iter_all_config_keys():
                    if not hasattr(config_class, attr):
                        if attr in empty_checklist:
                            print(
                                f"Please set {', '.join(empty_checklist)} in "
                                f"{default_config_class.__name__} in bot_cfg.py. See bot_default_cfg.py for more details.",
                                file=sys.stderr
                            )
                            exit(1)
                        setattr(config_class, attr, getattr(default_config_class, attr))


def init_pika(force_update: bool = False):
    # for better check
    gh_username = 'Antares0982'
    gh_repo = 'PikaInterface'
    gh_file = 'pika_interface.py'
    if not force_update and os.path.exists(gh_file):
        print(f"{gh_file} already exists, skipping download")
        return
    if force_update:
        print(f"Force updating {gh_file}")
    else:
        # read stdin to ensure the user is aware of the download
        read_input = input(
            "This operation will download the latest version of"
            f"{gh_file} from GitHub (Please note that using pika for logging also requires installing aio-pika, e.g. `pip install aio-pika`).\n"
            f"You may want to check the source code here: https://github.com/{gh_username}/{gh_repo}/blob/main/{gh_file}.\n"
            "Do you want to continue? (y/N)"
        )
        if not read_input.lower().strip().startswith('y'):
            print("Download skipped. If you want to skip this step forever, set SKIP_PIKA_SETUP in AntaresBotConfig to True.")
            # make sure the user is aware of this message
            import time
            time.sleep(2)
            return
    import subprocess
    command = f'curl -O https://raw.githubusercontent.com/{gh_username}/{gh_repo}/main/{gh_file}'
    print(command)
    code = subprocess.call(command, shell=True)
    if code != 0:
        print(f"failed to download {gh_file}", file=sys.stderr)
        return
    print(f"{gh_file} downloaded successfully.")


def read_user_cfg(cfg_class, section: str):
    import bot_cfg  # type: ignore
    class_name = cfg_class.__name__
    cfg = getattr(bot_cfg, class_name, None)
    return None if cfg is None else getattr(cfg, section, None)


def create_blank_cfg():
    try:
        with open("bot_cfg.py", "x", encoding="utf-8", opener=lambda x, y: os.open(x, y, 0o600)) as f:
            f.write(_BLANK_CFG)
    except FileExistsError:
        print(
            "bot_cfg.py already exists but cannot be imported, skipping creation.\n"
            "Please remove/modify it before running.",
            file=sys.stderr
        )
        return
    print(
        "bot_cfg.py created successfully."
        " Please fill in the required fields."
    )


_hook_cfg()
