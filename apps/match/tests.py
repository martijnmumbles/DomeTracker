from django.test import TestCase
from unittest.mock import patch, MagicMock
from apps.match.models import Match, Promos, RankedRecord
from apps.summoner.models import Summoner
from datetime import datetime, timezone
import json
import os


class TestPromos(TestCase):
    def test_eq_same(self):
        a = Promos(target=3, wins=1, losses=1, progress="WLN")
        b = Promos(target=3, wins=1, losses=1, progress="WLN")
        self.assertEqual(a, b)

    def test_eq_different_target(self):
        a = Promos(target=3, wins=1, losses=1, progress="WLN")
        b = Promos(target=2, wins=1, losses=1, progress="WLN")
        self.assertNotEqual(a, b)

    def test_eq_different_wins(self):
        a = Promos(target=3, wins=1, losses=1, progress="WLN")
        b = Promos(target=3, wins=2, losses=1, progress="WLN")
        self.assertNotEqual(a, b)

    def test_eq_non_promos(self):
        a = Promos(target=3, wins=1, losses=1, progress="WLN")
        self.assertNotEqual(a, "not promos")

    def test_lt_fewer_wins(self):
        a = Promos(target=3, wins=0, losses=1, progress="LNN")
        b = Promos(target=3, wins=1, losses=0, progress="WNN")
        self.assertTrue(a < b)

    def test_lt_more_losses(self):
        a = Promos(target=3, wins=1, losses=2, progress="WLL")
        b = Promos(target=3, wins=1, losses=1, progress="WLN")
        self.assertTrue(a < b)

    def test_lt_equal(self):
        a = Promos(target=3, wins=1, losses=1, progress="WLN")
        b = Promos(target=3, wins=1, losses=1, progress="WLN")
        self.assertFalse(a < b)

    def test_lt_non_promos_raises(self):
        a = Promos(target=3, wins=1, losses=1, progress="WLN")
        with self.assertRaises(Exception):
            a < "not promos"

    def test_str(self):
        p = Promos(target=3, wins=1, losses=1, progress="WLN")
        result = str(p)
        self.assertIn("1 wins", result)
        self.assertIn("3 needed", result)
        self.assertIn("3 matches left", result)


class TestRankedRecordConversions(TestCase):
    def test_tier_to_int_all_tiers(self):
        tiers = [
            ("IRON", 0), ("BRONZE", 1), ("SILVER", 2), ("GOLD", 3),
            ("PLATINUM", 4), ("EMERALD", 5), ("DIAMOND", 6), ("MASTER", 7),
            ("GRANDMASTER", 8), ("CHALLENGER", 9),
        ]
        for tier, expected in tiers:
            self.assertEqual(RankedRecord.tier_to_int(tier), expected, f"Failed for {tier}")

    def test_tier_to_int_case_insensitive(self):
        self.assertEqual(RankedRecord.tier_to_int("gold"), 3)
        self.assertEqual(RankedRecord.tier_to_int("Gold"), 3)

    def test_int_to_tier_all(self):
        tiers = [
            (0, "IRON"), (1, "BRONZE"), (2, "SILVER"), (3, "GOLD"),
            (4, "PLATINUM"), (5, "EMERALD"), (6, "DIAMOND"), (7, "MASTER"),
            (8, "GRANDMASTER"), (9, "CHALLENGER"),
        ]
        for val, expected in tiers:
            self.assertEqual(RankedRecord.int_to_tier(val), expected, f"Failed for {val}")

    def test_rank_to_int_all(self):
        ranks = [("IV", 0), ("III", 1), ("II", 2), ("I", 3)]
        for rank, expected in ranks:
            self.assertEqual(RankedRecord.rank_to_int(rank), expected, f"Failed for {rank}")

    def test_rank_to_int_case_insensitive(self):
        self.assertEqual(RankedRecord.rank_to_int("iv"), 0)

    def test_int_to_rank_all(self):
        ranks = [(0, "IV"), (1, "III"), (2, "II"), (3, "I")]
        for val, expected in ranks:
            self.assertEqual(RankedRecord.int_to_rank(val), expected, f"Failed for {val}")


