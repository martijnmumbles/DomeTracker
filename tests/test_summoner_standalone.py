import unittest
from unittest.mock import MagicMock, call

from summoner import Summoner


class TestSummonerEquality(unittest.TestCase):
    def test_equal_summoners(self):
        a = Summoner("GOLD", "IV", 50, "TestPlayer")
        b = Summoner("GOLD", "IV", 50, "OtherName")
        self.assertEqual(a, b)

    def test_different_tier(self):
        a = Summoner("GOLD", "IV", 50, "TestPlayer")
        b = Summoner("SILVER", "IV", 50, "TestPlayer")
        self.assertNotEqual(a, b)

    def test_different_rank(self):
        a = Summoner("GOLD", "IV", 50, "TestPlayer")
        b = Summoner("GOLD", "III", 50, "TestPlayer")
        self.assertNotEqual(a, b)

    def test_different_lp(self):
        a = Summoner("GOLD", "IV", 50, "TestPlayer")
        b = Summoner("GOLD", "IV", 60, "TestPlayer")
        self.assertNotEqual(a, b)

    def test_different_promo(self):
        a = Summoner("GOLD", "IV", 50, "TestPlayer", "WLN")
        b = Summoner("GOLD", "IV", 50, "TestPlayer", "")
        self.assertNotEqual(a, b)

    def test_case_insensitive_tier(self):
        a = Summoner("gold", "iv", 50, "TestPlayer")
        b = Summoner("GOLD", "IV", 50, "TestPlayer")
        self.assertEqual(a, b)

    def test_not_equal_to_non_summoner(self):
        a = Summoner("GOLD", "IV", 50, "TestPlayer")
        self.assertNotEqual(a, "not a summoner")


class TestSummonerOrdering(unittest.TestCase):
    def test_lower_tier(self):
        a = Summoner("SILVER", "IV", 50, "A")
        b = Summoner("GOLD", "IV", 50, "B")
        self.assertTrue(a < b)
        self.assertFalse(b < a)

    def test_lower_rank(self):
        a = Summoner("GOLD", "IV", 50, "A")
        b = Summoner("GOLD", "III", 50, "B")
        self.assertTrue(a < b)
        self.assertFalse(b < a)

    def test_lower_lp(self):
        a = Summoner("GOLD", "IV", 40, "A")
        b = Summoner("GOLD", "IV", 50, "B")
        self.assertTrue(a < b)
        self.assertFalse(b < a)

    def test_equal_not_less_than(self):
        a = Summoner("GOLD", "IV", 50, "A")
        b = Summoner("GOLD", "IV", 50, "B")
        self.assertFalse(a < b)

    def test_gt(self):
        a = Summoner("GOLD", "IV", 50, "A")
        b = Summoner("SILVER", "IV", 50, "B")
        self.assertTrue(a > b)

    def test_lt_non_summoner_raises(self):
        a = Summoner("GOLD", "IV", 50, "A")
        with self.assertRaises(Exception):
            a < "not a summoner"


class TestSummonerStr(unittest.TestCase):
    def test_str(self):
        s = Summoner("GOLD", "IV", 50, "TestPlayer", "WLN")
        self.assertEqual(str(s), "TestPlayer, GOLD, IV, 50, WLN")

    def test_str_no_promo(self):
        s = Summoner("GOLD", "IV", 50, "TestPlayer")
        self.assertEqual(str(s), "TestPlayer, GOLD, IV, 50, ")


class TestPromosLeft(unittest.TestCase):
    def test_all_remaining(self):
        s = Summoner("GOLD", "IV", 0, "T", "NNN")
        self.assertEqual(s.promos_left(), 3)

    def test_one_win(self):
        s = Summoner("GOLD", "IV", 0, "T", "WNN")
        self.assertEqual(s.promos_left(), 2)

    def test_win_then_loss(self):
        s = Summoner("GOLD", "IV", 0, "T", "WLN")
        self.assertEqual(s.promos_left(), 1)

    def test_all_done(self):
        s = Summoner("GOLD", "IV", 0, "T", "WLW")
        self.assertEqual(s.promos_left(), 0)


