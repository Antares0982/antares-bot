import asyncio
import sys
from logging import DEBUG as LOGLEVEL_DEBUG
from typing import TYPE_CHECKING, Any, List, Optional, Union, cast

from telegram import MessageOriginChannel, MessageOriginChat, MessageOriginUser, Update

from antares_bot.basic_language import BasicLanguage as Lang
from antares_bot.bot_logging import get_logger, get_root_logger
from antares_bot.framework import command_callback_wrapper
from antares_bot.module_base import TelegramBotModuleBase
from antares_bot.permission_check import CheckLevel
from antares_bot.text_process import trim_spaces_before_line
from antares_bot.utils import markdown_escape

if TYPE_CHECKING:
    from telegram.ext import BaseHandler

    from antares_bot.bot_inst import TelegramBot
    from antares_bot.context import RichCallbackContext
    from antares_bot.framework import CallbackBase

from antares_bot.test_commands import *  # noqa: F403
from antares_bot.bot_inst import get_bot_instance  # noqa: F401

_LOGGER = get_logger(__name__)

_INTERNAL_TEST_EXEC_COMMAND_PREFIX = """\
async def _t__():
    from bot_cfg import BasicConfig
    MASTER_ID = BasicConfig.MASTER_ID
    self = get_bot_instance()
"""

_IS_PY313 = sys.version_info >= (3, 13)


