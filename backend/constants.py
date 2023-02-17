import stravalib.model

class ActivityTypes:
    """
    This class acts as a dictionary of the possible activity types
    """
    CX = 'CX'
    TT = 'TT'
    MTB = 'MTB'
    ROAD = 'Road'
    GRAVEL = 'Gravel'
    RIDE = stravalib.model.Activity.RIDE
    HIKE = stravalib.model.Activity.HIKE
    RUN = stravalib.model.Activity.RUN
    NORDICSKI = stravalib.model.Activity.NORDICSKI
    FRAME_TYPES = {0: "", 1: MTB, 3: ROAD, 2: CX, 4: TT, 5: GRAVEL}
    ACTIVITY_TYPES = {HIKE, RUN, RIDE, ROAD, MTB, CX, TT, NORDICSKI}
