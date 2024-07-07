# should not import anything other than python stdlib here
import os


def hook_cfg():
    try:
        import bot_cfg as cfg
    except ImportError:
        print("""bot_cfg.py not found, please create it in your working directory and fill in the necessary information first.
See antares_bot.bot_default_cfg for example.
>>> from antares_bot import bot_default_cfg"""
              )
        exit(1)
    import antares_bot.bot_default_cfg as bot_default_cfg
    BaseConfig = bot_default_cfg.BaseConfig
    # start checking
    for k in dir(bot_default_cfg):
        default_config_class = getattr(bot_default_cfg, k)
        empty_checklist = getattr(default_config_class, 'non_empty', [])
        if isinstance(default_config_class, type) and issubclass(default_config_class, BaseConfig) and default_config_class != BaseConfig:
            if not hasattr(cfg, k):
                if len(empty_checklist) != 0:
                    raise RuntimeError(
                        f"Please create {default_config_class.__name__} in bot_cfg.py and fill in the required fields first. See bot_default_cfg.py for more details."
                    )
                setattr(cfg, k, default_config_class)
                config_class = default_config_class
            else:
                config_class = getattr(cfg, k)
                for attr in default_config_class.iter_all_config_keys():
                    if not hasattr(config_class, attr):
                        if attr in empty_checklist:
                            raise RuntimeError(
                                f"Please set {', '.join(empty_checklist)} in {default_config_class.__name__} in bot_cfg.py. See bot_default_cfg.py for more details."
                            )
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
        read_input = input(f"""This operation will download the latest version of {gh_file} from GitHub (Please note that using pika for logging also requires to install aio-pika via `pip install aio-pika`).
You may want to check the source code here: https://github.com/{gh_username}/{gh_repo}/blob/main/{gh_file}.
Do you want to continue? (y/N)""")
        if not read_input.lower().strip().startswith('y'):
            print("Download skipped. If you want to skip this step forever, set SKIP_PIKA_SETUP in AntaresBotConfig to True.")
            # make sure the user is aware of this message
            import time
            time.sleep(2)
            return
    import subprocess
    command = f'curl https://api.github.com/repos/{gh_username}/{gh_repo}/contents/{gh_file} | jq -r ".content" | base64 --decode > {gh_file}'
    print(command)
    code = subprocess.call(command, shell=True)
    if code != 0:
        import sys
        print(f"failed to download {gh_file}", file=sys.stderr)
        return
    print(f"{gh_file} downloaded successfully.")
