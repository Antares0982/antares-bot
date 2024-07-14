class BasicLanguage:
    CANCELLED = {
        "zh-CN": "操作取消～",
        "en": "Cancelled~",
    }
    END = {
        "zh-CN": "结束",
        "en": "END",
    }
    INVALID_CHAT_TYPE = {
        "zh-CN": "不能在这里使用哦",
        "en": "Cannot be used in this chat type",
    }
    NO_PERMISSION = {
        "zh-CN": "你没有权限哦",
        "en": "Oops, you don't have permission...",
    }
    SHORTSEP = {
        "zh-CN": "、",
        "en": ", ",
    }
    STARTUP = {
        "zh-CN": "Bot启动！",
        "en": "Bot is live!",
    }
    UNKNOWN_ERROR = {
        "zh-CN": "哎呀，出现了未知的错误呢……",
        "en": "Oops, an unknown error occurred...",
    }
    SHUTDOWN_GOODBYTE = {
        "zh-CN": "主人再见QAQ",
        "en": "Goodbye master QAQ",
    }
    DEBUG_MODE_ON = {
        "zh-CN": "已开启debug模式",
        "en": "Debug mode on",
    }
    DEBUG_MODE_OFF = {
        "zh-CN": "已关闭debug模式",
        "en": "Debug mode off",
    }
    EXEC_FAILED = {
        "zh-CN": "执行失败……",
        "en": "Execution failed...",
    }
    EXEC_SUCCEEDED = {
        "zh-CN": "执行成功，返回值：{}",
        "en": "Execution succeeded, return value: {}",
    }
    NO_EXEC_COMMAND = {
        "zh-CN": "没有接收到命令诶",
        "en": "No executable command received",
    }
    FORWARD_MESSAGE_FROM_CHANNEL = {
        "zh-CN": "转发消息的来源频道id：`{}`",
        "en": "Forwarded from channel id: {}",
    }
    FORWARD_MESSAGE_FROM_GROUP = {
        "zh-CN": "转发消息的来源群id：`{}`",
        "en": "Forwarded from group id: `{}`",
    }
    FORWARD_MESSAGE_FROM_USER = {
        "zh-CN": "转发消息的来源用户id：`{}`",
        "en": "Forwarded from user id: `{}`",
    }
    FORWARD_FROM_HIDDEN_USER = {
        "zh-CN": "转发消息的来源用户已隐藏",
        "en": "Forwarded from a hidden user",
    }
    GROUP_ID = {
        "zh-CN": "群id：`{}`",
        "en": "Group id: `{}`",
    }
    REPLY_MESSAGE_USER_ID = {
        "zh-CN": "回复消息的用户id：`{}`",
        "en": "Reply message user id: `{}`",
    }
    USER_ID = {
        "zh-CN": "您的id：`{}`",
        "en": "Your id: `{}`",
    }
    NO_SUCH_COMMAND = {
        "zh-CN": "没有找到命令：{}",
        "en": "No such command: {}",
    }

    @classmethod
    def t(cls, d: dict[str, str], locale: str | None = None):
        """
        Translate message by language context.
        May raise if the locale augument is invalid.
        If locale is None, we use the default context, will not raise any error
        as long as the language dict `d` is not empty.
        """
        from antares_bot.multi_lang import t
        return t(d, locale)
