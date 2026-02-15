import unittest
from unittest.mock import patch, MagicMock, mock_open

from discord_webhook import DiscordWebhook


class TestPostToDiscord(unittest.TestCase):
    @patch("discord_webhook.requests.post")
    def test_posts_message(self, mock_post):
        DiscordWebhook.post_to_discord("https://hook.example.com", "Hello!")
        mock_post.assert_called_once_with(
            "https://hook.example.com?wait=true",
            json={"content": "Hello!"},
        )

    @patch("discord_webhook.requests.post")
    def test_posts_with_correct_body(self, mock_post):
        DiscordWebhook.post_to_discord("https://hook.example.com", "Test message 123")
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["content"], "Test message 123")


class TestPostToMe(unittest.TestCase):
    @patch("discord_webhook.requests.post")
    def test_posts_with_mention(self, mock_post):
        DiscordWebhook.post_to_me("https://hook.example.com", "Alert!")
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("<@149112297355214849>", kwargs["json"]["content"])
        self.assertIn("Alert!", kwargs["json"]["content"])


class TestPostImageToDiscord(unittest.TestCase):
    @patch("discord_webhook.mimetypes.guess_type", return_value=("image/png", None))
    @patch("discord_webhook.open", mock_open(read_data=b"fake image data"), create=True)
    @patch("discord_webhook.requests.post")
    def test_posts_image(self, mock_post, mock_mime):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        DiscordWebhook.post_image_to_discord(
            "https://hook.example.com", "Check this graph!", "/tmp/graph.png"
        )

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://hook.example.com?wait=true")
        self.assertIn("files", kwargs)

    @patch("discord_webhook.mimetypes.guess_type", return_value=("image/png", None))
    @patch("discord_webhook.open", mock_open(read_data=b"fake image data"), create=True)
    @patch("discord_webhook.requests.post")
    def test_posts_error_on_failure(self, mock_post, mock_mime):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_post.return_value = mock_resp

        DiscordWebhook.post_image_to_discord(
            "https://hook.example.com", "Check this!", "/tmp/graph.png"
        )

        # Should have made a second call to report the error
        self.assertEqual(mock_post.call_count, 2)

    @patch("discord_webhook.requests.post")
    def test_no_image_path(self, mock_post):
        DiscordWebhook.post_image_to_discord(
            "https://hook.example.com", "No image", None
        )
        mock_post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
