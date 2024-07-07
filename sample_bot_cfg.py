class BasicConfig:
    """
    Basic sample config.
    TOKEN and MASTER_ID must be provided.
    Details refers to bot_default_cfg.py.
    """
    # LOCALE = 'en'
    # DATA_DIR = "data"
    TOKEN = "abcdef:123456"
    MASTER_ID = 123456789


class AntaresBotConfig:
    """
    Config to control the bot behavior.
    Details refers to bot_default_cfg.py.
    """
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
