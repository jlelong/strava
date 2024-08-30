import typing
from stravalib import model

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
    ACTIVITY_TYPES = typing.get_args(model.RelaxedActivityType.model_fields['root'].annotation)
    SPORT_TYPES = typing.get_args(model.RelaxedSportType.model_fields['root'].annotation)