class AntaresBuiltin(TelegramBotModuleBase):
    MODULE_PRIORITY = 10

    if TYPE_CHECKING:
        parent: "TelegramBot"

    def do_init(self) -> None:
        self._old_log_level: Optional[int] = None

    def mark_handlers(self) -> List[Union["CallbackBase", "BaseHandler"]]:
        return [
            self.stop,
            self.restart,
            self.debug_mode,
            self.exec,
            self.get_id,
            self.help,
        ]

    @command_callback_wrapper
    async def stop(self, u, c):
        """
        stop - stop the bot
        Stop the bot.
        """
        self.check(CheckLevel.MASTER)
        self.parent.true_stop()

    @command_callback_wrapper
    async def restart(self, update: Update, context: "RichCallbackContext"):
        """
        Restart the bot.
        """
        self.check(CheckLevel.MASTER)
        self.parent._post_stop_restart_flag = True
        self.parent.true_stop()

    @command_callback_wrapper
    async def debug_mode(self, update, context):
        """
        debug_mode - switch debug mode on or off
        Switch debug mode on/off.
        """
        self.check(CheckLevel.MASTER)
        root_logger = get_root_logger()
        old_level = root_logger.level
        if old_level == LOGLEVEL_DEBUG:
            if self._old_log_level is None:
                raise RuntimeError("Invalid state: maybe default debug level is DEBUG!")
            self.debug_info("debug off")
            root_logger.setLevel(self._old_log_level)
            self._old_log_level = None
            await self.reply(Lang.t(Lang.DEBUG_MODE_OFF))
        else:
            self._old_log_level = old_level
            root_logger.setLevel(LOGLEVEL_DEBUG)
            self.debug_info("debug on")
            await self.reply(Lang.t(Lang.DEBUG_MODE_ON))

    async def _internal_exec(self, command: str):
        if not command:
            await self.error_info(Lang.t(Lang.NO_EXEC_COMMAND))
            return
        codes = command.split("\n")
        try:
            code_string = _INTERNAL_TEST_EXEC_COMMAND_PREFIX + "".join(
                f"\n    {line}" for line in codes
            )
            _LOGGER.warning("executing: %s", code_string)
            if _IS_PY313:
                tmp_locals: dict[str, Any] = {}
                exec(code_string, locals=tmp_locals)  # pylint: disable=exec-used
                ans = await tmp_locals["_t__"]()
            else:
                exec(code_string)  # pylint: disable=exec-used
                ans = await locals()["_t__"]()
        except Exception:
            asyncio.get_running_loop().create_task(self.reply(Lang.t(Lang.EXEC_FAILED)))
            raise
        await self.reply(
            Lang.t(Lang.EXEC_SUCCEEDED).format(ans), parse_mode="MarkdownV2"
        )

    @command_callback_wrapper
    async def exec(self, update: Update, context: "RichCallbackContext"):
        """
        exec - execute python code
        Execute python code.
        `antares_bot.test_commands` is wildcard imported by default.
        You can use `self` to refer to the bot instance.
        """
        self.check(CheckLevel.MASTER)
        if context.args is None or len(context.args) == 0:
            try:
                reply_to = update.message.reply_to_message.text.strip()  # type: ignore
            except AttributeError:
                await self.error_info(Lang.t(Lang.NO_EXEC_COMMAND))
                return
            await self._internal_exec(reply_to)
            return
        assert update.message is not None and update.message.text is not None
        command = self.get_message_after_command(update)
        await self._internal_exec(command)

    @command_callback_wrapper
    async def get_id(self, update: Update, context: "RichCallbackContext"):
        """
        get_id - get the user id / chat id
        Get the user id / chat id.
        If replying to a forwarded message, get the id information of the forward prigin.
        Otherwise:
        - In a group chat:
          - If replying to a message, get the user id of the replied message;
          - otherwise, get the id of you and the group.
        - In a private chat: get your id.
        """
        if update.message is not None and update.message.reply_to_message is not None:
            message = update.message.reply_to_message
            forward_origin = message.forward_origin
            if forward_origin is not None:
                if forward_origin.type == forward_origin.CHANNEL:
                    forward_origin_channel = cast(MessageOriginChannel, forward_origin)
                    return await self.reply(
                        Lang.t(Lang.FORWARD_MESSAGE_FROM_CHANNEL).format(
                            forward_origin_channel.chat.id
                        ),
                        parse_mode="MarkdownV2",
                    )
                elif forward_origin.type == forward_origin.CHAT:
                    forward_origin_chat = cast(MessageOriginChat, forward_origin)
                    return await self.reply(
                        Lang.t(Lang.FORWARD_MESSAGE_FROM_GROUP).format(
                            forward_origin_chat.sender_chat.id
                        ),
                        parse_mode="MarkdownV2",
                    )
                elif forward_origin.type == forward_origin.USER:
                    forward_origin_user = cast(MessageOriginUser, forward_origin)
                    return await self.reply(
                        Lang.t(Lang.FORWARD_MESSAGE_FROM_USER).format(
                            forward_origin_user.sender_user.id
                        ),
                        parse_mode="MarkdownV2",
                    )
                elif forward_origin.type == forward_origin.HIDDEN_USER:
                    return await self.reply(Lang.t(Lang.FORWARD_FROM_HIDDEN_USER))
        if (
            context.is_group_chat()
            and update.message is not None
            and update.message.reply_to_message is not None
            and update.message.reply_to_message.from_user is not None
        ):
            return await self.reply(
                f"{Lang.t(Lang.GROUP_ID).format(context.chat_id)}\n{Lang.t(Lang.REPLY_MESSAGE_USER_ID).format(update.message.reply_to_message.from_user.id)}",
                parse_mode="MarkdownV2",
            )
        elif context.is_group_chat():
            return await self.reply(
                f"{Lang.t(Lang.GROUP_ID).format(context.chat_id)}\n{Lang.t(Lang.USER_ID).format(context.user_id)}",
                parse_mode="MarkdownV2",
            )
        else:
            return await self.reply(
                Lang.t(Lang.USER_ID).format(context.user_id), parse_mode="MarkdownV2"
            )

    async def _internal_full_help(self, context: "RichCallbackContext"):
        ret = ""
        for command in self.parent.handler_docs.keys():
            ret += f"`/help {command}`\n"
        await self.success_info(ret, parse_mode="Markdown")

    @staticmethod
    def _match_helpdoc_line0_command_list_format(
        command: str, doc: str, is_extract=True
    ):
        doc = doc.strip()
        _left, _, _right = doc.partition("\n")
        line0 = _left
        command_prefix = command + " - "
        if line0.startswith(command_prefix):
            return line0 if is_extract else _right
        return None if is_extract else doc

    def _internal_generate_command_list(self) -> str:
        content = []
        for command, doc in self.parent.handler_docs.items():
            tmp = self._match_helpdoc_line0_command_list_format(command, doc)
            if tmp is not None:
                content.append(tmp)
        if len(content) == 0:
            return ""
        content.sort()
        content = ["```"] + content + ["```"]
        return "\n".join(content)

    @command_callback_wrapper
    async def help(self, update: Update, context: "RichCallbackContext"):
        """
        help - show command helps
        `/help [command]`: get the docstring for commands.
        `/help to-command-list`: get the command list for setting up at BotFather.
        """
        assert context.args is not None
        if len(context.args) == 0:
            return await self._internal_full_help(context)

        command = context.args[0]
        if command == "to-command-list":
            content = self._internal_generate_command_list()
            if content:
                return await self.reply(content, parse_mode="Markdown")
            else:
                return await self.error_info("No command list available")
        doc = self.parent.handler_docs.get(command)
        if doc is None:
            return await self.error_info(Lang.t(Lang.NO_SUCH_COMMAND).format(command))
        doc = self._match_helpdoc_line0_command_list_format(
            command, doc, is_extract=False
        )
        if doc is not None:
            doc = trim_spaces_before_line(doc)
        if not doc:
            doc = "No doc"
        return await self.success_info(
            f"/{markdown_escape(command)}:\n{doc}", parse_mode="Markdown"
        )
