from apps.summoner.models import Summoner
from discord_webhook import DiscordWebhook
from django.conf import settings


def run():
    for summ in Summoner.objects.all():
        try:
            summ.poll()
        except Exception as e:
            DiscordWebhook.post_to_me(settings.DISCORD_ERROR_HOOK, e)