class TestRankedRecordAbsoluteValue(TestCase):
    def test_below_master(self):
        # tier=3 (GOLD), rank=2 (II), lp=50 => 3*400 + 2*100 + 50 = 1450
        r = RankedRecord(tier=3, rank=2, lp=50)
        self.assertEqual(r.absolute_value(), 1450)

    def test_iron_iv_zero(self):
        r = RankedRecord(tier=0, rank=0, lp=0)
        self.assertEqual(r.absolute_value(), 0)

    def test_above_master(self):
        # tier=7 (MASTER) => 7*400 + lp = 2800 + 150 = 2950
        r = RankedRecord(tier=7, rank=0, lp=150)
        self.assertEqual(r.absolute_value(), 2950)

    def test_emerald_boundary(self):
        # tier=5 (EMERALD), rank=3 (I), lp=99 => 5*400 + 3*100 + 99 = 2399
        r = RankedRecord(tier=5, rank=3, lp=99)
        self.assertEqual(r.absolute_value(), 2399)

    def test_master_ignores_rank(self):
        # tier=7 (MASTER), rank=1 should still just be tier*400 + lp
        r = RankedRecord(tier=7, rank=1, lp=200)
        self.assertEqual(r.absolute_value(), 3000)


class TestRankedRecordTrend(TestCase):
    def test_positive_trend_near_promotion(self):
        current = RankedRecord(tier=3, rank=2, lp=90)
        old = RankedRecord(tier=3, rank=2, lp=50)
        result = RankedRecord.trend(current, old)
        self.assertIn("+10", result)
        self.assertIn("promotion", result)

    def test_negative_trend_near_demotion(self):
        current = RankedRecord(tier=3, rank=2, lp=8)
        old = RankedRecord(tier=3, rank=2, lp=48)
        result = RankedRecord.trend(current, old)
        self.assertIn("-10", result)
        self.assertIn("demotion", result)

    def test_stable(self):
        current = RankedRecord(tier=3, rank=2, lp=50)
        old = RankedRecord(tier=3, rank=2, lp=50)
        result = RankedRecord.trend(current, old)
        self.assertIn("Netting 0", result)
        self.assertNotIn("promotion", result)
        self.assertNotIn("demotion", result)


class TestRankedRecordEquality(TestCase):
    def test_equal(self):
        a = RankedRecord(tier=3, rank=2, lp=50)
        b = RankedRecord(tier=3, rank=2, lp=50)
        self.assertEqual(a, b)

    def test_not_equal_tier(self):
        a = RankedRecord(tier=3, rank=2, lp=50)
        b = RankedRecord(tier=4, rank=2, lp=50)
        self.assertNotEqual(a, b)

    def test_not_equal_non_record(self):
        a = RankedRecord(tier=3, rank=2, lp=50)
        self.assertNotEqual(a, "not a record")


class TestRankedRecordLt(TestCase):
    def test_lower_tier(self):
        a = RankedRecord(tier=2, rank=2, lp=50)
        b = RankedRecord(tier=3, rank=2, lp=50)
        self.assertTrue(a < b)

    def test_lower_rank(self):
        a = RankedRecord(tier=3, rank=1, lp=50)
        b = RankedRecord(tier=3, rank=2, lp=50)
        self.assertTrue(a < b)

    def test_lower_lp(self):
        a = RankedRecord(tier=3, rank=2, lp=40)
        b = RankedRecord(tier=3, rank=2, lp=50)
        self.assertTrue(a < b)

    def test_equal_not_lt(self):
        a = RankedRecord(tier=3, rank=2, lp=50)
        b = RankedRecord(tier=3, rank=2, lp=50)
        self.assertFalse(a < b)

    def test_non_record_raises(self):
        a = RankedRecord(tier=3, rank=2, lp=50)
        with self.assertRaises(Exception):
            a < "not a record"


class TestRankedRecordStr(TestCase):
    def test_str_no_promo(self):
        r = RankedRecord(tier=3, rank=2, lp=50)
        r.promo = None
        result = str(r)
        self.assertEqual(result, "GOLD II 50 LP.")

    def test_str_with_promo(self):
        p = Promos(target=3, wins=1, losses=1, progress="WLN")
        r = RankedRecord(tier=3, rank=2, lp=50)
        r.promo = p
        result = str(r)
        self.assertIn("GOLD II 50 LP.", result)
        self.assertIn("1 wins", result)