class TestLastPromo(unittest.TestCase):
    def test_last_win(self):
        s = Summoner("GOLD", "IV", 0, "T", "NNW")
        result = s.last_promo()
        self.assertIn("WON", result)

    def test_last_loss(self):
        s = Summoner("GOLD", "IV", 0, "T", "NNL")
        result = s.last_promo()
        self.assertIn("lost", result)


class TestStrPromo(unittest.TestCase):
    def test_no_wins(self):
        s = Summoner("GOLD", "IV", 0, "T", "NNN")
        self.assertEqual(s.str_promo(), "3 more win(s) needed!")

    def test_one_win(self):
        s = Summoner("GOLD", "IV", 0, "T", "WNN")
        self.assertEqual(s.str_promo(), "2 more win(s) needed!")

    def test_two_wins(self):
        s = Summoner("GOLD", "IV", 0, "T", "WWN")
        self.assertEqual(s.str_promo(), "1 more win(s) needed!")


class TestNoPromos(unittest.TestCase):
    def test_no_promos(self):
        values = [(0, 0, 0, 0, 0, "T", ""), (0, 0, 0, 0, 0, "T", "")]
        self.assertTrue(Summoner.no_promos(values))

    def test_has_promos(self):
        values = [(0, 0, 0, 0, 0, "T", "WLN"), (0, 0, 0, 0, 0, "T", "")]
        self.assertFalse(Summoner.no_promos(values))


class TestSaveToDb(unittest.TestCase):
    def test_save_calls_insert(self):
        db = MagicMock()
        s = Summoner("GOLD", "IV", 50, "TestPlayer", "WLN")
        s.save_to_db(db)
        db.insert.assert_called_once_with(
            "INSERT INTO lp_record (tier, rank, lp, name, promo) VALUES (%s, %s, %s, %s, %s)",
            ("GOLD", "IV", 50, "TestPlayer", "WLN"),
        )


class TestLastRecord(unittest.TestCase):
    def test_returns_summoner(self):
        db = MagicMock()
        db.query.return_value = [(50, "IV", "GOLD", 0, 0, "TestPlayer", "")]
        result = Summoner.last_record(db, "TestPlayer")
        self.assertIsInstance(result, Summoner)
        self.assertEqual(result.name, "TestPlayer")
        self.assertEqual(result.tier, "GOLD")
        self.assertEqual(result.rank, "IV")
        self.assertEqual(result.lp, 50)

    def test_returns_none_when_empty(self):
        db = MagicMock()
        db.query.return_value = []
        result = Summoner.last_record(db, "TestPlayer")
        self.assertIsNone(result)


class TestFiveAgo(unittest.TestCase):
    def test_returns_fifth_record(self):
        db = MagicMock()
        db.query.return_value = [
            (50, "IV", "GOLD", 0, 0, "T", ""),
            (45, "IV", "GOLD", 0, 0, "T", ""),
            (40, "IV", "GOLD", 0, 0, "T", ""),
            (35, "IV", "GOLD", 0, 0, "T", ""),
            (30, "IV", "GOLD", 0, 0, "T", ""),
        ]
        result = Summoner.five_ago(db, "T")
        self.assertIsInstance(result, Summoner)
        self.assertEqual(result.lp, 30)

    def test_returns_none_when_insufficient(self):
        db = MagicMock()
        db.query.return_value = [
            (50, "IV", "GOLD", 0, 0, "T", ""),
            (45, "IV", "GOLD", 0, 0, "T", ""),
        ]
        result = Summoner.five_ago(db, "T")
        self.assertIsNone(result)

    def test_returns_none_when_promos_present(self):
        db = MagicMock()
        db.query.return_value = [
            (50, "IV", "GOLD", 0, 0, "T", "WLN"),
            (45, "IV", "GOLD", 0, 0, "T", ""),
            (40, "IV", "GOLD", 0, 0, "T", ""),
            (35, "IV", "GOLD", 0, 0, "T", ""),
            (30, "IV", "GOLD", 0, 0, "T", ""),
        ]
        result = Summoner.five_ago(db, "T")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
