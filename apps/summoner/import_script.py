from track import *
from .models import Summoner
from apps.match.models import Match, RankedRecord
import time


class ImportHistory:
    def __init__(self):
        conf = config.Config()
        db = DBManager(conf)
        sum_names = db.query("SELECT distinct(name) FROM public.lp_record;")
        for s in sum_names:
            print(s[0])
            summ = Summoner.create_summoner(s[0])

            match_count = db.query(
                f"SELECT count(id) FROM public.lp_record WHERE name = '{s[0]}';"
            )[0][0]

            sum_req = requests.get(
                f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-name/{s[0]}",
                headers={"X-Riot-Token": conf.X_Riot_Token},
            )

            match_req = requests.get(
                f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{sum_req.json().get('puuid')}/ids?start=0&count={match_count}&queue=420",
                headers={"X-Riot-Token": conf.X_Riot_Token},
            )
            lp_records = db.query(
                f"SELECT * FROM public.lp_record WHERE name = '{s[0]}' ORDER BY created_at DESC;"
            )
            for i in range(1, match_count):
                time.sleep(1)
                print(i, match_count, len(match_req.json()))

                match_id = match_req.json()[i]
                match = Match.create_match(match_id, summ)
                record = lp_records[i]
                rank = {"tier": record[2], "rank": record[1], "leaguePoints": record[0]}
                RankedRecord.create_record(summ, match, rank)


if __name__ == "__main__":
    ImportHistory()
