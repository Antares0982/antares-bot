class BasicLanguage:
    CANCELLED = {
        "zh-CN": "操作取消～",
        "en": "Cancelled~",
    }
    END = {
        "zh-CN": "结束",
    }
    INVALID_CHAT_TYPE = {
        "zh-CN": "不能在聊天类型：{}中使用哦",
    }
    NO_PERMISSION = {
        "zh-CN": "你没有权限哦",
    }
    SHORTSEP = {
        "zh-CN": "、",
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
    def t(cls, d: dict[str, str]):
        from antares_bot.multi_lang import t
        return t(d)
