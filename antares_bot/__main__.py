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
    """
    Bootstrap the bot.
    If from_cmd_line is True, it will parse the command line arguments.
    Otherwise it will use the kwargs.
    Supported kwargs: force_pika, log_level
    """
    # phase 1
    if from_cmd_line:
        # examine if working directory is in sys.path
        cwd = os.path.normpath(os.path.abspath(os.getcwd()))
        # if not, add to first. only do this if called from cmd line
        if cwd not in list(map(lambda x: os.path.normpath(os.path.abspath(x)), sys.path)):
            sys.path = [cwd] + sys.path

    # phase 2
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

    # phase 3
    # pika init phase. This is optional.
    def pika_init(_force_pika: bool) -> None:
        # cannot import init related things here
        from antares_bot.bot_default_cfg import AntaresBotConfig
        from antares_bot.init_hooks import init_pika, read_user_cfg
        # When init_hooks is imported, the cfg is automatically hooked.
        # Now we can call read_user_cfg safely.
        skip_pika_setup = False
        if not _force_pika:
            skip_pika_setup = read_user_cfg(AntaresBotConfig, "SKIP_PIKA_SETUP") or False
        if _force_pika or not skip_pika_setup:
            init_pika(force_update=_force_pika)
        # logging can start after pika inited.
        # As long as the logging module is imported, it is inited.
    pika_init(_force_pika=force_pika)

    import logging
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=log_level,
    )

    # phase 4
    # initiate bot
    from antares_bot.bot_inst import get_bot_instance
    bot_app = get_bot_instance()

    # phase 5
    # setup post_init. This is optional.
    if custom_post_init:
        bot_app.custom_post_init(custom_post_init())

    # DONE
    return bot_app


def main():
    bot_app = bootstrap(from_cmd_line=True)
    # start!
    bot_app.run()
    # exit
    return 0
