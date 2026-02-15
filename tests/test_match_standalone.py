import unittest
from unittest.mock import patch, MagicMock

from match import Match


class TestGetLatestMatchId(unittest.TestCase):
    @patch("match.requests.get")
    def test_returns_first_match_id(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = ["EUW1_111", "EUW1_222"]
        mock_get.return_value = mock_resp

        conf = MagicMock()
        conf.X_Riot_Token = "test-token"
        result = Match.get_latest_match_id("test-puuid", conf)

        self.assertEqual(result, "EUW1_111")
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertIn("test-puuid", call_args[0][0])
        self.assertEqual(call_args[1]["headers"]["X-Riot-Token"], "test-token")


class TestGetMatch(unittest.TestCase):
    @patch("match.requests.get")
    def test_returns_match_data(self, mock_get):
        match_data = {"info": {"participants": []}}
        mock_resp = MagicMock()
        mock_resp.json.return_value = match_data
        mock_get.return_value = mock_resp

        conf = MagicMock()
        conf.X_Riot_Token = "test-token"
        result = Match.get_match("EUW1_111", conf)

        self.assertEqual(result, match_data)


class TestGetParticipant(unittest.TestCase):
    @patch("match.requests.get")
    def test_returns_correct_participant(self, mock_get):
        match_data = {
            "info": {
                "participants": [
                    {"summonerName": "Alice", "kills": 5},
                    {"summonerName": "Bob", "kills": 10},
                ]
            }
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = match_data
        mock_get.return_value = mock_resp

        conf = MagicMock()
        conf.X_Riot_Token = "test-token"
        result = Match.get_participant("Bob", "EUW1_111", conf)

        self.assertEqual(result["kills"], 10)
        self.assertEqual(result["summonerName"], "Bob")


class TestGetNotableEvents(unittest.TestCase):
    def _mock_participant(self, mock_get, overrides=None):
        participant = {
            "summonerName": "TestPlayer",
            "championName": "Ahri",
            "pentaKills": 0,
            "quadraKills": 0,
            "tripleKills": 0,
            "epicMonsterSteals": 0,
        }
        if overrides:
            participant.update(overrides)
        match_data = {"info": {"participants": [participant]}}
        mock_resp = MagicMock()
        mock_resp.json.return_value = match_data
        mock_get.return_value = mock_resp

    @patch("match.requests.get")
    def test_penta_kill(self, mock_get):
        self._mock_participant(mock_get, {"pentaKills": 1})
        conf = MagicMock()
        conf.X_Riot_Token = "t"
        result = Match.get_notable_events("TestPlayer", "EUW1_111", conf)
        self.assertIn("PENTAKILL", result)
        self.assertIn("TESTPLAYER", result)

    @patch("match.requests.get")
    def test_quadra_kill(self, mock_get):
        self._mock_participant(mock_get, {"quadraKills": 1})
        conf = MagicMock()
        conf.X_Riot_Token = "t"
        result = Match.get_notable_events("TestPlayer", "EUW1_111", conf)
        self.assertIn("QUADRA", result)

    @patch("match.requests.get")
    def test_triple_kill(self, mock_get):
        self._mock_participant(mock_get, {"tripleKills": 1})
        conf = MagicMock()
        conf.X_Riot_Token = "t"
        result = Match.get_notable_events("TestPlayer", "EUW1_111", conf)
        self.assertIn("Triple", result)

    @patch("match.requests.get")
    def test_epic_monster_steal(self, mock_get):
        self._mock_participant(mock_get, {"epicMonsterSteals": 1})
        conf = MagicMock()
        conf.X_Riot_Token = "t"
        result = Match.get_notable_events("TestPlayer", "EUW1_111", conf)
        self.assertIn("thief", result)

    @patch("match.requests.get")
    def test_no_notable_events(self, mock_get):
        self._mock_participant(mock_get)
        conf = MagicMock()
        conf.X_Riot_Token = "t"
        result = Match.get_notable_events("TestPlayer", "EUW1_111", conf)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
