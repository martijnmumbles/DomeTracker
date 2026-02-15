import unittest
import json
from unittest.mock import patch, mock_open
from datetime import datetime

from config import Config


SAMPLE_CONFIG = {
    "DISCORD_TOKEN": "test-token",
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "DB_NAME": "testdb",
    "DB_USERNAME": "user",
    "DB_PW": "pass",
    "X_Riot_Token": "riot-token",
    "DISCORD_ERROR_HOOK": "https://error.hook",
    "DISCORD_REPORT_HOOK": "https://report.hook",
    "LAST_RUN": "2024-01-15 12:30:45.123456",
}


class TestConfigInit(unittest.TestCase):
    @patch("builtins.open", mock_open(read_data=json.dumps(SAMPLE_CONFIG)))
    def test_loads_all_fields(self):
        config = Config()
        self.assertEqual(config.DISCORD_TOKEN, "test-token")
        self.assertEqual(config.DB_HOST, "localhost")
        self.assertEqual(config.DB_PORT, "5432")
        self.assertEqual(config.DB_NAME, "testdb")
        self.assertEqual(config.DB_USERNAME, "user")
        self.assertEqual(config.DB_PW, "pass")
        self.assertEqual(config.X_Riot_Token, "riot-token")
        self.assertEqual(config.DISCORD_ERROR_HOOK, "https://error.hook")
        self.assertEqual(config.DISCORD_REPORT_HOOK, "https://report.hook")

    @patch("builtins.open", mock_open(read_data=json.dumps(SAMPLE_CONFIG)))
    def test_parses_last_run(self):
        config = Config()
        self.assertIsInstance(config.LAST_RUN, datetime)
        self.assertEqual(config.LAST_RUN.year, 2024)
        self.assertEqual(config.LAST_RUN.month, 1)
        self.assertEqual(config.LAST_RUN.day, 15)

    @patch(
        "builtins.open",
        mock_open(read_data=json.dumps({k: v for k, v in SAMPLE_CONFIG.items() if k != "LAST_RUN"})),
    )
    def test_no_last_run(self):
        config = Config()
        self.assertEqual(config.LAST_RUN, "")


class TestUpdateConfig(unittest.TestCase):
    @patch("builtins.open", mock_open(read_data=json.dumps(SAMPLE_CONFIG)))
    def test_writes_config(self):
        config = Config()

        m = mock_open()
        with patch("builtins.open", m):
            config.update_config()

        m.assert_called_once_with("settings.json", "w")
        written = "".join(
            call.args[0] for call in m().write.call_args_list
        )
        data = json.loads(written)
        self.assertEqual(data["DISCORD_TOKEN"], "test-token")
        self.assertEqual(data["DB_HOST"], "localhost")
        self.assertEqual(data["X_Riot_Token"], "riot-token")


if __name__ == "__main__":
    unittest.main()
