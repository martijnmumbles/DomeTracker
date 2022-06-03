from functools import total_ordering
from league import tier_to_int, rank_to_int


@total_ordering
class Summoner:
    tier = rank = lp = name = ""

    def __init__(self, _tier, _rank, _lp, _name):
        self.tier = _tier
        self.rank = _rank
        self.lp = _lp
        self.name = _name

    def save_to_db(self, db):
        db.insert(
            "INSERT INTO lp_record (tier, rank, lp, name) VALUES (%s, %s, %s, %s)",
            (self.tier, self.rank, self.lp, self.name),
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
    def last_record(db, name):
        val = db.query(
            "SELECT * FROM lp_record WHERE name = %s ORDER BY created_at DESC LIMIT 1",
            (name,),
        )
        if val:
            return Summoner(
                _tier=val[0][2], _rank=val[0][1], _lp=val[0][0], _name=val[0][4]
            )
        return None

    @staticmethod
    def four_ago(db, name):
        val = db.query(
            "SELECT * FROM lp_record WHERE name = %s ORDER BY created_at DESC LIMIT 4",
            (name,),
        )
        if len(val) > 3:
            return Summoner(
                _tier=val[3][2], _rank=val[3][1], _lp=val[3][0], _name=val[3][4]
            )
        return None

    @staticmethod
    def last_ten_summoner(db, name):
        val = db.query(
            "SELECT * FROM lp_record WHERE name = %s ORDER BY created_at DESC LIMIT 10",
            (name,),
        )
        return val
