import requests
from django.conf import settings
from discord_webhook import DiscordWebhook
import time


def call_api(url):
    req = requests.get(
        url,
        headers={"X-Riot-Token": settings.X_RIOT_TOKEN},
    )
    if req.status_code == 429:
        DiscordWebhook.post_to_me(settings.DISCORD_ERROR_HOOK, "Ratelimiting hit")
        time.sleep(60)
        return call_api(url)
    elif req.status_code != 200:
        DiscordWebhook.post_to_me(
            settings.DISCORD_ERROR_HOOK, f"API error {req.status_code}: {req.json()}"
        )
    return req
