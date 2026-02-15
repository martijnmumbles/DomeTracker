import requests
import json
import mimetypes


class DiscordWebhook:
    @staticmethod
    def post_to_discord(webhook, message):
        body = {"content": f"{message}"}
        requests.post(f"{webhook}?wait=true", json=body)

    @staticmethod
    def post_to_me(webhook, message):
        body = {"content": f"<@149112297355214849>: {message}"}
        requests.post(f"{webhook}?wait=true", json=body)

    @staticmethod
    def post_image_to_discord(webhook, message, image_path):
        body = {"content": f"{message}"}
        data = json.dumps(body)
        data = data.encode("utf-8")

        if image_path:
            file_body = [
                (
                    "images",
                    (
                        image_path.split("/")[-1],
                        open(image_path, "rb"),
                        mimetypes.guess_type(image_path)[0],
                    ),
                ),
                ("payload_json", (None, data, "application/json")),
            ]
            r = requests.post(f"{webhook}?wait=true", files=file_body)
            if r.status_code != 200:
                DiscordWebhook.post_to_discord(
                    webhook,
                    f"Response code {r.status_code} received when posting file.",
                )
