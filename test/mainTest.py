import os
import sys
import unittest


class MainTest(unittest.TestCase):
    def test_main(self):
        pass
        # TODO

if __name__ == "__main__":
    sys.path.append(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    unittest.main()
