from functools import total_ordering
from league import tier_to_int, rank_to_int


@total_ordering
class Summoner:
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

    def __eq__(self, other):
        return (
            isinstance(other, Summoner)
            and self.tier.upper() == other.tier.upper()
            and self.rank.upper() == other.rank.upper()
            and self.lp == other.lp
        )

    def __lt__(self, other):
        if not isinstance(other, Summoner):
            raise Exception("Not a Summoner object")
        if tier_to_int(self) < tier_to_int(other):
            return True
        if rank_to_int(self) < rank_to_int(other):
            return True
        if self.lp < other.lp:
            return True
        return False

    @staticmethod
    def last_summoner(db, name="Thelmkon"):
        val = db.query("SELECT * FROM dome ORDER BY created_at DESC LIMIT 1;")
        if val:
            return Summoner(_tier=val[0][2], _rank=val[0][1], _lp=val[0][0])
        return Summoner(None, None, None)

    @staticmethod
    def four_ago_summoner(db, name="Thelmkon"):
        val = db.query("SELECT * FROM dome ORDER BY created_at DESC LIMIT 4;")
        if val:
            return Summoner(_tier=val[3][2], _rank=val[3][1], _lp=val[3][0])
        return Summoner(None, None, None)
