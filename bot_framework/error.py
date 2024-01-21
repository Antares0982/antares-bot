
class BaseBotFrameworkException(Exception):
    pass


class InvalidQueryException(BaseBotFrameworkException):
    pass


class UserPermissionException(BaseBotFrameworkException):
    pass


class IgnoreChannelUpdateException(BaseBotFrameworkException):
    pass


class InvalidChatTypeException(BaseBotFrameworkException):
    pass


def permission_exceptions():
    return (
        UserPermissionException,
        IgnoreChannelUpdateException,
        InvalidChatTypeException,
    )
