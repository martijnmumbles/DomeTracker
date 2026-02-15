import os
import unittest
from unittest.mock import patch, MagicMock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DomeTracker.settings")

import django

django.setup()

from imgflip_meme import generate_meme


class TestGenerateMeme(unittest.TestCase):
    @patch("imgflip_meme.requests.post")
    def test_posts_correct_params(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "success": True,
            "data": {"url": "https://imgflip.com/meme/123"},
        }
        mock_post.return_value = mock_resp

        result = generate_meme(12345, ["top text", "bottom text"])

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://api.imgflip.com/caption_image")
        params = kwargs["params"]
        self.assertEqual(params["template_id"], "12345")
        self.assertEqual(params["username"], "martijnmumbles")
        self.assertEqual(params["boxes[0][text]"], "top text")
        self.assertEqual(params["boxes[1][text]"], "bottom text")

    @patch("imgflip_meme.requests.post")
    def test_returns_json_response(self, mock_post):
        expected = {
            "success": True,
            "data": {"url": "https://imgflip.com/meme/123"},
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = expected
        mock_post.return_value = mock_resp

        result = generate_meme(99, ["a"])
        self.assertEqual(result, expected)

    @patch("imgflip_meme.requests.post")
    def test_three_text_boxes(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True}
        mock_post.return_value = mock_resp

        generate_meme(99, ["one", "two", "three"])
        params = mock_post.call_args[1]["params"]
        self.assertEqual(params["boxes[0][text]"], "one")
        self.assertEqual(params["boxes[1][text]"], "two")
        self.assertEqual(params["boxes[2][text]"], "three")


if __name__ == "__main__":
    unittest.main()
