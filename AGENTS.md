# AGENTS.md

This file provides guidance to coding agents when working with code in this repository.

## What this repo is

`antares_bot/` is a published PyPI package — a framework wrapping python-telegram-bot (PTB).
`tests/` is tracked too, but is not packaged (`[tool.setuptools] packages = ["antares_bot"]`).
Everything else at the root (`bot_cfg.py`, `main.py`, `modules/`, `data/`, `test.py`) is
gitignored: it is a local sandbox for running the framework, not part of the deliverable.
Changes belong in `antares_bot/` (and `tests/`) unless you are deliberately exercising the sandbox.

## Environment & commands

Nix devshell (direnv, `use flake`); Python 3.14 lives at `.nix-pyenv/bin/python`.

```bash
.nix-pyenv/bin/python main.py     # run the bot (main.py calls bootstrap().run())
.nix-pyenv/bin/python -m pytest   # run the test suite (from the repo root)
pyright                           # type-check the entire repository
ruff format .                     # format the entire repository
ruff format --check .             # verify formatting without changes
nix build                         # build the package (default.nix)
nix build .#ptb                   # build the PTB fork; test.sh copies its telegram/ out for stubs
```

`python -m antares_bot` does **not** start anything — `__main__.py` has no `if __name__` guard;
the real entry points are the `antares_bot` console script and `main.py`.

There is no CI. Every change must leave the entire repository passing default `pyright` checks and
Ruff formatting; run `pyright` and `ruff format --check .` from the repository root before declaring
work complete. Root `test.py` is a scratch script for the fork-and-SIGKILL shutdown guard, not tests.

## Tests

`tests/` is a pytest suite (pytest + pytest-asyncio in `asyncio_mode = "auto"`, both in
`py_requirements.nix` and the `test` extra). It is offline: no network, no Telegram token, no
real RabbitMQ. Run it from the repo root — `pythonpath = ["."]` and `ModuleKeeper`'s relative
`modules/` walk both depend on the CWD.

`tests/conftest.py` installs a **synthetic `bot_cfg` module into `sys.modules` at import time**,
before anything imports `antares_bot` — otherwise `init_hooks._hook_cfg()` would pick up the
local sandbox `bot_cfg.py` (or `exit(1)`). Patch config with
`monkeypatch.setattr(cfg.AntaresBotConfig, "KEY", v, raising=False)`; `read_user_cfg` re-reads the
module each call. An autouse fixture saves/restores every process global
(`GlobalLoggerInstance.INST`, `DataBasesManager.INST`, `LangContextManager.INST`,
`bot_inst.__bot_singleton`, module `INST`s).

Codex must run `.nix-pyenv/bin/python -m pytest` outside its Linux sandbox: sandboxed aiosqlite
worker threads do not wake the asyncio loop. `.codex/rules/pytest.rules` grants only that prefix.

Not covered, deliberately: `run()`/`run_polling`, `_post_run` restart,
`_do_post_init`/`_do_post_stop`, `obj_graph.py`, `fetch_url`.

Three long-standing bugs the suite found and now pins down — do not "simplify" these back:

- `force_longtext_split` must budget the `"\n"` separators into `counting`, not just subtract one
  `sep_len`. Without it, many short lines produce chunks well over Telegram's hard 4096 cap.
- `CallbackBase.__init__` must default `_pre_executer` **before** `on_init()`, which is what stores
  the real one. It was the other way round from the day `_btn_pre_executer` was added (ed65814,
  2023-12), so `btn_click_wrapper` never auto-answered a callback query.
- `PikaGlobalLoggerInstance.stop()` must post its sentinel through `call_soon_threadsafe`, like
  `enqueue()` does; a direct `put_nowait` overtakes records still pending and drops the last log
  lines before shutdown.

## Hard dependency on a PTB fork

Requires `antares-ptb` (github.com/Antares0982/python-telegram-bot, pinned in `ptb-src.nix`,
currently `v22.7`), not upstream PTB. It supplies APIs upstream lacks, e.g.
`from telegram.ext import ConversationHandlerEx`. Bumping the fork means editing `ptb-src.nix`
rev + sha256 (`requirements.txt` carries a separate pip pin).

## Architecture

### Startup / shutdown chain

`bootstrap()` (`__main__.py`) → `get_bot_instance()` (singleton, overridable via
`register_bot_class`) → `TelegramBot.__init__` builds the PTB `Application` with `RichCallbackContext`,
`ChatData`/`UserData` and `JobQueueEx` → `TelegramBot.run()` loads modules, converts their marked
callbacks to PTB handlers, registers `exception_handler`, schedules the daily job, then `run_polling`.
`_do_post_init` / `_do_post_stop` fan out to every module and time each one.

