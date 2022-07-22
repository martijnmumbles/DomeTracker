import datetime

import discord
from discord.ext import commands
import logging
import requests
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DomeTracker.settings")

from DomeTracker import settings
import django

django.setup()
from apps.summoner.models import Summoner, RiotAPIException
from apps.match.models import Match
from asgiref.sync import sync_to_async


class YetAnotherBot(commands.Bot):
    def __init__(self, prefix, bot):
        commands.Bot.__init__(self, command_prefix=prefix, self_bot=bot)
        logger = logging.getLogger("discord")
        logger.setLevel(logging.WARNING)
        handler = logging.FileHandler(
            filename="discord.log", encoding="utf-8", mode="w"
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
        )
        logger.addHandler(handler)
        self.add_commands()

    # noinspection PyMethodMayBeStatic
    async def on_ready(self):
        print("YAB ready.")

    @staticmethod
    def check_param(*args, min_length=1, max_length=None):
        if len(args) >= min_length and not max_length or len(args) <= max_length:
            return " ".join(str(e) for e in args)
        else:
            return None

    @staticmethod
    def sanitize(user_input):
        return requests.utils.quote(user_input)

    def add_commands(self):
        stats_supported = [
            "epic_steals",
            "kills",
            "deaths",
            "assists",
            "kda",
            "win",
            "vision_score",
            "first_blood_kill",
            "first_blood_assist",
            "first_tower_kill",
            "first_tower_assist",
        ]

        @self.event
        async def on_command_error(ctx, error):
            if isinstance(error, discord.ext.commands.errors.CommandNotFound):
                await ctx.channel.send("That command wasn't found! Try <help")

        # @self.command(name="echo", pass_context=True)
        # async def echo(ctx):
        #     await ctx.channel.send(
        #         f"{ctx.author} in {ctx.channel}: {ctx.message.content}"
        #     )

        def _get_ranked(name):
            try:
                summ = Summoner.objects.get(name=name)
                return f"{summ.name} is {summ.match_set.order_by('-start_time').first().rankedrecord}"
            except Summoner.DoesNotExist:
                return f"{name} is not being tracked."

        @self.command(
            brief="Shows current rank for Summoner '<rank Thelmkon'",
            name="rank",
            pass_context=True,
        )
        async def rank(ctx, *args):
            name = YetAnotherBot.check_param(*args)
            if name:
                ranked = await sync_to_async(_get_ranked)(name=name)
                await ctx.channel.send(f"{ranked}")
            else:
                await ctx.channel.send(f"Correct usage '<rank Thelmkon'")

        def _track_summoner(name):
            try:
                Summoner.objects.get(name=name)
                return "Summoner is already being tracked"
            except Summoner.DoesNotExist:
                if Summoner.objects.count() >= 20:
                    return "Hardcoded limit set to 20 summoners to limit API call load"
                sum_req = requests.get(
                    f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-name/{YetAnotherBot.sanitize(name)}",
                    headers={"X-Riot-Token": settings.X_RIOT_TOKEN},
                )
                if sum_req.status_code == 200:
                    try:
                        summ = Summoner.create_summoner(name)
                        return f"Summoner added: {summ.match_set.last().rankedrecord}"
                    except RiotAPIException:
                        return "Riot API didn't return 200 OK"
                elif sum_req.status_code == 404:
                    return "Summoner by that name not found"
                else:
                    return "Invalid return code from Riot API"

        @self.command(
            brief="Enable tracking for Summoner",
            name="track",
            pass_context=True,
        )
        async def track(ctx, *args):
            name = YetAnotherBot.check_param(*args)
            if name:
                tracked = await sync_to_async(_track_summoner)(name=name)
                await ctx.channel.send(f"{tracked}")
            else:
                await ctx.channel.send(f"Correct usage '<track Thelmkon'")

        def _graph(name):
            summ = Summoner.objects.get(name=name)
            val = summ.graph(post=False)
            return f"{val} for {summ.name}"

        @self.command(
            brief="Show graph for summoner",
            name="graph",
            pass_context=True,
        )
        async def graph(ctx, *args):
            name = YetAnotherBot.check_param(*args)
            if name:
                try:
                    graph = await sync_to_async(_graph)(name=name)
                    if graph:
                        await ctx.channel.send(
                            graph, file=discord.File(f"graph_{name}.png")
                        )
                except Summoner.DoesNotExist:
                    await ctx.channel.send(f"Can't find summoner by that name")
            else:
                await ctx.channel.send(f"Correct usage '<graph Thelmkon'")

        def _matches(name):
            summ = Summoner.objects.get(name=name)
            val = " ".join(
                [ma.match_id for ma in summ.match_set.order_by("-start_time")]
            )
            return f"{val}"

        @self.command(
            brief="Show recorded matches for summoner",
            name="matches",
            pass_context=True,
        )
        async def matches(ctx, *args):
            name = YetAnotherBot.check_param(*args)
            if name:
                try:
                    match_list = await sync_to_async(_matches)(name=name)
                    if match_list:
                        await ctx.channel.send(match_list)
                except Summoner.DoesNotExist:
                    await ctx.channel.send(f"Can't find summoner by that name")
            else:
                await ctx.channel.send(f"Correct usage '<matches Thelmkon'")

        def _match_info(match_id):
            events = []
            match_list = Match.objects.filter(match_id=match_id)
            for match in match_list:
                events += match.events()
            return events

        @self.command(
            brief="Show match info for match ID",
            name="match_info",
            pass_context=True,
        )
        async def match_info(ctx, *args):
            match_id = YetAnotherBot.check_param(*args, min_length=1, max_length=1)
            if match_id:
                try:
                    match_events = await sync_to_async(_match_info)(match_id=match_id)
                    for event in match_events:
                        await ctx.channel.send(event)
                except Summoner.DoesNotExist:
                    await ctx.channel.send(f"Can't find match by that ID")
            else:
                await ctx.channel.send(f"Correct usage '<match_info EUW1_5889986459")

        def _last_match(name):
            summ = Summoner.objects.get(name=name)
            print(summ.name)
            match_id = summ.match_set.order_by("-start_time").first().match_id
            print(match_id)
            val = _match_info(match_id)
            return val

        @self.command(
            brief="Show match info for last recorded match for summoner",
            name="last_match",
            pass_context=True,
        )
        async def last_match(ctx, *args):
            name = YetAnotherBot.check_param(*args)
            if name:
                try:
                    match_events = await sync_to_async(_last_match)(name=name)
                    for event in match_events:
                        await ctx.channel.send(event)
                except Summoner.DoesNotExist:
                    await ctx.channel.send(f"Can't find summoner by that name")
            else:
                await ctx.channel.send(f"Correct usage '<last_match Thelmkon")

        def _recent(name):
            summ = Summoner.objects.get(name=name)
            return summ.recent_stats()

        @self.command(
            brief="Show stats for recent matches for summoner",
            name="recent",
            pass_context=True,
        )
        async def recent_stats(ctx, *args):
            name = YetAnotherBot.check_param(*args)
            if name:
                try:
                    stats = await sync_to_async(_recent)(name=name)
                    await ctx.channel.send(stats)
                except Summoner.DoesNotExist:
                    await ctx.channel.send(f"Can't find summoner by that name")
            else:
                await ctx.channel.send(f"Correct usage '<recent Thelmkon")

        def _weekly(stat):
            if stat in stats_supported:
                rankings = []
                for summ in Summoner.objects.all():
                    week = summ.get_weekly()
                    if week:
                        rankings.append((summ.name, week))
                keyword = (
                    "average"
                    if stat == "vision_score"
                    else "top"
                    if stat == "kda"
                    else "total"
                )
                results = []
                return [f"Showing {keyword} {stat} over the last 7 days"] + results

            return None

        @self.command(
            brief="Show weekly rankings",
            name="weekly",
            pass_context=True,
        )
        async def weekly(ctx, *args):
            stat = YetAnotherBot.check_param(*args, 1, 1)
            results = _weekly(stat)
            if results:
                for res in results:
                    await ctx.channel.send(res)
            else:
                await ctx.channel.send(f"Supported stats: {' '.join(stats_supported)}.")


if __name__ == "__main__":
    client = YetAnotherBot(prefix="<", bot=False)
    client.run(settings.DISCORD_TOKEN)
