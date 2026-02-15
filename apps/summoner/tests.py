from django.test import TestCase
from unittest.mock import patch, MagicMock
from apps.summoner.models import Summoner
from apps.match.models import Match, RankedRecord, Promos, RiotAPIException, RiotEmptyResponseException
from apps.change.models import Change
from datetime import datetime, timezone, timedelta


class TestSummonerStr(TestCase):
    def test_str(self):
        s = Summoner(name="TestPlayer")
        self.assertEqual(str(s), "TestPlayer")


class TestSummonerToJson(TestCase):
    def test_to_json(self):
        s = Summoner(
            name="TestPlayer",
            report_hook="https://hook",
            summoner_id="sum123",
            account_id="acc123",
            puu_id="puu123",
        )
        result = s.to_json()
        self.assertEqual(result["name"], "TestPlayer")
        self.assertEqual(result["report_hook"], "https://hook")
        self.assertEqual(result["summoner_id"], "sum123")
        self.assertEqual(result["account_id"], "acc123")
        self.assertEqual(result["puu_id"], "puu123")


class TestSummonerGetWeekly(TestCase):
    def setUp(self):
        self.summoner = Summoner.objects.create(
            name="TestPlayer",
            summoner_id="sum123",
            account_id="acc123",
            puu_id="puu_weekly",
        )

    def test_no_matches_returns_none(self):
        result = self.summoner.get_weekly()
        self.assertIsNone(result)

    def test_with_recent_matches(self):
        now = datetime.now(timezone.utc)
        Match.objects.create(
            match_id="EUW1_W1",
            summoner=self.summoner,
            champion_name="Ahri",
            kills=10,
            deaths=2,
            assists=8,
            kda=9.0,
            start_time=now - timedelta(days=1),
            vision_score=30,
            epic_steals=1,
            win=True,
            first_blood_kill=True,
            first_blood_assist=False,
            first_tower_kill=True,
            first_tower_assist=False,
        )
        Match.objects.create(
            match_id="EUW1_W2",
            summoner=self.summoner,
            champion_name="Zed",
            kills=5,
            deaths=5,
            assists=3,
            kda=1.6,
            start_time=now - timedelta(days=2),
            vision_score=20,
            epic_steals=0,
            win=False,
            first_blood_kill=False,
            first_blood_assist=True,
            first_tower_kill=False,
            first_tower_assist=True,
        )

        result = self.summoner.get_weekly()
        self.assertIsNotNone(result)
        self.assertEqual(result["kills"], 15)
        self.assertEqual(result["deaths"], 7)
        self.assertEqual(result["assists"], 11)
        self.assertEqual(result["kda"], 9.0)  # max kda
        self.assertEqual(result["win"], 1)
        self.assertEqual(result["epic_steals"], 1)
        self.assertEqual(result["vision_score"], 25.0)  # avg
        self.assertEqual(result["first_blood_kill"], 1)
        self.assertEqual(result["first_blood_assist"], 1)
        self.assertEqual(result["first_tower_kill"], 1)
        self.assertEqual(result["first_tower_assist"], 1)


class TestSummonerRecentStats(TestCase):
    def setUp(self):
        self.summoner = Summoner.objects.create(
            name="TestPlayer",
            summoner_id="sum123",
            account_id="acc123",
            puu_id="puu_recent",
        )

    def test_no_matches(self):
        result = self.summoner.recent_stats()
        self.assertIn("No matches recorded", result)

    def test_with_matches(self):
        now = datetime.now(timezone.utc)
        for i in range(3):
            Match.objects.create(
                match_id=f"EUW1_R{i}",
                summoner=self.summoner,
                champion_name="Ahri",
                kills=5 + i,
                deaths=2 + i,
                assists=7,
                kda=3.0 + i,
                start_time=now - timedelta(hours=i),
                win=i % 2 == 0,
            )
        result = self.summoner.recent_stats()
        self.assertIn("Over the last 3 games", result)
        self.assertIn("TestPlayer", result)
        self.assertIn("kills", result)
        self.assertIn("deaths", result)
        self.assertIn("assists", result)
        self.assertIn("2 wins", result)


