from bot_framework.locale.general import Locale, locale


class ZH_CN(Locale):
    button_invalid = "(*￣︿￣) 这个按钮请求已经无效了"
    welcome = "Bot启动！"


if __name__ != "__main__":
    ZH_CN.internalSetLocale()
