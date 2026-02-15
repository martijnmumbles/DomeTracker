import unittest
from unittest.mock import MagicMock

from league import tier_to_int, rank_to_int, absolute_value, trend


def _summoner(tier="GOLD", rank="IV", lp=50):
    s = MagicMock()
    s.tier = tier
    s.rank = rank
    s.lp = lp
    return s


class TestTierToInt(unittest.TestCase):
    def test_iron(self):
        self.assertEqual(tier_to_int(_summoner(tier="IRON")), 0)

    def test_bronze(self):
        self.assertEqual(tier_to_int(_summoner(tier="BRONZE")), 1)

    def test_silver(self):
        self.assertEqual(tier_to_int(_summoner(tier="SILVER")), 2)

    def test_gold(self):
        self.assertEqual(tier_to_int(_summoner(tier="GOLD")), 3)

    def test_platinum(self):
        self.assertEqual(tier_to_int(_summoner(tier="PLATINUM")), 4)

    def test_diamond(self):
        self.assertEqual(tier_to_int(_summoner(tier="DIAMOND")), 5)

    def test_master(self):
        self.assertEqual(tier_to_int(_summoner(tier="MASTER")), 6)

    def test_grandmaster(self):
        self.assertEqual(tier_to_int(_summoner(tier="GRANDMASTER")), 7)

    def test_challenger(self):
        self.assertEqual(tier_to_int(_summoner(tier="CHALLENGER")), 8)

    def test_case_insensitive(self):
        self.assertEqual(tier_to_int(_summoner(tier="gold")), 3)
        self.assertEqual(tier_to_int(_summoner(tier="Gold")), 3)


class TestRankToInt(unittest.TestCase):
    def test_iv(self):
        self.assertEqual(rank_to_int(_summoner(rank="IV")), 0)

    def test_iii(self):
        self.assertEqual(rank_to_int(_summoner(rank="III")), 1)

    def test_ii(self):
        self.assertEqual(rank_to_int(_summoner(rank="II")), 2)

    def test_i(self):
        self.assertEqual(rank_to_int(_summoner(rank="I")), 3)

    def test_case_insensitive(self):
        self.assertEqual(rank_to_int(_summoner(rank="iv")), 0)


class TestAbsoluteValue(unittest.TestCase):
    def test_iron_iv_0(self):
        self.assertEqual(absolute_value(_summoner("IRON", "IV", 0)), 0)

    def test_gold_iv_50(self):
        # tier=3*400=1200, rank=0*100=0, lp=50 => 1250
        self.assertEqual(absolute_value(_summoner("GOLD", "IV", 50)), 1250)

    def test_gold_i_75(self):
        # tier=3*400=1200, rank=3*100=300, lp=75 => 1575
        self.assertEqual(absolute_value(_summoner("GOLD", "I", 75)), 1575)

    def test_challenger_i_500(self):
        # tier=8*400=3200, rank=3*100=300, lp=500 => 4000
        self.assertEqual(absolute_value(_summoner("CHALLENGER", "I", 500)), 4000)


class TestTrend(unittest.TestCase):
    def test_positive_trend_near_promotion(self):
        current = _summoner("GOLD", "IV", 90)
        old = _summoner("GOLD", "IV", 40)
        result = trend(current, old)
        self.assertIn("+10", result)
        self.assertIn("promotion", result)

    def test_negative_trend_near_demotion(self):
        current = _summoner("GOLD", "IV", 10)
        old = _summoner("GOLD", "IV", 60)
        result = trend(current, old)
        self.assertIn("-10", result)
        self.assertIn("demotion", result)

    def test_stable_trend(self):
        current = _summoner("GOLD", "II", 50)
        old = _summoner("GOLD", "II", 50)
        result = trend(current, old)
        self.assertIn("stabilizing", result)

    def test_positive_trend_not_near_promotion(self):
        current = _summoner("GOLD", "IV", 55)
        old = _summoner("GOLD", "IV", 50)
        result = trend(current, old)
        self.assertIn("+1", result)
        self.assertIn("stabilizing", result)

    def test_negative_trend_not_near_demotion(self):
        current = _summoner("GOLD", "IV", 50)
        old = _summoner("GOLD", "IV", 55)
        result = trend(current, old)
        self.assertIn("-1", result)
        self.assertIn("stabilizing", result)


if __name__ == "__main__":
    unittest.main()
