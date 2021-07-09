from configparser import ConfigParser
from typing import List, Tuple

__all__ = [
    "token",
    "proxy",
    "proxy_url",
    "MYID",
    "blacklistdatabase"
]

cfgparser = ConfigParser()
cfgparser.read("config.ini")

# basic
token = cfgparser["settings"]["token"]
proxy = cfgparser.getboolean("settings", "proxy")
proxy_url = cfgparser["settings"]["proxy_url"]
MYID = cfgparser.getint("settings", "myid")
blacklistdatabase = cfgparser["settings"]["blacklistdatabase"]

del cfgparser
