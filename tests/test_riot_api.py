import os
import unittest
from unittest.mock import patch, MagicMock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DomeTracker.settings")

import django

django.setup()

from riot_api import call_api


class TestCallApi(unittest.TestCase):
    @patch("riot_api.DiscordWebhook")
    @patch("riot_api.requests.get")
    def test_success(self, mock_get, mock_webhook):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": "test"}
        mock_get.return_value = mock_resp

        result = call_api("https://api.example.com/test")

        self.assertEqual(result.status_code, 200)
        mock_get.assert_called_once()
        mock_webhook.post_to_me.assert_not_called()

    @patch("riot_api.time.sleep")
    @patch("riot_api.DiscordWebhook")
    @patch("riot_api.requests.get")
    def test_rate_limit_retry(self, mock_get, mock_webhook, mock_sleep):
        rate_limit_resp = MagicMock()
        rate_limit_resp.status_code = 429

        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.json.return_value = {"data": "ok"}

        mock_get.side_effect = [rate_limit_resp, success_resp]

        result = call_api("https://api.example.com/test")

        self.assertEqual(result.status_code, 200)
        self.assertEqual(mock_get.call_count, 2)
        mock_sleep.assert_called_once_with(60)
        mock_webhook.post_to_me.assert_called_once()

    @patch("riot_api.DiscordWebhook")
    @patch("riot_api.requests.get")
    def test_error_code(self, mock_get, mock_webhook):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.json.return_value = {"status": {"message": "Forbidden"}}
        mock_get.return_value = mock_resp

        result = call_api("https://api.example.com/test")

        self.assertEqual(result.status_code, 403)
        mock_webhook.post_to_me.assert_called_once()
        call_args = mock_webhook.post_to_me.call_args[0]
        self.assertIn("403", call_args[1])

    @patch("riot_api.DiscordWebhook")
    @patch("riot_api.requests.get")
    def test_passes_riot_token_header(self, mock_get, mock_webhook):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        call_api("https://api.example.com/test")

        call_args = mock_get.call_args
        self.assertIn("X-Riot-Token", call_args[1]["headers"])


if __name__ == "__main__":
    unittest.main()
