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

    def add_commands(self):
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
            if len(args) != 1:
                await ctx.channel.send(f"Correct usage '<rank Thelmkon'")
            else:
                ranked = await sync_to_async(_get_ranked)(name=args[0])
                await ctx.channel.send(f"{ranked}")

        def _track_summoner(name):
            try:
                Summoner.objects.get(name=name)
                return "Summoner is already being tracked"
            except Summoner.DoesNotExist:
                if Summoner.objects.count() >= 20:
                    return "Hardcoded limit set to 20 summoners to limit API call load"
                sum_req = requests.get(
                    f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-name/{requests.utils.quote(name)}",
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
            if len(args) != 1:
                await ctx.channel.send(f"Correct usage '<track Thelmkon'")
            else:
                tracked = await sync_to_async(_track_summoner)(name=args[0])
                await ctx.channel.send(f"{tracked}")

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
            if len(args) != 1:
                await ctx.channel.send(f"Correct usage '<graph Thelmkon'")
            else:
                try:
                    graph = await sync_to_async(_graph)(name=args[0])
                    if graph:
                        await ctx.channel.send(
                            graph, file=discord.File(f"graph_{args[0]}.png")
                        )
                except Summoner.DoesNotExist:
                    await ctx.channel.send(f"Can't find summoner by that name")


if __name__ == "__main__":
    client = YetAnotherBot(prefix="<", bot=False)
    client.run(settings.DISCORD_TOKEN)
