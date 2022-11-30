import os
import sys
import unittest


class LocaleTest(unittest.TestCase):
    def test_locale(self):
        from bot_framework.locale.en_US import Locale

        print(Locale.locale.button_invalid)

        from bot_framework.locale.zh_CN import ZH_CN

        ZH_CN.setCurrentLocale()
        print(dir(Locale))
        print(Locale.button_invalid)


if __name__ == "__main__":
    sys.path.append(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    unittest.main()
