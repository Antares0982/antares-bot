from telegram import Update
from telegram.ext import CallbackContext
from bot_framework.utils.workflow import HandleStatus, handleIgnore


class BotHandleABC(object):
    def textHandler(self, update: Update, context: CallbackContext) -> HandleStatus:
        """To override."""
        return handleIgnore

    def photoHandler(self, update: Update, context: CallbackContext) -> HandleStatus:
        """To override."""
        return handleIgnore

    def channelHandler(self, update: Update, context: CallbackContext) -> HandleStatus:
        """To override."""
        return handleIgnore

    def editedChannelHandler(
        self, update: Update, context: CallbackContext
    ) -> HandleStatus:
        """To override."""
        return handleIgnore

    def buttonHandler(self, update: Update, context: CallbackContext) -> HandleStatus:
        """To override."""
        return handleIgnore
