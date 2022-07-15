from apps.summoner.models import Summoner


def run():
    for summ in Summoner.objects.all():
        summ.poll()