class TestSummonerGraph(TestCase):
    def setUp(self):
        self.summoner = Summoner.objects.create(
            name="TestPlayer",
            summoner_id="sum123",
            account_id="acc123",
            puu_id="puu_graph",
        )

    def test_no_matches(self):
        result = self.summoner.graph()
        self.assertIn("No ranked record", result)

    @patch("apps.summoner.models.plt")
    @patch("apps.summoner.models.DiscordWebhook")
    def test_with_matches(self, mock_webhook, mock_plt):
        now = datetime.now(timezone.utc)
        for i in range(3):
            m = Match.objects.create(
                match_id=f"EUW1_G{i}",
                summoner=self.summoner,
                champion_name="Ahri",
                kills=5,
                deaths=3,
                assists=7,
                kda=4.0,
                start_time=now - timedelta(hours=i),
                win=True,
            )
            RankedRecord.objects.create(
                tier=3, rank=2, lp=50 + i * 10,
                summoner=self.summoner, match=m,
            )

        result = self.summoner.graph(post=False)
        self.assertIn("LP graph", result)
        mock_plt.plot.assert_called_once()
        mock_plt.savefig.assert_called_once()
        mock_plt.clf.assert_called_once()

    @patch("apps.summoner.models.plt")
    @patch("apps.summoner.models.DiscordWebhook")
    def test_graph_posts_to_discord(self, mock_webhook, mock_plt):
        now = datetime.now(timezone.utc)
        for i in range(2):
            m = Match.objects.create(
                match_id=f"EUW1_GP{i}",
                summoner=self.summoner,
                champion_name="Ahri",
                start_time=now - timedelta(hours=i),
            )
            RankedRecord.objects.create(
                tier=3, rank=2, lp=50,
                summoner=self.summoner, match=m,
            )

        self.summoner.report_hook = "https://hook"
        self.summoner.save()
        self.summoner.graph(post=True)

        mock_webhook.post_image_to_discord.assert_called_once()


class TestSummonerReportMethods(TestCase):
    def setUp(self):
        self.summoner = Summoner.objects.create(
            name="TestPlayer",
            summoner_id="sum123",
            account_id="acc123",
            puu_id="puu_report",
            report_hook="https://hook",
        )

    @patch("apps.summoner.models.DiscordWebhook")
    @patch("apps.summoner.models.plt")
    def test_report_new_match_first_match(self, mock_plt, mock_webhook):
        now = datetime.now(timezone.utc)
        m = Match.objects.create(
            match_id="EUW1_FIRST",
            summoner=self.summoner,
            champion_name="Ahri",
            kills=5, deaths=3, assists=7, kda=4.0,
            start_time=now,
            win=True, vision_wards_bought=5, vision_score=30,
        )
        RankedRecord.objects.create(
            tier=3, rank=2, lp=50,
            summoner=self.summoner, match=m,
        )
        self.summoner.report_new_match_found()
        mock_webhook.post_to_discord.assert_called()
        first_call = mock_webhook.post_to_discord.call_args_list[0]
        self.assertIn("added", first_call[0][1])

    @patch("apps.summoner.models.DiscordWebhook")
    @patch("apps.summoner.models.plt")
    def test_report_new_match_no_hook(self, mock_plt, mock_webhook):
        self.summoner.report_hook = None
        self.summoner.save()
        self.summoner.report_new_match_found()
        mock_webhook.post_to_discord.assert_not_called()

    @patch("apps.summoner.models.DiscordWebhook")
    def test_report_ongoing_promos_new(self, mock_webhook):
        now = datetime.now(timezone.utc)
        m1 = Match.objects.create(
            match_id="EUW1_P1",
            summoner=self.summoner, champion_name="Ahri",
            start_time=now, win=True,
        )
        p = Promos.objects.create(target=3, wins=1, losses=0, progress="WNN")
        RankedRecord.objects.create(
            tier=3, rank=3, lp=100,
            summoner=self.summoner, match=m1, promo=p,
        )

        m2 = Match.objects.create(
            match_id="EUW1_P2",
            summoner=self.summoner, champion_name="Zed",
            start_time=now - timedelta(hours=1), win=True,
        )
        RankedRecord.objects.create(
            tier=3, rank=3, lp=100,
            summoner=self.summoner, match=m2,
        )

        matches = self.summoner.match_set.order_by("-start_time")[:10]
        self.summoner.report_ongoing_promos(matches)
        mock_webhook.post_to_discord.assert_called_once()
        self.assertIn("Starting promos", mock_webhook.post_to_discord.call_args[0][1])

    @patch("apps.summoner.models.DiscordWebhook")
    def test_report_regular_match(self, mock_webhook):
        now = datetime.now(timezone.utc)
        for i in range(2):
            m = Match.objects.create(
                match_id=f"EUW1_REG{i}",
                summoner=self.summoner, champion_name="Ahri",
                start_time=now - timedelta(hours=i),
                win=i == 0,
            )
            RankedRecord.objects.create(
                tier=3, rank=2, lp=60 - i * 20,
                summoner=self.summoner, match=m,
            )

        matches = self.summoner.match_set.order_by("-start_time")[:10]
        self.summoner.report_regular_match(matches)
        mock_webhook.post_to_discord.assert_called()
        first_call = mock_webhook.post_to_discord.call_args_list[0]
        self.assertIn("Gained", first_call[0][1])


