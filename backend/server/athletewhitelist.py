# List of authorized athletes
ATHLETE_WHITELIST = ()


def get_athlete_whitelist():
    """
    Return the content of ATHLETE_WHITELIST as a list
    """
    if isinstance(ATHLETE_WHITELIST, tuple):
        return ATHLETE_WHITELIST
    else:
        return tuple([ATHLETE_WHITELIST])


def isauthorized(id):
    """
    Return True if the athlete_id id is authorized to use the application

    :param id: a Strava athlete_id
    """
    # Empty list
    if not ATHLETE_WHITELIST:
        return True
    if id in get_athlete_whitelist():
        return True
    return False
