from django.db import models
import requests
from django.conf import settings
from apps.match.models import Match
import matplotlib.pyplot as plt
from django.db.models.signals import post_save
from apps.change.models import Change
from model_utils import FieldTracker


class Summoner(models.Model):
    tier = models.IntegerField(null=True)
    rank = models.IntegerField(null=True)
    lp = models.IntegerField(null=True)
    name = models.CharField(max_length=16, null=False)
    report_hook = models.CharField(max_length=120, null=True)
    summoner_id = models.CharField(max_length=47)
    account_id = models.CharField(max_length=46)
    puu_id = models.CharField(max_length=78, unique=True)
    last_match_id = models.CharField(max_length=15)
    tracker = FieldTracker()

    def absolute_value(self):
        return self.tier * 400 + self.rank * 100 + self.lp

    def graph(self, records):
        base_val = self.absolute_value() // 100 * 100
        plt.plot(
            range(1, len(records) + 1),
            [self.absolute_value() - base_val for x in list(reversed(records))],
        )
        plt.savefig("graph.png")

    def poll(self):
        matches_req = requests.get(
            f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{self.puu_id}/ids?start=0&count=20",
            headers={"X-Riot-Token": settings.X_RIOT_TOKEN},
        )
        if matches_req.status_code == 200:
            for match_id in matches_req.json():
                if match_id == self.last_match_id:
                    break
                else:
                    Match.create_match(match_id, self)
        else:
            raise Exception(f"Failed to get matches on poll call for {self.name}")

    def to_json(self):
        return {
            "tier": self.tier,
            "rank": self.rank,
            "lp": self.lp,
            "name": self.name,
            "report_hook": self.report_hook,
            "summoner_id": self.summoner_id,
            "account_id": self.account_id,
            "puu_id": self.puu_id,
            "last_match_id": self.last_match_id,
        }

    def update_summoner_data(self):
        sum_req = requests.get(
            f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{self.puu_id}",
            headers={"X-Riot-Token": settings.X_RIOT_TOKEN},
        )
        if sum_req.status_code == 200:
            reply = sum_req.json()
            self.name = reply.get("name")
            self.summoner_id = reply.get("id")
            self.account_id = reply.get("accountId")
            self.save()
        else:
            raise Exception(
                "Failed to get summoner information on update_summoner call"
            )

    @staticmethod
    def on_update(sender, instance, **kwargs):
        Change.objects.create(
            ref_object=instance,
            changes=instance.tracker.changed(),
            new_object=instance.to_json(),
        )

    @staticmethod
    def create_summoner(name):
        sum_req = requests.get(
            f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-name/{name}",
            headers={"X-Riot-Token": settings.X_RIOT_TOKEN},
        )
        if sum_req.status_code == 200:
            reply_sum = sum_req.json()
            rank_req = requests.get(
                f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-summoner/{reply_sum.get('id')}",
                headers={"X-Riot-Token": settings.X_RIOT_TOKEN},
            )
            match_req = requests.get(
                f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{reply_sum.get('puuid')}/ids?start=0&count=1",
                headers={"X-Riot-Token": settings.X_RIOT_TOKEN},
            )
            if (
                rank_req.status_code == 200
                and match_req.status_code == 200
                and len(match_req.json()) == 1
            ):
                for rank in rank_req.json():
                    if rank.get("queueType") == "RANKED_SOLO_5x5":
                        new_sum = Summoner(
                            name=reply_sum.get("name"),
                            summoner_id=reply_sum.get("id"),
                            account_id=reply_sum.get("accountId"),
                            puu_id=reply_sum.get("puuid"),
                            tier=Summoner.tier_to_int(rank.get("tier")),
                            rank=Summoner.rank_to_int(rank.get("rank")),
                            lp=rank.get("leaguePoints"),
                            last_match_id=match_req.json()[0],
                        )
                        new_sum.save()
                        if rank.get("miniSeries"):
                            promo = rank.get("miniSeries")
                            new_promo = Promos(
                                target=promo.get("target"),
                                wins=promo.get("wins"),
                                losses=promo.get("losses"),
                                progress=promo.get("progress"),
                                summoner=new_sum,
                            )
                            new_promo.save()
                        return new_sum
            else:
                raise Exception(
                    f"Failed to get rank or match history information on create_summoner call for {name}"
                )
        else:
            raise Exception(
                f"Failed to get summoner information on create_summoner call for {name}"
            )

    def __str__(self):
        return f"{self.name}"

    @staticmethod
    def tier_to_int(tier):
        if tier.upper() == "IRON":
            return 0
        if tier.upper() == "BRONZE":
            return 1
        if tier.upper() == "SILVER":
            return 2
        if tier.upper() == "GOLD":
            return 3
        if tier.upper() == "PLATINUM":
            return 4
        if tier.upper() == "DIAMOND":
            return 5
        if tier.upper() == "MASTER":
            return 6
        if tier.upper() == "GRANDMASTER":
            return 7
        if tier.upper() == "CHALLENGER":
            return 8

    @staticmethod
    def int_to_tier(tier):
        if tier == 0:
            return "IRON"
        if tier == 1:
            return "BRONZE"
        if tier == 2:
            return "SILVER"
        if tier == 3:
            return "GOLD"
        if tier == 4:
            return "PLATINUM"
        if tier == 5:
            return "DIAMOND"
        if tier == 6:
            return "MASTER"
        if tier == 7:
            return "GRANDMASTER"
        if tier == 8:
            return "CHALLENGER"

    @staticmethod
    def rank_to_int(rank):
        if rank.upper() == "IV":
            return 0
        if rank.upper() == "III":
            return 1
        if rank.upper() == "II":
            return 2
        if rank.upper() == "I":
            return 3

    @staticmethod
    def int_to_rank(rank):
        if rank == 0:
            return "IV"
        if rank == 1:
            return "III"
        if rank == 2:
            return "II"
        if rank == 3:
            return "I"


class Promos(models.Model):
    target = models.IntegerField()
    wins = models.IntegerField()
    losses = models.IntegerField()
    progress = models.CharField(max_length=5)
    summoner = models.OneToOneField(Summoner, on_delete=models.CASCADE)


post_save.connect(Summoner.on_update, sender=Summoner)
