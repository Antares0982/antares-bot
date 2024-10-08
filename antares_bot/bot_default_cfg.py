class BaseConfig:
    @classmethod
    def iter_all_config_keys(cls):
        keys = dir(cls)
        for k in keys:
            if k.startswith("__") or k != k.upper():
                continue
            yield k


class BasicConfig(BaseConfig):
    """
    Basic config.
    Create a class with same name in bot_cfg.py to override the default value.
    TOKEN and MASTER_ID must be overriden.
    """
    non_empty = [
        "TOKEN",
        "MASTER_ID",
    ]
    LOCALE = 'en'
    DATA_DIR = "data"
    TOKEN = "abcdef:123456"
    MASTER_ID = 123456789


class AntaresBotConfig(BaseConfig):
    """
    Config to control the bot behavior.
    Create a class with same name in bot_cfg.py to set the value.
    """
