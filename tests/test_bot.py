import os
import unittest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DomeTracker.settings")

import django

django.setup()

from bot import YetAnotherBot


class TestCheckParam(unittest.TestCase):
    def test_single_arg(self):
        result = YetAnotherBot.check_param("hello")
        self.assertEqual(result, "hello")

    def test_multiple_args(self):
        result = YetAnotherBot.check_param("hello", "world")
        self.assertEqual(result, "hello world")

    def test_no_args_returns_none(self):
        result = YetAnotherBot.check_param(min_length=1, max_length=1)
        self.assertIsNone(result)

    def test_too_many_args(self):
        result = YetAnotherBot.check_param("a", "b", "c", min_length=1, max_length=2)
        self.assertIsNone(result)

    def test_exact_max_length(self):
        result = YetAnotherBot.check_param("a", "b", min_length=1, max_length=2)
        self.assertEqual(result, "a b")

    def test_numeric_args(self):
        result = YetAnotherBot.check_param(1, 2, 3)
        self.assertEqual(result, "1 2 3")


class TestSanitize(unittest.TestCase):
    def test_sanitizes_spaces(self):
        result = YetAnotherBot.sanitize("hello world")
        self.assertNotIn(" ", result)
        self.assertIn("hello", result)

    def test_sanitizes_special_chars(self):
        result = YetAnotherBot.sanitize("<script>alert('xss')</script>")
        self.assertNotIn("<", result)
        self.assertNotIn(">", result)

    def test_safe_string_unchanged(self):
        result = YetAnotherBot.sanitize("Thelmkon")
        self.assertEqual(result, "Thelmkon")

    def test_empty_string(self):
        result = YetAnotherBot.sanitize("")
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
