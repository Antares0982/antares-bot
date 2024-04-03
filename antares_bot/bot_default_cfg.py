# note that this file must be in the same folder with init_hooks.py

# general
LOCALE = 'zh-cn'
TOKEN = "abcdef:123456"
MASTER_ID = "123456789"
DEFAULT_DATA_DIR = "data"

_all = [
    "LOCALE",
    "TOKEN",
    "MASTER_ID",
    "DEFAULT_DATA_DIR",
]

if "default" in __file__:
    __all__ = _all
