def main() -> None:
    import os
    import sys

    # examine if working directory is in sys.path
    cwd = os.getcwd()
    # if not, add to first
    if cwd not in sys.path:
        sys.path = [cwd] + sys.path

    import argparse
    import logging

    # define arg: force pika
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-pika-interface", action="store_true", default=False,
                        help="Force download latest Pika interface from GitHub", required=False, dest="force_pika")

    args = parser.parse_args()

    def script_init(force_pika: bool) -> None:
        from antares_bot.init_hooks import hook_cfg, init_pika
        hook_cfg()  # checked cfg here
        skip_pika_setup = False
        if not force_pika:
            from bot_cfg import AntaresBotConfig
            skip_pika_setup = getattr(AntaresBotConfig, "SKIP_PIKA_SETUP", False)
        if force_pika or not skip_pika_setup:
            init_pika(force_update=force_pika)
        # log start after pika inited
        from antares_bot.bot_logging import log_start
        log_start()
        # import bot_cfg
        # generate_language(bot_cfg.BasicConfig.LOCALE)

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.WARN,
    )
    force_pika = args.force_pika
    #
    script_init(force_pika=force_pika)
    #
    from antares_bot.bot_inst import get_bot_instance
    bot_app = get_bot_instance()

    async def at_init():
        from antares_bot.basic_language import BasicLanguage
        from bot_cfg import BasicConfig
        MASTER_ID = BasicConfig.MASTER_ID
        await bot_app.send_to(MASTER_ID, BasicLanguage.STARTUP)
    bot_app.custom_post_init(at_init())
    bot_app.pull_when_stop()
    bot_app.run()
    # exit
