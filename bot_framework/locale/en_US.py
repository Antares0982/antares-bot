from bot_framework.locale.general import Locale


class EN_US(Locale):
    button_invalid = "(*￣︿￣) This button is now invalid"
    welcome = "Bot is live!"


if __name__ != "__main__":
    EN_US.setCurrentLocale()
