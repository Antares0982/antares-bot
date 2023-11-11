class HandleStatus(object):
    """
    Represent a status of event handling.
    :param:`normal`: True if the event is handled normally.
    :param:`block`: True if the event is fully handled and will not be passed to the next handler.
    """
    __slots__ = ["__block", "__normal"]

    def __init__(self, normal: bool, block: bool) -> None:
        self.__block: bool = block
        self.__normal: bool = normal

    def blocked(self):
        return self.__block

    def normal(self):
        return self.__normal


class HandleBlocked(HandleStatus):
    __slots__ = []

    def __init__(self, normal=True):
        super().__init__(normal, True)


handleIgnore = HandleStatus(True, False)
"""event not handled."""
handleSuccess = HandleStatus(True, True)
"""event handled successfully."""
handleFailed = HandleStatus(False, True)
"""event handling failed."""