Shutdown: signal handlers → `true_stop()` → `_guard_stop()` arms a faulthandler watchdog that
calls `os._exit(1)` after 10s if the process hasn't exited. `SIGTERM`/`SIGABRT` set `_exit_fast` (skips
`git pull`). Restart uses `systemctl restart` when `SYSTEMD_SERVICE_NAME` is set, else re-execs
`sys.orig_argv`.

### Config: import-time hook

`init_hooks.py` calls `_hook_cfg()` **at import time** (bottom of the file), and nearly everything
imports it transitively. It imports top-level `bot_cfg` from the *current working directory*,
back-fills any key missing from the matching `bot_default_cfg` class, and `exit(1)`s (creating a
template `bot_cfg.py`) if required keys are absent. Consequences:

- Any process touching `antares_bot` must run with a valid `bot_cfg.py` in CWD.
- New config keys: add to the class in `bot_default_cfg.py`, read with
  `read_user_cfg(AntaresBotConfig, "KEY")` — returns `None` when unset, so callers do the defaulting.

### Module discovery

`ModuleKeeper._import_all_modules()` loads `antares_bot/internal_modules/*.py` first, then walks
`modules/` under CWD. A file is only picked up if it defines a class whose CamelCase name matches
the snake_case filename (`my_example.py` → `class MyExample(TelegramBotModuleBase)`); a mismatch is
silently skipped. `MODULE_PRIORITY` (0–256, default 128) orders init, ties broken by name.
`SKIP_LOAD_MODULE_<NAME>` / `SKIP_LOAD_ALL_*` config keys gate loading.

Module lifecycle — override these, never `__init__`:
`do_init()` (sync) → `post_init(app)` (async, all modules gathered) → `daily_job()` (00:00) → `do_stop()`.
`mark_handlers()` returns the callbacks to register. Each module class keeps a `INST` singleton
(`Module.get_inst()`), and modules reach each other via `self.parent.get_module(cls_or_name)`.

### Context is a ContextVar — the central design point

`RichCallbackContext` is stored in a `ContextVar` (`context_manager.py`). `CallbackBase.__call__`
enters `ContextHelper(context)` around every handler, which is why `self.reply(text)`, `self.check(...)`
and `Lang.t(...)` need no `update` argument.

Anything running **outside** a handler frame (job-queue callbacks, `create_task`) loses that context.
Wrap those with `callback_job_wrapper` (see `modules/timer.py`). `ContextReverseHelper` deliberately
installs an `InvalidContext` that raises a pointed error instead of silently replying to the wrong
chat — used for `daily_job` and patched into `apscheduler.add_job` by `JobQueueEx`.

### Handlers are descriptor objects, not functions

`command_callback_wrapper` / `msg_handle_wrapper` / `btn_click_wrapper` (`framework.py`) return
`CallbackBase` instances; `__get__` binds the module instance and `to_handler()` produces the PTB
handler at `run()` time. The command name is the *function name*. The docstring becomes `/help`
text, conventionally first line `cmd - short description`, rest is the long help.

Permission checks (`self.check(CheckLevel.MASTER, ConditionLimit.PRIVATE)`) raise; `CallbackBase`
catches those exceptions and replies with the localized message, and `exception_handler` catches
any that leak.

### Sending messages

`bot_method_wrapper.py` (`TelegramBotBaseWrapper`) — each of `reply` / `reply_to` / `send_to` has
four variants: base → last message id, `_v2` → all ids, `_v3` → last `Message`, `_v4` → all
`Message`s, because long text is auto-split by `text_process.longtext_split`. Sends retry on
transient `TelegramError` and retry once more after dropping `reply_to_message_id` or `parse_mode`
when Telegram rejects them.

A hand-written `antares_bot/bot_method_wrapper.pyi` mirrors these signatures for type checkers —
**update it whenever you change a signature there**, it is not generated.

### Logging

`bot_logging._log_start()` also runs at import time. Use `get_logger(__name__)`; `run()` injects a
`_LOGGER` into any module file lacking one. With pika enabled, records publish to RabbitMQ over the
bot's own event loop: they buffer in a deque until `start_logger()` (post-init) and drain at
`stop_logger()` (post-stop), so `_LOGGER` calls are safe before the loop exists.

### i18n

Language entries are plain `dict[locale, str]` class attributes (`basic_language.py`), resolved by
`Lang.t(Lang.KEY)` against the per-user locale from the current context, falling back to
`BasicConfig.LOCALE` and finally the first value.

### sqlite

`sqlite/manager.py` wraps `aiosqlite`: `Database.connect()` registers with the `DataBasesManager`
singleton, which closes every database during post-stop, so modules need not close theirs.
`TableProxy` derives columns/primary keys from `PRAGMA table_info` and builds the upsert SQL.