class TestRankedRecordCreateRecord(TestCase):
    def setUp(self):
        self.summoner = Summoner.objects.create(
            name="TestPlayer",
            summoner_id="sum123",
            account_id="acc123",
            puu_id="puu123",
        )
        self.match = Match.objects.create(
            match_id="EUW1_111",
            summoner=self.summoner,
            champion_name="Ahri",
            start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

    def test_create_record_without_promos(self):
        ranked_data = {
            "tier": "GOLD",
            "rank": "II",
            "leaguePoints": 50,
        }
        RankedRecord.create_record(self.summoner, self.match, ranked_data)

        record = RankedRecord.objects.get(match=self.match)
        self.assertEqual(record.tier, 3)
        self.assertEqual(record.rank, 2)
        self.assertEqual(record.lp, 50)
        self.assertIsNone(record.promo)

    def test_create_record_with_promos(self):
        ranked_data = {
            "tier": "GOLD",
            "rank": "I",
            "leaguePoints": 100,
            "miniSeries": {
                "target": 3,
                "wins": 1,
                "losses": 0,
                "progress": "WNN",
            },
        }
        RankedRecord.create_record(self.summoner, self.match, ranked_data)

        record = RankedRecord.objects.get(match=self.match)
        self.assertEqual(record.tier, 3)
        self.assertEqual(record.rank, 3)
        self.assertIsNotNone(record.promo)
        self.assertEqual(record.promo.target, 3)
        self.assertEqual(record.promo.wins, 1)


class TestMatchEvents(TestCase):
    def setUp(self):
        self.summoner = Summoner.objects.create(
            name="TestPlayer",
            summoner_id="sum123",
            account_id="acc123",
            puu_id="puu123_events",
            bully_opt_in=False,
        )

    def _create_match(self, **kwargs):
        defaults = {
            "match_id": "EUW1_111",
            "summoner": self.summoner,
            "champion_name": "Ahri",
            "penta_kills": 0,
            "quadra_kills": 0,
            "triple_kills": 0,
            "epic_steals": 0,
            "kills": 5,
            "deaths": 3,
            "assists": 7,
            "kda": 4.0,
            "start_time": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "duration": 1800,
            "win": True,
            "vision_wards_bought": 5,
            "wards_placed": 10,
            "vision_score": 30,
            "longest_time_spent_living": 600,
            "first_blood_kill": False,
            "first_blood_assist": False,
            "first_tower_kill": False,
            "first_tower_assist": False,
        }
        defaults.update(kwargs)
        return Match.objects.create(**defaults)

    def test_base_event(self):
        match = self._create_match()
        events = match.events()
        self.assertEqual(len(events), 1)
        self.assertIn("5/3/7", events[0])
        self.assertIn("4.0 kda", events[0])

    def test_penta_kill(self):
        match = self._create_match(penta_kills=1)
        events = match.events()
        penta_events = [e for e in events if "PENTAKILL" in e]
        self.assertEqual(len(penta_events), 1)

    def test_quadra_kill(self):
        match = self._create_match(quadra_kills=1)
        events = match.events()
        quadra_events = [e for e in events if "QUADRA" in e]
        self.assertEqual(len(quadra_events), 1)

    def test_triple_kill(self):
        match = self._create_match(triple_kills=1)
        events = match.events()
        triple_events = [e for e in events if "Triple" in e]
        self.assertEqual(len(triple_events), 1)

    def test_penta_takes_priority_over_quadra(self):
        match = self._create_match(penta_kills=1, quadra_kills=2)
        events = match.events()
        self.assertTrue(any("PENTAKILL" in e for e in events))
        self.assertFalse(any("QUADRA" in e for e in events))

    def test_first_blood(self):
        match = self._create_match(first_blood_kill=True)
        events = match.events()
        self.assertTrue(any("first blood" in e for e in events))

    def test_epic_steal(self):
        match = self._create_match(epic_steals=1)
        events = match.events()
        self.assertTrue(any("thief" in e for e in events))

    def test_long_game(self):
        match = self._create_match(duration=3500)
        events = match.events()
        self.assertTrue(any("minute game" in e for e in events))

    def test_bully_vision_wards_zero(self):
        self.summoner.bully_opt_in = True
        self.summoner.save()
        match = self._create_match(vision_wards_bought=0)
        events = match.events()
        self.assertTrue(any("vision ward" in e for e in events))

    def test_bully_vision_wards_one(self):
        self.summoner.bully_opt_in = True
        self.summoner.save()
        match = self._create_match(vision_wards_bought=1)
        events = match.events()
        self.assertTrue(any("single" in e.lower() for e in events))

    @patch("apps.match.models.generate_meme")
    def test_bully_low_vision_score_meme_success(self, mock_meme):
        mock_meme.return_value = {
            "success": True,
            "data": {"url": "https://imgflip.com/meme/123"},
        }
        self.summoner.bully_opt_in = True
        self.summoner.save()
        match = self._create_match(vision_score=5, vision_wards_bought=5)
        events = match.events()
        self.assertTrue(any("imgflip" in e for e in events))

    @patch("apps.match.models.generate_meme")
    def test_bully_low_vision_score_meme_failure(self, mock_meme):
        mock_meme.return_value = {"success": False}
        self.summoner.bully_opt_in = True
        self.summoner.save()
        match = self._create_match(vision_score=5, vision_wards_bought=5)
        events = match.events()
        self.assertTrue(any("API ERROR" in e for e in events))


class TestMatchStr(TestCase):
    def test_str(self):
        summoner = Summoner.objects.create(
            name="TestPlayer",
            summoner_id="sum123",
            account_id="acc123",
            puu_id="puu_str_test",
        )
        match = Match.objects.create(
            match_id="EUW1_111",
            summoner=summoner,
            champion_name="Ahri",
            start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(str(match), "Match EUW1_111 for TestPlayer")


class TestMatchWriteRead(TestCase):
    def test_write_and_read(self):
        match_data = {"info": {"participants": [{"kills": 5}]}}
        Match.write("TEST_MATCH_001", match_data)

        result = Match.read("TEST_MATCH_001")
        self.assertEqual(result, match_data)

        # Clean up
        path = f"{os.getcwd()}/matches/TEST_MATCH_001.json"
        if os.path.exists(path):
            os.remove(path)


class TestMatchCreateMatch(TestCase):
    @patch("apps.match.models.call_api")
    def test_creates_match(self, mock_call_api):
        summoner = Summoner.objects.create(
            name="TestPlayer",
            summoner_id="sum123",
            account_id="acc123",
            puu_id="puu_create_test",
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "info": {
                "queueId": 420,
                "gameStartTimestamp": 1704067200000,
                "gameDuration": 1800,
                "participants": [
                    {
                        "puuid": "puu_create_test",
                        "championName": "Ahri",
                        "pentaKills": 0,
                        "quadraKills": 0,
                        "tripleKills": 0,
                        "kills": 5,
                        "deaths": 3,
                        "assists": 7,
                        "win": True,
                        "visionWardsBoughtInGame": 2,
                        "wardsPlaced": 10,
                        "visionScore": 30,
                        "longestTimeSpentLiving": 600,
                        "firstBloodKill": False,
                        "firstBloodAssist": False,
                        "firstTowerKill": False,
                        "firstTowerAssist": False,
                        "challenges": {
                            "epicMonsterSteals": 0,
                            "kda": 4.0,
                        },
                    }
                ],
            }
        }
        mock_call_api.return_value = mock_resp

        with patch.object(Match, "write"):
            match = Match.create_match("EUW1_CREATE", summoner)

        self.assertIsNotNone(match)
        self.assertEqual(match.match_id, "EUW1_CREATE")
        self.assertEqual(match.champion_name, "Ahri")
        self.assertEqual(match.kills, 5)
        self.assertTrue(match.win)

    @patch("apps.match.models.call_api")
    def test_create_match_non_200_raises(self, mock_call_api):
        summoner = Summoner.objects.create(
            name="TestPlayer",
            summoner_id="sum123",
            account_id="acc123",
            puu_id="puu_create_err",
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"status": {"message": "Not found"}}
        mock_call_api.return_value = mock_resp

        from apps.match.models import RiotAPIException

        with self.assertRaises(RiotAPIException):
            Match.create_match("EUW1_ERR", summoner)


class TestMatchFindLastRanked(TestCase):
    @patch("apps.match.models.call_api")
    def test_finds_last_ranked(self, mock_call_api):
        summoner = Summoner.objects.create(
            name="TestPlayer",
            summoner_id="sum123",
            account_id="acc123",
            puu_id="puu_find_test",
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = ["EUW1_LAST"]
        mock_call_api.return_value = mock_resp

        result = Match.find_last_ranked(summoner)
        self.assertEqual(result, "EUW1_LAST")

    @patch("apps.match.models.call_api")
    def test_find_last_ranked_error_raises(self, mock_call_api):
        summoner = Summoner.objects.create(
            name="TestPlayer",
            summoner_id="sum123",
            account_id="acc123",
            puu_id="puu_find_err",
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"status": {"message": "Not found"}}
        mock_call_api.return_value = mock_resp

        from apps.match.models import RiotAPIException

        with self.assertRaises(RiotAPIException):
            Match.find_last_ranked(summoner)
