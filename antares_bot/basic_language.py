from antares_bot.multi_lang.lang_meta import LanguageMeta


class BasicLanguage(metaclass=LanguageMeta):
    CANCELLED = {
        "zh": "操作取消～",
        "en": "Cancelled~",
    }
    END = {
        "zh": "结束",
    }
    INVALID_CHAT_TYPE = {
        "zh": "不能在聊天类型：{}中使用哦",
    }
    NO_PERMISSION = {
        "zh": "你没有权限哦",
    }
    SHORTSEP = {
        "zh": "、",
    }
    STARTUP = {
        "zh": "Bot启动！",
        "en": "Bot is live!",
    }
    UNKNOWN_ERROR = {
        "zh": "哎呀，出现了未知的错误呢……",
        "en": "Oops, an unknown error occurred...",
    }
