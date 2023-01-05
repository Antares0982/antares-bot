import os
import sys
import unittest


class LocaleTest(unittest.TestCase):
    def test_locale(self):
        from bot_framework.locale.general import locale
        # default import zh_CN
        chinese = locale.button_invalid
        self.assertIn("按钮", chinese)

        import bot_framework.locale.en_US as EN_US
        english = locale.button_invalid
        self.assertIn("button", english)

        import bot_framework.locale.zh_CN as ZH_CN
        # import does not take effect here
        self.assertEqual(locale.button_invalid, english)

        locale.setCurrentLocale(ZH_CN)
        self.assertEqual(locale.button_invalid, chinese)

        locale.setCurrentLocale(EN_US)
        self.assertEqual(locale.button_invalid, english)


if __name__ == "__main__":
    sys.path.append(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    unittest.main()
