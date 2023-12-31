# note that this file must be in the same folder with init_hooks.py

# general
LOCALE = 'zh-cn'
TOKEN = "abcdef:123456"
MASTER_ID = "123456789"

_all = [
    "LOCALE",
    "TOKEN",
    "MASTER_ID",
]

if "default" in __file__:
    __all__ = _all