from apps.summoner.models import Summoner
from discord_webhook import DiscordWebhook
from django.conf import settings
import time


def run():
    for summ in Summoner.objects.all():
        time.sleep(1)
        try:
            summ.poll()
        except Exception as e:
            DiscordWebhook.post_to_me(settings.DISCORD_ERROR_HOOK, e)
