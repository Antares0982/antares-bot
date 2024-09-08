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
    Supported kwargs: log_level
    """
    # phase 1
    if from_cmd_line:
        # examine if working directory is in sys.path
        cwd = os.path.normpath(os.path.abspath(os.getcwd()))
        # if not, add to first. only do this if called from cmd line
        if cwd not in list(map(lambda x: os.path.normpath(os.path.abspath(x)), sys.path)):
            sys.path = [cwd] + sys.path

    # phase 2
    # define arg: log_level
    if from_cmd_line:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--log-level", type=str, default=ANTARES_BOT_LOG_LEVEL_DEFAULT, help="Logging level", required=False)
        args = parser.parse_args()
        log_level = args.log_level
    else:
        log_level = kwargs.get("log_level", ANTARES_BOT_LOG_LEVEL_DEFAULT)

    import logging
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=log_level,
    )

    # phase 3
    # initiate bot
    from antares_bot.bot_inst import get_bot_instance
    bot_app = get_bot_instance()

    # phase 4
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
