def tier_to_int(summoner):
    if summoner.tier.upper() == "IRON":
        return 0
    if summoner.tier.upper() == "BRONZE":
        return 1
    if summoner.tier.upper() == "SILVER":
        return 2
    if summoner.tier.upper() == "GOLD":
        return 3
    if summoner.tier.upper() == "PLATINUM":
        return 4
    if summoner.tier.upper() == "DIAMOND":
        return 5
    if summoner.tier.upper() == "MASTER":
        return 6
    if summoner.tier.upper() == "GRANDMASTER":
        return 7
    if summoner.tier.upper() == "CHALLENGER":
        return 8


def rank_to_int(summoner):
    if summoner.rank.upper() == "IV":
        return 0
    if summoner.rank.upper() == "III":
        return 1
    if summoner.rank.upper() == "II":
        return 2
    if summoner.rank.upper() == "I":
        return 3


def absolute_value(summoner):
    return tier_to_int(summoner) * 1000 + rank_to_int(summoner) * 100 + summoner.lp


def trend(current, old):
    delta = (absolute_value(current) - absolute_value(old)) // 5
    trending = f"averaging {delta} lp over the last 5 games,"
    if delta < 0:
        threshold = (absolute_value(current) // 100) * 100
        buffer = absolute_value(current) - threshold
        if buffer // delta * -1 + 1 < 5:
            return (
                trending
                + f" projected {buffer // delta*-1 +1} game(s) until demotion :scream:"
            )
    if delta > 0:
        threshold = (absolute_value(current) // 100 + 1) * 100
        buffer = threshold - absolute_value(current)
        if buffer // delta + 1 < 5:
            return (
                trending
                + f" projected {buffer // delta +1} game(s) until promotion :+1::muscle:"
            )
    return trending + " stabilizing."
