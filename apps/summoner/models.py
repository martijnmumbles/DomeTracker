from django.db import models
from riot_api import call_api
from django.conf import settings
from apps.match.models import Match, RankedRecord, RiotAPIException
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from django.db.models.signals import post_save
from apps.change.models import Change
from model_utils import FieldTracker
from discord_webhook import DiscordWebhook
import time
from datetime import datetime, timedelta, timezone, time as t


class Summoner(models.Model):
    name = models.CharField(max_length=16, null=False)
    report_hook = models.CharField(max_length=120, null=True)
    summoner_id = models.CharField(max_length=63)
    account_id = models.CharField(max_length=56)
    puu_id = models.CharField(max_length=78, unique=True)
    bully_opt_in = models.BooleanField(default=False)
    tracker = FieldTracker()

    def __str__(self):
        return f"{self.name}"

    def to_json(self):
        return {
            "name": self.name,
            "report_hook": self.report_hook,
            "summoner_id": self.summoner_id,
            "account_id": self.account_id,
            "puu_id": self.puu_id,
        }

    def get_weekly(self):
        result = {
            "epic_steals": 0,
            "kills": 0,
            "deaths": 0,
            "assists": 0,
            "kda": 0,
            "win": 0,
            "vision_score": 0,
            "first_blood_kill": 0,
            "first_blood_assist": 0,
            "first_tower_kill": 0,
            "first_tower_assist": 0,
        }
        matches = self.match_set.filter(
            start_time__range=[
                (
                    datetime.combine(datetime.now(timezone.utc), t.min)
                    - timedelta(weeks=1)
                ).replace(tzinfo=timezone.utc),
                datetime.now(timezone.utc),
            ]
        )
        for match in matches:
            result["epic_steals"] += match.epic_steals
            result["kills"] += match.kills
            result["deaths"] += match.deaths
            result["assists"] += match.assists
            result["kda"] = match.kda if match.kda > result["kda"] else result["kda"]
            result["win"] += match.win
            result["vision_score"] += match.vision_score
            result["first_blood_kill"] += match.first_blood_kill
            result["first_blood_assist"] += match.first_blood_assist
            result["first_tower_kill"] += match.first_tower_kill
            result["first_tower_assist"] += match.first_tower_assist
        if matches.exists():
            result["vision_score"] = round(result["vision_score"] / len(matches), 2)
            result["kda"] = round(result["kda"], 2)
            return result
        else:
            return None

    def recent_stats(self):
        records = self.match_set.order_by("-start_time")[:10]
        length = len(records)
        kills = deaths = assists = kda = wins = 0
        min_kills = min_deaths = min_assists = min_kda = 10000
        max_kills = max_deaths = max_assists = max_kda = 0
        for match in records:
            kills += match.kills
            min_kills = match.kills if min_kills > match.kills else min_kills
            max_kills = match.kills if max_kills < match.kills else max_kills
            deaths += match.deaths
            min_deaths = match.deaths if min_deaths > match.deaths else min_deaths
            max_deaths = match.deaths if max_deaths < match.deaths else max_deaths
            assists += match.assists
            min_assists = match.assists if min_assists > match.assists else min_assists
            max_assists = match.assists if max_assists < match.assists else max_assists
            kda += match.kda
            min_kda = match.kda if min_kda > match.kda else min_kda
            max_kda = match.kda if max_kda < match.kda else max_kda
            wins += 1 if match.win else 0
        return (
            f"Over the last {length} games, {self.name} has been averaging:\n"
            f"{round(kills/length, 2)} kills ({min_kills} min, {max_kills} max)\n"
            f"{round(deaths/length, 2)} deaths ({min_deaths} min, {max_deaths} max)\n"
            f"{round(assists/length, 2)} assists ({min_assists} min, {max_assists} max)\n"
            f"A {round(kda/length, 2)} KDA ({round(min_kda, 2)} min, {round(max_kda, 2)} max)\n\n"
            f"{wins} wins, {length-wins} losses"
        )

    def graph(self, length=10, post=True):
        records = self.match_set.order_by("-start_time")[:length]
        base_val = records[0].rankedrecord.absolute_value() // 100 * 100
        plt.plot(
            range(1, len(records) + 1),
            [
                x.rankedrecord.absolute_value() - base_val
                for x in list(reversed(records))
            ],
        )
        file_name = f"graph_{records[0].summoner.name}.png"
        plt.savefig(file_name)
        if self.report_hook and post:
            DiscordWebhook.post_image_to_discord(
                self.report_hook,
                f"LP graph over last {len(records)} games",
                file_name,
            )
        plt.clf()
        return f"LP graph over last {len(records)} games"

    def report_ongoing_promos(self, matches):
        # new promos
        if not matches[1].rankedrecord.promo:
            DiscordWebhook.post_to_discord(
                self.report_hook,
                f"Starting promos! {matches[0].rankedrecord.promo.target - matches[0].rankedrecord.promo.wins}"
                " wins needed! May your inner-Faker channel through.",
            )
            return

        # won promo match
        if matches[0].win:
            DiscordWebhook.post_to_discord(
                self.report_hook,
                f"One step closer to {RankedRecord.int_to_tier(matches[0].rankedrecord.tier + 1)}! Keep it "
                f"up! {5 - matches[0].rankedrecord.promo.losses - matches[0].rankedrecord.promo.wins}"
                f" matches left to play.",
            )
            return

        # lost promo match
        if (
            matches[0].rankedrecord.promo.target - matches[0].rankedrecord.promo.wins
            == 1
        ):
            clutch = "Clutch out that last win!"
        else:
            clutch = (
                f"Clutch out those "
                f"{matches[0].rankedrecord.promo.target - matches[0].rankedrecord.promo.wins} wins!"
            )
        DiscordWebhook.post_to_discord(
            self.report_hook,
            f"Time to rally. Step up to the fight, bring them down! {clutch} "
            f"{5 - matches[0].rankedrecord.promo.losses - matches[0].rankedrecord.promo.wins} matches left "
            f"to play.",
        )

    def report_promos_result(self, matches):
        if not matches[0].win:
            DiscordWebhook.post_to_discord(
                self.report_hook,
                'Promos ended.. "Mission Failed. We\'ll Get Em Next Time."',
            )
        else:
            DiscordWebhook.post_to_discord(
                self.report_hook,
                f"Promos ended, congratulations! Sally forth brave Summoner, may "
                f"{RankedRecord.int_to_tier(matches[0].rankedrecord.tier)} be kind.",
            )

    def report_regular_match(self, matches):
        trend = ""
        if len(matches) > 4:
            trend = RankedRecord.trend(matches[0].rankedrecord, matches[4].rankedrecord)
        match_result = "Gained" if matches[0].win else "Lost"
        DiscordWebhook.post_to_discord(
            self.report_hook,
            f"{match_result} "
            f"{abs(matches[0].rankedrecord.absolute_value() - matches[1].rankedrecord.absolute_value())} LP."
            f" {trend}",
        )
        # gained a rank/tier
        if (
            matches[0].rankedrecord.rank > matches[1].rankedrecord.rank
            and not matches[0].rankedrecord.tier < matches[1].rankedrecord.tier
        ) or matches[0].rankedrecord.tier > matches[1].rankedrecord.tier:
            DiscordWebhook.post_to_discord(
                self.report_hook,
                f"Rising up to {RankedRecord.int_to_tier(matches[0].rankedrecord.tier)}"
                f" {RankedRecord.int_to_rank(matches[0].rankedrecord.rank)}!",
            )
        # lost a rank/tier
        elif (
            matches[0].rankedrecord.rank < matches[1].rankedrecord.rank
            or matches[0].rankedrecord.tier < matches[1].rankedrecord.tier
        ):
            DiscordWebhook.post_to_discord(
                self.report_hook,
                f"Dropped down to {RankedRecord.int_to_tier(matches[0].rankedrecord.tier)}"
                f" {RankedRecord.int_to_rank(matches[0].rankedrecord.rank)}.. Time to rally. Step up to the "
                f"fight, bring them down!",
            )

    def report_new_match_found(self):
        # no report link set
        if not self.report_hook:
            return

        # first detected match
        if self.match_set.count() == 1:
            record = self.match_set.first().rankedrecord
            DiscordWebhook.post_to_discord(
                self.report_hook, f"{self.name} added. Currently {record}."
            )
            return

        # report last match result
        matches = self.match_set.order_by("-start_time")[:10]
        match_result = "won" if matches[0].win else "lost"
        DiscordWebhook.post_to_discord(
            self.report_hook,
            f"{self.name} just {match_result} as {matches[0].champion_name}!",
        )

        # report active promos
        if matches[0].rankedrecord.promo:
            self.report_ongoing_promos(matches)
        # report promos that have ended
        elif matches[1].rankedrecord.promo:
            self.report_promos_result(matches)
        # report regular match
        else:
            self.report_regular_match(matches)
        self.graph(10)
        for event in matches[0].events():
            DiscordWebhook.post_to_discord(self.report_hook, event)

    def poll(self):
        self.update_summoner_data()
        matches_req = call_api(
            f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{self.puu_id}/ids?start=0&count=1&queue=420"
        )

        if not matches_req.status_code == 200:
            raise RiotAPIException(
                f"Failed to poll match list: {matches_req.json()} {self.name}"
            )
        for match_id in matches_req.json():
            if match_id == self.match_set.last().match_id:
                break
            # new match found
            match = Match.create_match(match_id, self)
            try:
                rank = self.get_current_rank()
                RankedRecord.create_record(self, match, rank)
                if self.report_hook:
                    self.report_new_match_found()
            except:
                time.sleep(5)
                rank = self.get_current_rank()
                RankedRecord.create_record(self, match, rank)
                if self.report_hook:
                    self.report_new_match_found()

    def update_summoner_data(self):
        sum_req = call_api(
            f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{self.puu_id}"
        )
        if sum_req.status_code == 200:
            reply = sum_req.json()
            self.name = reply.get("name")
            self.summoner_id = reply.get("id")
            self.account_id = reply.get("accountId")
            self.save()
        else:
            raise RiotAPIException(
                f"Failed to update summoner info: {sum_req.json()} {self.puu_id}"
            )

    def get_current_rank(self):
        rank_req = call_api(
            f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-summoner/{self.summoner_id}"
        )
        if rank_req.status_code == 200:
            for rank in rank_req.json():
                if rank.get("queueType") == "RANKED_SOLO_5x5":
                    return rank
        else:
            raise RiotAPIException(
                f"Failed to find rank info: {rank_req} {self.summoner_id}"
            )

    @staticmethod
    def create_summoner(name, report_hook=None):
        sum_req = call_api(
            f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-name/{name}"
        )
        if sum_req.status_code == 200:
            reply_sum = sum_req.json()
            new_sum = Summoner(
                name=reply_sum.get("name"),
                summoner_id=reply_sum.get("id"),
                account_id=reply_sum.get("accountId"),
                puu_id=reply_sum.get("puuid"),
                report_hook=report_hook,
            )
            new_sum.save()

            match_id = Match.find_last_ranked(new_sum)
            last_match = Match.create_match(match_id, new_sum)
            rank = new_sum.get_current_rank()
            RankedRecord.create_record(new_sum, last_match, rank)
            if report_hook:
                new_sum.report_new_match_found()
            return new_sum
        else:
            raise RiotAPIException(f"Failed to find Summoner: {sum_req.json()} {name}")

    @staticmethod
    def on_update(sender, instance, **kwargs):
        Change.objects.create(
            ref_object=instance,
            changes=instance.tracker.changed(),
            new_object=instance.to_json(),
        )


post_save.connect(Summoner.on_update, sender=Summoner)
