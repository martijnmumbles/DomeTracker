from functools import total_ordering
from league import tier_to_int, rank_to_int


@total_ordering
class Summoner:
    tier = rank = lp = name = promo = ""

    def __init__(self, _tier, _rank, _lp, _name, _promo=""):
        self.tier = _tier
        self.rank = _rank
        self.lp = _lp
        self.name = _name
        self.promo = _promo

    def save_to_db(self, db):
        db.insert(
            "INSERT INTO lp_record (tier, rank, lp, name, promo) VALUES (%s, %s, %s, %s, %s)",
            (self.tier, self.rank, self.lp, self.name, self.promo),
        )

    def __str__(self):
        return f"{self.name}, {self.tier}, {self.rank}, {self.lp}, {self.promo}"

    def __eq__(self, other):
        return (
            isinstance(other, Summoner)
            and self.tier.upper() == other.tier.upper()
            and self.rank.upper() == other.rank.upper()
            and self.lp == other.lp
            and self.promo == other.promo
        )

    def __lt__(self, other):
        if not isinstance(other, Summoner):
            raise Exception("Not a Summoner object")
        if tier_to_int(self) < tier_to_int(other):
            return True
        elif tier_to_int(self) > tier_to_int(other):
            return False
        if rank_to_int(self) < rank_to_int(other):
            return True
        elif rank_to_int(self) > rank_to_int(other):
            return False
        if self.lp < other.lp:
            return True
        return False

    def promos_left(self):
        count = 0
        rev = reversed(self.promo)
        for p in rev:
            if p == "N":
                count += 1
            else:
                return count
        return count

    def last_promo(self):
        rev = reversed(self.promo)
        for p in rev:
            if p == "W":
                return "WON! LET'S FUCKING GO!"
            if p == "L":
                return "lost.. Time to rally. Step up to the fight, bring them down!"

    def str_promo(self):
        wins = 0
        for p in self.promo:
            if p == "W":
                wins += 1
        return f"{3-wins} more win(s) needed!"

    @staticmethod
    def last_record(db, name):
        val = db.query(
            "SELECT * FROM lp_record WHERE name = %s ORDER BY created_at DESC LIMIT 1",
            (name,),
        )
        if val:
            return Summoner(
                _tier=val[0][2],
                _rank=val[0][1],
                _lp=val[0][0],
                _name=val[0][5],
                _promo=val[0][6],
            )
        return None

    @staticmethod
    def no_promos(values):
        for val in values:
            if val[6] and val[6] != "":
                return False
        return True

    @staticmethod
    def five_ago(db, name):
        val = db.query(
            "SELECT * FROM lp_record WHERE name = %s ORDER BY created_at DESC LIMIT 5",
            (name,),
        )
        if len(val) > 4 and Summoner.no_promos(val):
            return Summoner(
                _tier=val[4][2],
                _rank=val[4][1],
                _lp=val[4][0],
                _name=val[4][5],
                _promo=val[4][6],
            )
        return None

    @staticmethod
    def last_ten_summoner(db, name):
        val = db.query(
            "SELECT * FROM lp_record WHERE name = %s ORDER BY created_at DESC LIMIT 10",
            (name,),
        )
        return val
