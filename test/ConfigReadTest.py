import os
import sys
import unittest


class ConfigReadTest(unittest.TestCase):
    def test_cfgread(self):
        from bot_framework.config import BotConfig
        from configparser import ConfigParser

        class TestSubConfigClass(BotConfig):
            def __init__(self) -> None:
                ...

            def parse(self, parser: ConfigParser) -> None:
                self.testfield = parser["test"]["testfield"]
                self.testintfield = parser.getint("test", "testintfield")
                self.testboolfield = parser.getboolean("test", "testboolfield")

        class testbot(object):
            def __init__(self) -> None:
                self.cfg = TestSubConfigClass()
                self.cfg.load("config.ini")

        bot = testbot()
        self.assertEqual(bot.cfg.admin_id, 123456789)
        self.assertEqual(bot.cfg.testintfield, 12345)


if __name__ == "__main__":
    sys.path.append(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    unittest.main()
