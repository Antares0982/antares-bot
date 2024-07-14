# AntaresBot
A Telegram bot framework wrapping many things.

### How to use

* `pip install antares_bot`. If you want to use pika for logging, `pip install antares_bot[pika]`
* Run `antares_bot` once in working directory to generate the `bot_cfg.py`
* Complete the `bot_cfg.py`
* Write your module in `modules` directory under working directory
* Run `antares_bot` to start your bot

### Examples

The documentation is far from completed, so here we only introduce a small part of features. We assume that you are already familiar with [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot).

Creating a bot with command `/echo`. First create a file `modules/echo.py`.

```python
from typing import TYPE_CHECKING

from antares_bot.module_base import TelegramBotModuleBase
from antares_bot.framework import command_callback_wrapper

if TYPE_CHECKING:
    from telegram import Update

    from antares_bot.context import RichCallbackContext


class Echo(TelegramBotModuleBase):
    def mark_handlers(self):
        return [self.echo]

    @command_callback_wrapper
    async def echo(self, update: "Update", context: "RichCallbackContext") -> bool:
        assert update.message is not None
        assert update.message.text is not None
        text = update.message.text.strip()
        if text.startswith("/echo"):
            text = text[len("/echo"):].strip()
        if text:
            await self.reply(text)
```

`antares_bot` will automatically scan the files under `modules` directory and find the class derived from `TelegramBotModuleBase`, with the same name pattern as the file (`CamelCase` for class name, `snake_case` for file name, for example: `my_example.py` corresponds to `class MyExample(TelegramBotModuleBase):`)

Module interfaces:

* Override `mark_handlers` to define the handlers. Handler wrappers can be found in `antares_bot.framework`.
* Override `do_init` to init. `__init__` is not recommanded.
* Override `post_init` to run some async function right after all modules are inited.
* Override `do_stop` to run some async function when exiting.

We use contexts to store the needed information for sending a message, so you only need to pass the message text when using the method `reply`.

Methods sending texts like `reply` (defined in `TelegramBotBaseWrapper`, `bot_method_wrapper.py`) have 4 different versions. These methods will automatically split the long text into parts, so it may send many messages. The original version returns id of the last message. V2 returns a list of ids of all messages (sorted). V3 returns the last `Message` object, and V4 returns all `Message` objects (sorted).

Creating a bot with command `/timer`

```python
import time
from typing import TYPE_CHECKING

from antares_bot.framework import command_callback_wrapper
from antares_bot.module_base import TelegramBotModuleBase
from antares_bot.context_manager import callback_job_wrapper


if TYPE_CHECKING:
    from telegram import Update

    from antares_bot.context import RichCallbackContext


class Timer(TelegramBotModuleBase):
    def mark_handlers(self):
        return [self.timer]

    @command_callback_wrapper
    async def timer(self, update: "Update", context: "RichCallbackContext") -> bool:
        assert update.message is not None
        assert update.message.text is not None

        @callback_job_wrapper
        async def cb(context_new):
            await self.reply("Time up!")
        self.job_queue.run_once(cb, 5, name=f"{time.time()}")
        return True
```

We use `callback_job_wrapper` to wrap the outer context for the nested function `cb`, and thus `reply` can reply to the correct message after 5 seconds.

i18n:

```python
from antares_bot.basic_language import BasicLanguage as Lang
await self.send_to(self.get_master_id(), Lang.t(Lang.UNKNOWN_ERROR))
```

You can define any i18n config like `Lang.UNKNOWN_ERROR`

```python
UNKNOWN_ERROR = {
    "zh-CN": "哎呀，出现了未知的错误呢……",
    "en": "Oops, an unknown error occurred...",
}
```

Call `set_lang` for each user to define their language.

Custom commands:

* `/exec` execute some python code (master only). `self` is defined to be the `TelegramBot` object in `bot_inst.py`.

  ```python
  /exec import objgraph
  return list(map(lambda x:x.misfire_grace_time, objgraph.by_type("Job")))
  # Execution succeeded, return value: [60, 60]
  ```

* `restart`, `stop` restart/stop the bot (master only). If `AntaresBotConfig.SYSTEMD_SERVICE_NAME` is configured, `/restart` will try to call `systemctl restart` for you. If `AntaresBotConfig.PULL_WHEN_STOP` is configured, these two commands will perform `git pull`.

* `get_id` see `/help get_id`.

* `help` check the docstring of command. For more information see `/help help`.

* `debug_mode` switch the logging level to `DEBUG` (master only).

Also, you can start the bot by yourself, without calling `antares_bot` in the command line.

```python
if __name__ == "__main__":
    from antares_bot import __main__
    inst = __main__.bootstrap()
    inst.run()
```



### Note

* Only support Python version >= 3.10

