import config
from datetime import datetime, timedelta
import requests
import psycopg2
from discord_webhook import DiscordWebhook
from summoner import Summoner
from match import Match
from league import trend
from graph import graph


class DBManager:
    host = port = db = user = password = ""

    def __init__(self, conf):
        self.host = conf.DB_HOST
        self.port = conf.DB_PORT
        self.db = conf.DB_NAME
        self.user = conf.DB_USERNAME
        self.password = conf.DB_PW

    def get_connection(self):
        conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.db,
            user=self.user,
            password=self.password,
            sslmode="require",
        )
        conn.autocommit = True
        cur = conn.cursor()
        return conn, cur

    def close_connection(self, conn, cur):
        cur.close()
        conn.close()

    def query(self, query, values=()):
        conn, cur = self.get_connection()
        cur.execute(query, values)
        results = cur.fetchall()
        self.close_connection(conn, cur)
        return results

    def insert(self, query, values=()):
        conn, cur = self.get_connection()
        cur.execute(query, values)
        self.close_connection(conn, cur)


class Poller:
    conf = ""
    db = ""

    def __init__(self):
        self.conf = config.Config()
        if not self.conf.LAST_RUN:
            self.conf.LAST_RUN = datetime.now() - timedelta(days=7)
        self.db = DBManager(self.conf)
        self.poll()
        self.conf.LAST_RUN = datetime.now()
        self.conf.update_config()

    def poll(self):
        self.get_lp()

    def lp_graph(self, record):
        sums = [
            Summoner(_tier=val[2], _rank=val[1], _lp=val[0], _name=record.name)
            for val in Summoner.last_ten_summoner(self.db, record.name)
        ]
        if sums:
            graph(sums)
            DiscordWebhook.post_image_to_discord(
                self.conf.DISCORD_REPORT_HOOK,
                f"LP graph over last {len(sums)} games",
                "graph.png",
            )

    def events(self, record, puuid):
        match_id = Match.get_latest_match_id(puuid, self.conf)
        event = Match.get_notable_events(record.name, match_id, self.conf)
        if event:
            DiscordWebhook.post_to_discord(
                self.conf.DISCORD_REPORT_HOOK,
                event,
            )

    def print_regular_match(self, record, last):
        if last and record < last:
            res = f" and lost.."
            if last.rank != record.rank:
                res += f"Demoted to {record.tier} {record.rank}"
        elif last and record > last:
            res = f" and won!"
            if record.promo:
                res += f" PROMO TIME!! {record.str_promo()}"
            elif last.rank != record.rank or last.tier != record.tier:
                res += f" Promoted to {record.tier} {record.rank}! Rising up!"
        else:
            res = f"."

        # if last and (record.rank != last.rank or record.tier != last.tier):
        DiscordWebhook.post_to_discord(
            self.conf.DISCORD_REPORT_HOOK,
            f"{record.name} just played a match{res}",
        )
        last_five = Summoner.five_ago(self.db, record.name)
        if not record.promo and last_five:
            DiscordWebhook.post_to_discord(
                self.conf.DISCORD_REPORT_HOOK,
                f"{trend(record, last_five)}",
            )

        self.lp_graph(record)

    def compare_promos(self, record):
        DiscordWebhook.post_to_discord(
            self.conf.DISCORD_REPORT_HOOK,
            f"{record.name} just played a promo game and... {record.last_promo()} {record.str_promo()}"
            f"{record.promos_left()} matches left.",
        )

    def new_match(self, record, last, puuid):
        record.save_to_db(self.db)
        if record.name != "whatever25":
            return
        if record.promo and last and last.promo:
            self.compare_promos(record)
        else:
            self.print_regular_match(record, last)
        self.events(record, puuid)

    def get_lp(self):
        names = ["whatever25", "MartijnMumbles"]
        for name in names:
            sum_req = requests.get(
                f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-name/{name}",
                headers={"X-Riot-Token": self.conf.X_Riot_Token},
            )
            if sum_req.status_code != 200:
                DiscordWebhook.post_to_me(
                    self.conf.DISCORD_ERROR_HOOK,
                    f"{sum_req.status_code} error, token expired? {sum_req.url}",
                )
                raise Exception("Failed API call")
            rank_req = requests.get(
                f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-summoner/{sum_req.json().get('id')}",
                headers={"X-Riot-Token": self.conf.X_Riot_Token},
            )

            for rank in rank_req.json():
                if rank.get("queueType") == "RANKED_SOLO_5x5":
                    promo = ""
                    if rank.get("miniSeries"):
                        promo = rank.get("miniSeries").get("progress")
                    record = Summoner(
                        rank.get("tier"),
                        rank.get("rank"),
                        rank.get("leaguePoints"),
                        name,
                        promo,
                    )

                    last = Summoner.last_record(self.db, name)
                    if not last or record != last:
                        self.new_match(record, last, sum_req.json().get("puuid"))


if __name__ == "__main__":
    Poller()
