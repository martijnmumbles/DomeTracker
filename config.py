import json
from datetime import datetime


class Config:
    DISCORD_TOKEN = ""
    DB_HOST = ""
    DB_PORT = ""
    DB_NAME = ""
    DB_USERNAME = ""
    DB_PW = ""
    LAST_RUN = ""
    X_Riot_Token = ""
    DISCORD_ERROR_HOOK = ""

    def __init__(self):
        with open("settings.json", "r") as conf_file:
            data = json.load(conf_file)
            self.DISCORD_TOKEN = data.get("DISCORD_TOKEN")
            self.DB_HOST = data.get("DB_HOST")
            self.DB_PORT = data.get("DB_PORT")
            self.DB_NAME = data.get("DB_NAME")
            self.DB_USERNAME = data.get("DB_USERNAME")
            self.DB_PW = data.get("DB_PW")
            self.X_Riot_Token = data.get("X_Riot_Token")
            self.DISCORD_ERROR_HOOK = data.get("DISCORD_ERROR_HOOK")
            if data.get("LAST_RUN"):
                self.LAST_RUN = datetime.strptime(
                    data.get("LAST_RUN"), "%Y-%m-%d %H:%M:%S.%f"
                )

    def update_config(self):
        with open("settings.json", "w") as jsonFile:
            data = {
                "DISCORD_TOKEN": self.DISCORD_TOKEN,
                "DB_HOST": self.DB_HOST,
                "DB_PORT": self.DB_PORT,
                "DB_NAME": self.DB_NAME,
                "DB_USERNAME": self.DB_USERNAME,
                "DB_PW": self.DB_PW,
                "LAST_RUN": self.LAST_RUN,
                "X_Riot_Token": self.X_Riot_Token,
                "DISCORD_ERROR_HOOK": self.DISCORD_ERROR_HOOK,
            }
            json.dump(data, jsonFile, indent=4, sort_keys=True, default=str)
