import config
from datetime import datetime, timedelta
import requests
import psycopg2
from discord_webhook import DiscordWebhook


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


class Dome:
    tier = rank = lp = ""

    def __init__(self, _tier, _rank, _lp):
        self.tier = _tier
        self.rank = _rank
        self.lp = _lp

    def save_to_db(self, db):
        db.insert(
            "INSERT INTO dome (tier, rank, lp) VALUES (%s, %s, %s)",
            (self.tier, self.rank, self.lp),
        )

    @staticmethod
    def last_dome(db):
        val = db.query("SELECT * FROM dome ORDER BY created_at DESC LIMIT 1;")
        if val:
            return Dome(_tier=val[0][2], _rank=val[0][1], _lp=val[0][0])
        return Dome(None, None, None)


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
        self.get_dome()

    def get_dome(self):
        sum_req = requests.get(
            "https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-name/Thelmkon",
            headers={"X-Riot-Token": self.conf.X_Riot_Token},
        )
        if sum_req.status_code != 200:
            DiscordWebhook.post_to_discord(
                self.conf.DISCORD_ERROR_HOOK,
                f"{sum_req.status_code} error, token expired?",
            )
        rank_req = requests.get(
            f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-summoner/{sum_req.json().get('id')}",
            headers={"X-Riot-Token": self.conf.X_Riot_Token},
        )

        for rank in rank_req.json():
            if rank.get("queueType") == "RANKED_SOLO_5x5":
                dome = Dome(
                    rank.get("tier"), rank.get("rank"), rank.get("leaguePoints")
                )
                if dome.lp != Dome.last_dome(self.db).lp:
                    dome.save_to_db(self.db)


if __name__ == "__main__":
    Poller()
