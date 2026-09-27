# AntaresBot
A Telegram bot framework wrapping many things.

### How to use

* `pip install antares_bot`. If you want to use pika for logging, `pip install antares_bot[pika]`
* Run `antares_bot` once in working directory to generate the `bot_cfg.py`
* Complete the `bot_cfg.py`
* Write your module in `modules` directory under working directory
* Run `antares_bot` to start your bot

### Examples

#### Webhook mode

Install `pip install 'antares_bot[webhooks]'` and add `WEBHOOK_CONFIG` to your
existing `AntaresBotConfig` in `bot_cfg.py`. For HTTPS terminated by a reverse proxy:

```python
class AntaresBotConfig:
    WEBHOOK_CONFIG = {
        "listen": "127.0.0.1",
        "port": 8080,
        "url_path": "telegram-updates",
        "webhook_url": "https://bot.example.com/telegram-updates",
        "secret_token": "replace-with-a-random-secret",
        "drop_pending_updates": False,
    }
```

Forward that public URL to `http://127.0.0.1:8080/telegram-updates`, preserving
the `X-Telegram-Bot-Api-Secret-Token` header. PTB registers the webhook and checks
the secret on incoming requests. Use a secret containing only letters, digits,
underscores and hyphens (1–256 characters).

For direct HTTPS, use a publicly reachable listener and provide the certificate
and private key:

```python
class AntaresBotConfig:
    WEBHOOK_CONFIG = {
        "listen": "0.0.0.0",
        "port": 8443,
        "url_path": "telegram-updates",
        "webhook_url": "https://bot.example.com:8443/telegram-updates",
        "cert": "/etc/bot/cert.pem",
        "key": "/etc/bot/key.pem",
        "secret_token": "replace-with-a-random-secret",
    }
```

`WEBHOOK_CONFIG = None` (the default) uses polling. Any dictionary, including
`{}`, selects webhook mode. Keys follow PTB's
[`Application.run_webhook`](https://docs.python-telegram-bot.org/en/stable/telegram.ext.application.html#telegram.ext.Application.run_webhook)
parameters, except `stop_signals`, which the framework manages and rejects in
the dictionary. All update types are enabled and pending updates are dropped
by default, matching polling; override `allowed_updates` and
`drop_pending_updates` in the dictionary as needed. Other defaults come from PTB.

#### Custom Bot API server

These settings work with both polling and webhook mode:

```python
class AntaresBotConfig:
    BOT_API_BASE_URL = "http://localhost:8081/bot"
    BOT_API_BASE_FILE_URL = "http://localhost:8081/file/bot"
    BOT_API_LOCAL_MODE = True
```

The URL prefixes exclude the bot token; PTB appends it. Configure both URLs
when using a custom server: each unset URL independently uses Telegram's public
API default. `BOT_API_LOCAL_MODE` defaults to `False`; enable it for a Bot API
server running with `--local`. Local file paths must be accessible at the same
paths by the bot and server, including shared mounts when using containers.

Before migrating from the public API to a local server, call `log_out` against
the public API as part of deployment. The framework does not migrate sessions
automatically. See Telegram's
[local server instructions](https://core.telegram.org/bots/api#using-a-local-bot-api-server).

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
            text = text[len("/echo") :].strip()
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
