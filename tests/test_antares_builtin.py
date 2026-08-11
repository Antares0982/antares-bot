import pytest

from antares_bot.framework import CommandCallback
from antares_bot.internal_modules.antares_builtin import AntaresBuiltin


@pytest.fixture
def builtin(dummy_parent):
    module = AntaresBuiltin(dummy_parent)
    module.do_init()
    return module


match_line0 = AntaresBuiltin._match_helpdoc_line0_command_list_format


# ------------------------------------ _match_helpdoc_line0_command_list_format


def test_extract_returns_the_summary_line():
    doc = "help - show command helps\nlong description"
    assert match_line0("help", doc) == "help - show command helps"


def test_extract_returns_none_without_the_prefix():
    assert match_line0("help", "no summary here\nrest") is None


def test_extract_ignores_surrounding_whitespace():
    doc = "\n        help - show command helps\n        rest\n        "
    assert match_line0("help", doc) == "help - show command helps"


def test_non_extract_returns_the_remainder():
    doc = "help - show command helps\nlong description"
    assert match_line0("help", doc, is_extract=False) == "long description"


def test_non_extract_returns_the_whole_doc_when_unmatched():
    doc = "no summary here\nrest"
    assert match_line0("help", doc, is_extract=False) == doc


def test_a_similar_command_name_does_not_match():
    doc = "helper - something\nrest"
    assert match_line0("help", doc) is None


def test_a_single_line_doc():
    assert match_line0("stop", "stop - stop the bot") == "stop - stop the bot"
    assert match_line0("stop", "stop - stop the bot", is_extract=False) == ""


# ----------------------------------------------- _internal_generate_command_list


def test_generate_command_list_collects_and_sorts(builtin, dummy_parent):
    dummy_parent.handler_docs = {
        "zeta": "zeta - last one\nbody",
        "alpha": "alpha - first one\nbody",
        "undocumented": "no summary line",
    }
    content = builtin._internal_generate_command_list()
    assert content.splitlines() == [
        "```",
        "alpha - first one",
        "zeta - last one",
        "```",
    ]


def test_generate_command_list_is_empty_without_matches(builtin, dummy_parent):
    dummy_parent.handler_docs = {"x": "no summary line"}
    assert builtin._internal_generate_command_list() == ""


def test_generate_command_list_with_no_commands(builtin, dummy_parent):
    dummy_parent.handler_docs = {}
    assert builtin._internal_generate_command_list() == ""


# ------------------------------------------------------------------- handlers


def test_module_priority_runs_early():
    assert AntaresBuiltin.MODULE_PRIORITY == 10


def test_mark_handlers_exposes_the_builtin_commands(builtin):
    handlers = builtin.mark_handlers()
    commands = {h.kwargs["command"] for h in handlers}
    assert commands == {"stop", "restart", "debug_mode", "exec", "get_id", "help"}


def test_every_handler_is_a_command_callback_with_a_doc(builtin):
    for handler in builtin.mark_handlers():
        assert isinstance(handler, CommandCallback)
        assert handler.__doc__, handler.kwargs["command"]


def test_documented_commands_use_the_command_list_convention(builtin):
    """Commands whose docstring starts with `name - summary` show up in
    `/help to-command-list`; the rest deliberately do not."""
    listed = set()
    for handler in builtin.mark_handlers():
        command = handler.kwargs["command"]
        if match_line0(command, handler.__doc__) is not None:
            listed.add(command)
    assert listed == {"stop", "debug_mode", "exec", "get_id", "help"}


# ------------------------------------------------------------------ /help


class ReplyRecorder:
    def __init__(self):
        self.messages: list[str] = []
        self.ok: list[bool] = []

    async def reply(self, text, **kwargs):
        self.messages.append(text)
        return 1

    async def success_info(self, text, **kwargs):
        self.messages.append(text)
        self.ok.append(True)
        return True

    async def error_info(self, text, **kwargs):
        self.messages.append(text)
        self.ok.append(False)
        return False


@pytest.fixture
def replies(builtin, monkeypatch):
    recorder = ReplyRecorder()
    for name in ("reply", "success_info", "error_info"):
        monkeypatch.setattr(builtin, name, getattr(recorder, name))
    return recorder


async def test_help_lists_every_command(builtin, dummy_parent, replies, fake_context):
    dummy_parent.handler_docs = {"a": "a - x", "b": "b - y"}
    ctx = fake_context()
    ctx.args = []
    await builtin.help(None, ctx)
    assert replies.messages == ["`/help a`\n`/help b`\n"]


async def test_help_for_one_command_returns_the_body(
    builtin, dummy_parent, replies, fake_context
):
    dummy_parent.handler_docs = {"a": "a - summary\n    detailed body"}
    ctx = fake_context()
    ctx.args = ["a"]
    await builtin.help(None, ctx)
    assert replies.messages == ["/a:\ndetailed body"]
    assert replies.ok == [True]


async def test_help_for_an_unknown_command(
    builtin, dummy_parent, replies, fake_context
):
    dummy_parent.handler_docs = {}
    ctx = fake_context()
    ctx.args = ["nope"]
    await builtin.help(None, ctx)
    assert replies.messages == ["No such command: nope"]
    assert replies.ok == [False]


async def test_help_to_command_list(builtin, dummy_parent, replies, fake_context):
    dummy_parent.handler_docs = {"a": "a - summary\nbody"}
    ctx = fake_context()
    ctx.args = ["to-command-list"]
    await builtin.help(None, ctx)
    assert replies.messages == ["```\na - summary\n```"]


async def test_help_to_command_list_without_any_documented_command(
    builtin, dummy_parent, replies, fake_context
):
    dummy_parent.handler_docs = {"a": "undocumented"}
    ctx = fake_context()
    ctx.args = ["to-command-list"]
    await builtin.help(None, ctx)
    assert replies.messages == ["No command list available"]
    assert replies.ok == [False]


async def test_help_for_a_command_without_a_body(
    builtin, dummy_parent, replies, fake_context
):
    dummy_parent.handler_docs = {"a": "a - summary"}
    ctx = fake_context()
    ctx.args = ["a"]
    await builtin.help(None, ctx)
    assert replies.messages == ["/a:\nNo doc"]


# ------------------------------------------------------------------ /exec


async def test_exec_without_a_command_reports_it(builtin, replies, fake_context):
    await builtin._internal_exec("")
    assert replies.messages == ["No executable command received"]


async def test_exec_runs_code_and_reports_the_result(builtin, replies, fake_context):
    await builtin._internal_exec("return 1 + 1")
    assert replies.messages == ["Execution succeeded, return value:\n```\n2\n```"]


async def test_exec_can_reach_the_master_id(builtin, replies, cfg, monkeypatch):
    monkeypatch.setattr(cfg.BasicConfig, "MASTER_ID", 4242)
    await builtin._internal_exec("return MASTER_ID")
    assert "4242" in replies.messages[0]


async def test_exec_reports_failure_and_reraises(builtin, replies):
    with pytest.raises(ZeroDivisionError):
        await builtin._internal_exec("return 1 / 0")
    import asyncio

    await asyncio.sleep(0)
    assert "Execution failed..." in replies.messages
