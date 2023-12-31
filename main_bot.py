#!/usr/bin/python3 -O
import logging

# should not import anything other than python stdlib here


def script_init() -> None:
    from bot_framework.init_hooks import hook_cfg, generate_language, init_pika
    hook_cfg()
    init_pika()
    # log start after pika inited
    from bot_framework.bot_logging import log_start
    log_start()
    import bot_cfg
    generate_language(bot_cfg.LOCALE)


def on_exit() -> None:
    from bot_framework.bot_logging import stop_logger
    stop_logger()


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    #
    script_init()
    #
    from bot_framework.bot_inst import get_bot_instance
    bot_app = get_bot_instance()
    bot_app.run()
    # exit
    on_exit()


if __name__ == "__main__":
    main()
