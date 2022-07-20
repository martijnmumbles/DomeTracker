from django.db import models
import requests
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

    def report_new(self):
        if not self.report_hook:
            return
        if self.match_set.count() == 1:
            record = self.match_set.first().rankedrecord
            DiscordWebhook.post_to_discord(
                self.report_hook, f"{self.name} added. Currently {record}."
            )
        else:
            matches = self.match_set.order_by("-start_time")[:10]
            match_result = "won" if matches[0].win else "lost"
            DiscordWebhook.post_to_discord(
                self.report_hook,
                f"{self.name} just {match_result} as {matches[0].champion_name}!",
            )
            if matches[0].rankedrecord.promo:
                if not matches[1].rankedrecord.promo:
                    DiscordWebhook.post_to_discord(
                        self.report_hook,
                        f"Starting promos! {matches[0].rankedrecord.promo.target-matches[0].rankedrecord.promo.wins}"
                        " wins needed! May your inner-Faker channel through.",
                    )
                else:
                    if matches[0].win:
                        DiscordWebhook.post_to_discord(
                            self.report_hook,
                            f"One step closer to {RankedRecord.int_to_tier(matches[0].rankedrecord.tier+1)}! Keep it "
                            f"up!",
                        )
                    else:
                        DiscordWebhook.post_to_discord(
                            self.report_hook,
                            f"Time to rally. Step up to the fight, bring them down! Clutch out those "
                            f"{matches[0].rankedrecord.promo.target-matches[0].rankedrecord.promo.wins} win(s)!",
                        )
            elif matches[1].rankedrecord.promo:
                if not matches[0].win:
                    DiscordWebhook.post_to_discord(
                        self.report_hook,
                        'Promos ended.. "Mission Failed. We\'ll Get Em Next Time."',
                    )
                else:
                    DiscordWebhook.post_to_discord(
                        self.report_hook,
                        f"Promos ended, congratulations! Sally forth brave Summoner, may "
                        f"{RankedRecord.int_to_tier(matches[1].rankedrecord.tier)} be kind.",
                    )
            else:
                trend = ""
                if len(matches) > 4:
                    trend = RankedRecord.trend(
                        matches[0].rankedrecord, matches[1].rankedrecord
                    )
                match_result = "Gained" if matches[0].win else "Lost"
                DiscordWebhook.post_to_discord(
                    self.report_hook,
                    f"{match_result} "
                    f"{abs(matches[0].rankedrecord.absolute_value()-matches[1].rankedrecord.absolute_value())} LP."
                    f" {trend}",
                )
                if matches[0].rankedrecord.rank > matches[1].rankedrecord.rank:
                    DiscordWebhook.post_to_discord(
                        self.report_hook,
                        f"Rising up to {RankedRecord.int_to_tier(matches[0].rankedrecord.tier)}"
                        f" {RankedRecord.int_to_rank(matches[0].rankedrecord.rank)}!",
                    )
                elif matches[1].rankedrecord.rank > matches[0].rankedrecord.rank:
                    DiscordWebhook.post_to_discord(
                        self.report_hook,
                        f"Dropped down to {RankedRecord.int_to_tier(matches[0].rankedrecord.tier)}"
                        f" {RankedRecord.int_to_rank(matches[0].rankedrecord.rank)}.. Time to rally. Step up to the "
                        f"fight, bring them down!",
                    )
            self.graph(10)
            for event in matches[0].events():
                DiscordWebhook.post_to_discord(self.report_hook, event)

    def poll(self):
        time.sleep(1)
        self.update_summoner_data()
        matches_req = requests.get(
            f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{self.puu_id}/ids?start=0&count=1&queue=420",
            headers={"X-Riot-Token": settings.X_RIOT_TOKEN},
        )

        if matches_req.status_code == 200:
            for match_id in matches_req.json():
                if match_id == self.match_set.last().match_id:
                    break
                else:
                    # new match found
                    match = Match.create_match(match_id, self)
                    try:
                        rank = self.get_current_rank()
                        RankedRecord.create_record(self, match, rank)
                        if self.report_hook:
                            self.report_new()
                    except:
                        time.sleep(5)
                        rank = self.get_current_rank()
                        RankedRecord.create_record(self, match, rank)
                        if self.report_hook:
                            self.report_new()
        else:
            raise RiotAPIException(
                f"Failed to poll match list: {matches_req.json()} {self.name}"
            )

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
            raise RiotAPIException(
                f"Failed to update summoner info: {sum_req.json()} {self.puu_id}"
            )

    def get_current_rank(self):
        rank_req = requests.get(
            f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-summoner/{self.summoner_id}",
            headers={"X-Riot-Token": settings.X_RIOT_TOKEN},
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
        sum_req = requests.get(
            f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-name/{name}",
            headers={"X-Riot-Token": settings.X_RIOT_TOKEN},
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
                new_sum.report_new()
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
