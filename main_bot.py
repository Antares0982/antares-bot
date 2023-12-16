#!/usr/bin/python3 -O
import logging

# should not import anything other than python stdlib here


def script_init():
    from init_hooks import hook_cfg, generate_language
    hook_cfg()
    import bot_cfg
    generate_language(bot_cfg.LOCALE)


def main():
    script_init()
    #
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.WARN,
    )
    #
    from bot_inst import get_bot_instance
    bot_app = get_bot_instance()
    bot_app.start()


if __name__ == "__main__":
    main()
