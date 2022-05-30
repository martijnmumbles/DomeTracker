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
