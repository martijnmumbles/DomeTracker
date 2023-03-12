from django.db import models
import os
import json
from datetime import datetime, timezone
from imgflip_meme import generate_meme
import time
from riot_api import call_api


class RiotAPIException(Exception):
    def __init__(self, message="API did not return 200 OK"):
        # Call the base class constructor with the parameters it needs
        super(RiotAPIException, self).__init__(message)


class RiotEmptyResponseException(Exception):
    def __init__(self, message="API did not return expected response body"):
        # Call the base class constructor with the parameters it needs
        super(RiotEmptyResponseException, self).__init__(message)


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
    start_time = models.DateTimeField()
    duration = models.IntegerField(default=0)
    win = models.BooleanField(default=False)
    vision_wards_bought = models.IntegerField(default=0)
    wards_placed = models.IntegerField(default=0)
    vision_score = models.IntegerField(default=0)
    longest_time_spent_living = models.IntegerField(default=0)
    first_blood_kill = models.BooleanField(default=False)
    first_blood_assist = models.BooleanField(default=False)
    first_tower_kill = models.BooleanField(default=False)
    first_tower_assist = models.BooleanField(default=False)

    class Meta:
        ordering = ["start_time"]

    def __str__(self):
        return f"Match {self.match_id} for {self.summoner.name}"

    def events(self):
        event_list = [
            f"{self.summoner.name} went {self.kills}/{self.deaths}/{self.assists}, {round(self.kda, 2)} kda, "
            f"{self.vision_score} vision score."
        ]
        if self.penta_kills > 0:
            event_list.append(
                f"penta? penta? Penta? PENTA?! PENTAKILL BAAAYBBEEE! {self.summoner.name.upper()} does not believe "
                f'"sharing is caring" on {self.champion_name}'
            )
        elif self.quadra_kills > 0:
            event_list.append(
                f"EPIC! {self.summoner.name.upper()} SECURED A QUADRA KILL ON {self.champion_name.upper()}"
            )
        elif self.triple_kills > 0:
            event_list.append(
                f"{self.summoner.name} with the Trip-Trip-Triple kill on {self.champion_name}! Let's go!"
            )
        if self.first_blood_kill:
            event_list.append(f"Bloodthirsty {self.summoner.name} claimed first blood!")
        if self.epic_steals > 0:
            event_list.append(
                f"{self.summoner.name} coming in like a thief in the night. \"What's mine is mine, and what's yours is "
                f'also mine". Assisted in an epic monster steal!'
            )
        if self.duration > 3000:
            event_list.append(
                f"A {3000 // 60} minute game? Oof, you worked for that one!"
            )
        if self.summoner.bully_opt_in and self.vision_wards_bought < 2:
            if self.vision_wards_bought == 1:
                event_list.append(
                    f"{self.summoner.name} bought a (single) vision ward all game.. :thinking: And that was probably a "
                    f"missclick.",
                )
            else:
                event_list.append(
                    f"{self.summoner.name} didn't buy a single vision ward, clearly to leave space on the map "
                    f"for their teammates so they also feel like they're contributing..."
                )
        if self.summoner.bully_opt_in and self.vision_score < 10:
            meme = generate_meme(
                322841258,
                [
                    f"{self.summoner.name}: The API will return a single digit vision score.",
                    "Must be a bug, right?",
                    "Must be a bug?",
                ],
            )
            if meme.get("success"):
                event_list.append(meme.get("data").get("url"))
            else:
                event_list.append(
                    f"POTENTIAL API ERROR, single digit vision score! Must be a bug, right {self.summoner.name}"
                    f"?.. Oh say it *ain't* so.."
                )
        return event_list

    @staticmethod
    def update_all_new_attributes(field, name, challenges=False):
        for match in Match.objects.all():
            time.sleep(0.2)
            val = match.update_new_attribute(field, name, challenges)
            if not val:
                print(f"not found, {match.match_id} {match.summoner.name}")

    def update_new_attribute(self, field, name, challenges=False):
        loaded = Match.read(self.match_id)

        for player in loaded.get("info").get("participants"):
            if player.get("puuid") == self.summoner.puu_id:
                if challenges:
                    value = player.get("challenges").get(name)
                else:
                    value = player.get(name)
                setattr(self, field, value)
                self.save()
                return True
        return False

    def restore_puuid(self):
        match_req = call_api(
            f"https://europe.api.riotgames.com/lol/match/v5/matches/{self.match_id}"
        )
        if (
            match_req.status_code == 200
            and match_req.json().get("info").get("queueId") == 420
        ):
            match_data = match_req.json()
            Match.write(self.match_id, match_data)
            print(f"Updated {self.match_id}")
        else:
            raise RiotAPIException(
                f"{self.match_id}: {match_req.status_code} {match_req.json()}"
            )

    @staticmethod
    def create_match(match_id, summoner):
        match_req = call_api(
            f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}"
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
                        start_time=datetime.fromtimestamp(
                            match_req.json().get("info").get("gameStartTimestamp")
                            / 1e3,
                            timezone.utc,
                        ),
                        duration=match_req.json().get("info").get("gameDuration"),
                        win=participant.get("win"),
                        vision_wards_bought=participant.get("visionWardsBoughtInGame"),
                        wards_placed=participant.get("wardsPlaced"),
                        vision_score=participant.get("visionScore"),
                        longest_time_spent_living=participant.get(
                            "longestTimeSpentLiving"
                        ),
                        first_blood_kill=participant.get("firstBloodKill"),
                        first_blood_assist=participant.get("firstBloodAssist"),
                        first_tower_kill=participant.get("firstTowerKill"),
                        first_tower_assist=participant.get("firstTowerAssist"),
                    )
                    match.save()
                    Match.write(match_id, match_data)
                    return match
        else:
            raise RiotAPIException(f"Failed to create match: {match_req.json()}")

    @staticmethod
    def find_last_ranked(summoner):
        match_req = call_api(
            f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{summoner.puu_id}/ids?start=0&count=1&queue=420"
        )
        if match_req.status_code == 200 and match_req.json():
            for match in match_req.json():
                return match
        else:
            raise RiotAPIException(f"Failed to find ranked history: {match_req.json()}")

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
            and self.progress == other.progress
        )

    def __lt__(self, other):
        if not isinstance(other, Promos):
            raise Exception("Not a Promos object")
        if self.wins > other.wins:
            return False
        elif self.wins < other.wins:
            return True
        if self.losses > other.losses:
            return True
        elif self.losses < other.losses:
            return False
        return False

    def __str__(self):
        return f"{self.wins} wins out of {self.target} needed. {5-self.losses-self.wins} matches left."


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

    def __lt__(self, other):
        if not isinstance(other, RankedRecord):
            raise Exception("Not a RankedRecord object")
        if self.promo and other.promo:
            if self.promo < other.promo:
                return True
            elif self.promo > other.promo:
                return False
        if self.tier < other.tier:
            return True
        elif self.tier > other.tier:
            return False
        if self.rank < other.rank:
            return True
        elif self.rank > self.rank:
            return False
        if self.lp < other.lp:
            return True
        return False

    def __str__(self):
        result = f"{RankedRecord.int_to_tier(self.tier)} {RankedRecord.int_to_rank(self.rank)} {self.lp} LP."
        if self.promo:
            result += f" {self.promo}"
        return result

    @staticmethod
    def trend(current, old):
        delta = round((current.absolute_value() - old.absolute_value()) / 4)
        trending = (
            f"Netting {'+' if delta > 0 else ''}{delta} lp over the last 4 games."
        )
        if delta < 0:
            threshold = (current.absolute_value() // 100) * 100
            buffer = current.absolute_value() - threshold
            if buffer // delta * -1 + 1 < 5:
                return (
                    trending
                    + f" Projected {buffer // delta * -1 + 1} game(s) until demotion :scream:"
                )
        if delta > 0:
            threshold = (current.absolute_value() // 100 + 1) * 100
            buffer = threshold - current.absolute_value()
            if buffer // delta + 1 < 5:
                return (
                    trending
                    + f" Projected {buffer // delta + 1} game(s) until promotion :+1::muscle:"
                )
        return trending

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
        if self.tier > 5:
            return self.tier * 400 + self.lp
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
