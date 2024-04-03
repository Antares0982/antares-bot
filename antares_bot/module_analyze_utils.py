import importlib
import sys
from types import ModuleType
from typing import Optional, Type, TypeVar, cast

from antares_bot.bot_logging import get_logger


_T = TypeVar("_T")

_LOGGER = get_logger(__name__)


def get_module_from_name(module_name: str):
    """
    Return:
        module, is_reload

    Note:
        Does not raise any exception
    """
    try:
        if module_name in sys.modules:
            return sys.modules[module_name], True
        else:
            return importlib.import_module(module_name), False
    except Exception as e:
        _LOGGER.error(e)
        return None, False


def get_module_class_from_module(module: ModuleType, instance_class: Optional[Type[_T]] = None) -> Optional[Type[_T]]:
    """
    Return:
        kls

    Note:
        Does not reload. Does not raise any exception
    """
    try:
        modulefile_name = module.__name__.split(".")[-1]
        modulefile_names = modulefile_name.split("_")
        class_name = ''.join([name.capitalize() for name in modulefile_names])
        kls = getattr(module, class_name, None)
        if instance_class is None:
            return kls
        # need check class
        if issubclass(cast(type, kls), instance_class):
            return kls
    except Exception:
        pass
    return None


def get_module_class_from_name(module_name: str, instance_class: Optional[Type[_T]] = None) -> Optional[Type[_T]]:
    """
    Return:
        kls (optional)

    Note:
        Does not reload. Does not raise any exception
    """
    module, _ = get_module_from_name(module_name)
    if module is None:
        return None
    return get_module_class_from_module(module, instance_class)
