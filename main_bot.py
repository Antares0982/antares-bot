#!/usr/bin/python3 -O
import logging


# should not import anything other than python stdlib here


def script_init() -> None:
    from bot_framework.init_hooks import generate_language, hook_cfg, init_pika
    hook_cfg()
    init_pika()
    # log start after pika inited
    from bot_framework.bot_logging import log_start
    log_start()
    import bot_cfg
    generate_language(bot_cfg.LOCALE)


def on_exit() -> None:
    print("Stopped gracefully.")


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.WARN,
    )
    #
    script_init()
    #
    from bot_framework.bot_inst import get_bot_instance
    bot_app = get_bot_instance()
    async def at_init():
        from bot_framework import language
        from bot_cfg import MASTER_ID
        await bot_app.send_to(MASTER_ID, language.STARTUP)
    bot_app.custom_post_init(at_init())
    bot_app.pull_when_stop()
    bot_app.run()
    # exit
    on_exit()


if __name__ == "__main__":
    main()
