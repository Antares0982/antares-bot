import os
import sys
from typing import TYPE_CHECKING, Awaitable, Callable


if TYPE_CHECKING:
    from antares_bot.bot_inst import TelegramBot


ANTARES_BOT_LOG_LEVEL_DEFAULT = "WARN"


def bootstrap(
    from_cmd_line=False,
    custom_post_init: Callable[[], Awaitable] | None = None,
    **kwargs
) -> "TelegramBot":
    if from_cmd_line:
        # examine if working directory is in sys.path
        cwd = os.getcwd()
        # if not, add to first. only do this if called from cmd line
        if cwd not in sys.path:
            sys.path = [cwd] + sys.path

    # define arg: force_pika and log_level
    if from_cmd_line:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--update-pika-interface", action="store_true", default=False,
                            help="Force download latest Pika interface from GitHub", required=False, dest="force_pika")
        parser.add_argument("--log-level", type=str, default=ANTARES_BOT_LOG_LEVEL_DEFAULT, help="Logging level", required=False)
        args = parser.parse_args()
        force_pika: bool = args.force_pika
        log_level = args.log_level
    else:
        force_pika = kwargs.get("force_pika", False)
        log_level = kwargs.get("log_level", ANTARES_BOT_LOG_LEVEL_DEFAULT)

    import logging
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=log_level,
    )

    def logger_init(_force_pika: bool) -> None:
        # cannot import init related things here
        from antares_bot.bot_default_cfg import AntaresBotConfig, BasicConfig
        from antares_bot.init_hooks import hook_cfg, init_pika, read_user_cfg
        hook_cfg()  # init bot_cfg here. now we can call read_user_cfg safely.
        skip_pika_setup = False
        if not _force_pika:
            skip_pika_setup = read_user_cfg(AntaresBotConfig, "SKIP_PIKA_SETUP") or False
        if _force_pika or not skip_pika_setup:
            init_pika(force_update=_force_pika)
        # log start after pika inited
        from antares_bot.bot_logging import log_start
        logger_top_name = read_user_cfg(BasicConfig, "BOT_NAME")
        log_start(logger_top_name)
    # logger init, after this the bot_cfg and antares_bot can be correctly imported
    logger_init(_force_pika=force_pika)
    # initiate bot
    from antares_bot.bot_inst import get_bot_instance
    bot_app = get_bot_instance()

    # setup post_init
    if custom_post_init:
        bot_app.custom_post_init(custom_post_init())

    return bot_app


def main():
    bot_app = bootstrap(from_cmd_line=True)
    # start!
    bot_app.run()
    # exit
    return 0