class TestSummonerPoll(TestCase):
    def setUp(self):
        self.summoner = Summoner.objects.create(
            name="TestPlayer",
            summoner_id="sum123",
            account_id="acc123",
            puu_id="puu_poll",
        )

    @patch("apps.summoner.models.call_api")
    def test_poll_no_new_matches(self, mock_call_api):
        now = datetime.now(timezone.utc)
        Match.objects.create(
            match_id="EUW1_EXISTING",
            summoner=self.summoner,
            champion_name="Ahri",
            start_time=now,
        )

        update_resp = MagicMock()
        update_resp.status_code = 200
        update_resp.json.return_value = {
            "name": "TestPlayer", "id": "sum123", "accountId": "acc123",
        }

        matches_resp = MagicMock()
        matches_resp.status_code = 200
        matches_resp.json.return_value = ["EUW1_EXISTING"]

        rank_resp = MagicMock()
        rank_resp.status_code = 200
        rank_resp.json.return_value = [{"queueType": "RANKED_SOLO_5x5", "tier": "GOLD", "rank": "II", "leaguePoints": 50}]

        mock_call_api.side_effect = [update_resp, matches_resp, rank_resp]

        self.summoner.poll()
        # No new match created
        self.assertEqual(Match.objects.filter(summoner=self.summoner).count(), 1)

    @patch("apps.summoner.models.call_api")
    def test_poll_api_error_raises(self, mock_call_api):
        update_resp = MagicMock()
        update_resp.status_code = 200
        update_resp.json.return_value = {
            "name": "TestPlayer", "id": "sum123", "accountId": "acc123",
        }

        matches_resp = MagicMock()
        matches_resp.status_code = 500
        matches_resp.json.return_value = {"status": {"message": "Server error"}}

        mock_call_api.side_effect = [update_resp, matches_resp]

        with self.assertRaises(RiotAPIException):
            self.summoner.poll()


class TestSummonerCreateSummoner(TestCase):
    @patch("apps.summoner.models.Match.find_last_ranked")
    @patch("apps.summoner.models.Match.create_match")
    @patch("apps.summoner.models.RankedRecord.create_record")
    @patch("apps.summoner.models.call_api")
    def test_creates_summoner(self, mock_call_api, mock_create_record, mock_create_match, mock_find_last):
        sum_resp = MagicMock()
        sum_resp.status_code = 200
        sum_resp.json.return_value = {
            "name": "NewPlayer",
            "id": "sum_new",
            "accountId": "acc_new",
            "puuid": "puu_new",
        }

        rank_resp = MagicMock()
        rank_resp.status_code = 200
        rank_resp.json.return_value = [
            {"queueType": "RANKED_SOLO_5x5", "tier": "GOLD", "rank": "II", "leaguePoints": 50}
        ]

        mock_call_api.side_effect = [sum_resp, rank_resp]
        mock_find_last.return_value = "EUW1_LAST"
        mock_match = MagicMock()
        mock_create_match.return_value = mock_match

        result = Summoner.create_summoner("NewPlayer")

        self.assertEqual(result.name, "NewPlayer")
        self.assertEqual(result.puu_id, "puu_new")
        mock_find_last.assert_called_once()
        mock_create_match.assert_called_once()

    @patch("apps.summoner.models.call_api")
    def test_create_summoner_api_error_raises(self, mock_call_api):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"status": {"message": "Not found"}}
        mock_call_api.return_value = mock_resp

        with self.assertRaises(RiotAPIException):
            Summoner.create_summoner("NonExistent")


class TestSummonerOnUpdate(TestCase):
    def test_on_update_creates_change(self):
        summoner = Summoner.objects.create(
            name="TestPlayer",
            summoner_id="sum123",
            account_id="acc123",
            puu_id="puu_signal",
        )
        # The post_save signal should have created a Change
        changes = Change.objects.filter(object_id=summoner.pk)
        self.assertTrue(changes.exists())

    def test_on_update_records_changes(self):
        summoner = Summoner.objects.create(
            name="OriginalName",
            summoner_id="sum123",
            account_id="acc123",
            puu_id="puu_change",
        )
        initial_count = Change.objects.count()

        summoner.name = "NewName"
        summoner.save()

        self.assertEqual(Change.objects.count(), initial_count + 1)
        latest_change = Change.objects.last()
        self.assertIn("name", latest_change.new_object)
