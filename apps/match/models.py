import requests
from django.conf import settings
from django.db import models
import os
import json


# Create your models here.
class Match(models.Model):
    match_id = models.CharField(max_length=15)
    summoner = models.ForeignKey("summoner.Summoner", on_delete=models.CASCADE)
    champion_name = models.CharField(max_length=20)
    penta_kills = models.IntegerField(default=0)
    quadra_kills = models.IntegerField(default=0)
    triple_kills = models.IntegerField(default=0)
    epic_steals = models.IntegerField(default=0)
    kills = models.IntegerField(default=0)
    deaths = models.IntegerField(default=0)
    assists = models.IntegerField(default=0)
    kda = models.FloatField(default=0)

    def __str__(self):
        return f"Match {self.match_id} for {self.summoner.name}"

    @staticmethod
    def create_match(match_id, summoner):
        match_req = requests.get(
            f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}",
            headers={"X-Riot-Token": settings.X_RIOT_TOKEN},
        )
        if (
            match_req.status_code == 200
            and match_req.json().get("info").get("queueId") == 420
        ):
            match_data = match_req.json()
            for participant in match_data.get("info").get("participants"):
                if participant.get("puuid") == summoner.puu_id:
                    match = Match(
                        match_id=match_id,
                        summoner=summoner,
                        champion_name=participant.get("championName"),
                        penta_kills=participant.get("pentaKills"),
                        quadra_kills=participant.get("quadraKills"),
                        triple_kills=participant.get("tripleKills"),
                        epic_steals=participant.get("challenges").get(
                            "epicMonsterSteals"
                        ),
                        kills=participant.get("kills"),
                        deaths=participant.get("deaths"),
                        assists=participant.get("assists"),
                        kda=participant.get("challenges").get("kda"),
                    )
                    match.save()
                    Match.write(match_id, match_data)
                    return match

    @staticmethod
    def find_last_ranked(summoner):
        match_req = requests.get(
            f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{summoner.puu_id}/ids?start=0&count=1&queue=420",
            headers={"X-Riot-Token": settings.X_RIOT_TOKEN},
        )
        if match_req.status_code == 200 and match_req.json():
            for match in match_req.json():
                return Match.create_match(match, summoner)
        else:
            raise Exception(f"Can't find any rank records fur {summoner.puu_id}")

    @staticmethod
    def write(match_id, match):
        os.makedirs("matches", exist_ok=True)

        with open(f"{os.getcwd()}/matches/{match_id}.json", "w") as f:
            f.write(json.dumps(match))
            f.close()

    @staticmethod
    def read(match_id):
        os.makedirs("matches", exist_ok=True)
        with open(f"{os.getcwd()}/matches/{match_id}.json", "r") as f:
            match = json.load(f)
            f.close()
            return match


class Promos(models.Model):
    target = models.IntegerField()
    wins = models.IntegerField()
    losses = models.IntegerField()
    progress = models.CharField(max_length=5)

    def __eq__(self, other):
        return (
            isinstance(other, Promos)
            and self.target == other.target
            and self.wins == other.wins
            and self.losses == other.losses
            and self.progress == other.prgress
        )


class RankedRecord(models.Model):
    tier = models.IntegerField()
    rank = models.IntegerField()
    lp = models.IntegerField()
    summoner = models.ForeignKey("summoner.Summoner", on_delete=models.CASCADE)
    match = models.OneToOneField(
        Match, on_delete=models.CASCADE, null=True, default=None
    )
    promo = models.OneToOneField(
        Promos, on_delete=models.CASCADE, null=True, default=None
    )

    def __eq__(self, other):
        return (
            isinstance(other, RankedRecord)
            and self.tier == other.tier
            and self.rank == other.rank
            and self.lp == other.lp
            and self.promo == other.promo
        )

    @staticmethod
    def create_record(summoner, match, ranked):
        promo = None
        if ranked.get("miniSeries"):
            promo = Promos.objects.create(
                target=ranked.get("miniSeries").get("target"),
                wins=ranked.get("miniSeries").get("wins"),
                losses=ranked.get("miniSeries").get("losses"),
                progress=ranked.get("miniSeries").get("progress"),
            )
        RankedRecord.objects.create(
            tier=RankedRecord.tier_to_int(ranked.get("tier")),
            rank=RankedRecord.rank_to_int(ranked.get("rank")),
            lp=ranked.get("leaguePoints"),
            summoner=summoner,
            match=match,
            promo=promo,
        )

    def absolute_value(self):
        return self.tier * 400 + self.rank * 100 + self.lp

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
