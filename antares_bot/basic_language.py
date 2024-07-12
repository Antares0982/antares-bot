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
        "zh-CN": "不能在聊天类型：{}中使用哦",
        "en": "Cannot be used in chat type: {}",
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
