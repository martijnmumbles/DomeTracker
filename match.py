import requests


class Match:
    @staticmethod
    def get_latest_match_id(puuid, conf):
        matches_req = requests.get(
            f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=20",
            headers={"X-Riot-Token": conf.X_Riot_Token},
        )
        return matches_req.json()[0]

    @staticmethod
    def get_match(match_id, conf):
        match_req = requests.get(
            f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}",
            headers={"X-Riot-Token": conf.X_Riot_Token},
        )
        return match_req.json()

    @staticmethod
    def get_participant(name, match_id, conf):
        match = Match.get_match(match_id, conf)
        participants = match.get("info").get("participants")
        return [x for x in participants if x.get("summonerName") == name][0]

    @staticmethod
    def get_notable_events(name, match_id, conf):
        participant = Match.get_participant(name, match_id, conf)
        if participant.get("pentaKills") and participant.get("pentaKills") > 0:
            return f"PENTAKILL BAAAYBBEEE! {name.upper()} does not believe \"sharing is caring\" on {participant.get('championName')}"
        if participant.get("quadraKills") and participant.get("quadraKills") > 0:
            return f"EPIC! {name.upper()} SECURED A QUADRA KILL ON {participant.get('championName').upper()}"
        if participant.get("tripleKills") and participant.get("tripleKills") > 0:
            return f"{name} with the Trip-Trip-Triple kill on {participant.get('championName')}! Let's go!"
        if (
            participant.get("epicMonsterSteals")
            and participant.get("epicMonsterSteals") > 0
        ):
            return f"{name} coming in like a thief in the night. \"What's mine is mine, and what's yours is also mine\". Assisted in an epic monster steal!"
