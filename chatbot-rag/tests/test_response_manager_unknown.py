import unittest

from src.response_manager import is_unknown_response


class TestUnknownResponse(unittest.TestCase):
    def setUp(self):
        self.patterns = [
            "i don't know",
            "i'm not sure",
            "sorry, i don't have proper answer",
            "not in the context",
        ]

    def test_empty_response(self):
        self.assertTrue(is_unknown_response("", self.patterns))

    def test_exact_pattern(self):
        resp = "I don't know the specifics of that policy."
        self.assertTrue(is_unknown_response(resp, self.patterns))

    def test_case_insensitive(self):
        resp = "SORRY, I DON'T HAVE PROPER ANSWER for that"
        self.assertTrue(is_unknown_response(resp, self.patterns))

    def test_not_unknown(self):
        resp = "Based on general Schengen visa information (not from site docs): Most short stays require travel insurance."
        self.assertFalse(is_unknown_response(resp, self.patterns))


if __name__ == "__main__":
    unittest.main()
