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
    kda = models.IntegerField(default=0)
    lp_diff = models.IntegerField(null=True, default=None)

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
