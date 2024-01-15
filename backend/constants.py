class ActivityTypes:
    """
    This class acts as a dictionary of the possible activity types
    """
    CX = 'CX'
    TT = 'TT'
    MTB = 'MTB'
    ROAD = 'Road'
    GRAVEL = 'Gravel'
    RIDE = 'Ride'
    HIKE = 'Hike'
    RUN = 'Run'
    NORDICSKI = 'NordicSki'
    FRAME_TYPES = {0: "", 1: MTB, 3: ROAD, 2: CX, 4: TT, 5: GRAVEL}
    ACTIVITY_TYPES = {HIKE, RUN, RIDE, ROAD, MTB, CX, TT, NORDICSKI}
