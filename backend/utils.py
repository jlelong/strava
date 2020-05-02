import datetime
import geocoder

def format_timedelta(t):
    """
    Turn a timedelta object into a string representation "hh:mm:ss" with a resolution of one second.

    :param t: a timedelta object
    """
    if (t is not None):
        assert(isinstance(t, datetime.timedelta))
        seconds = int(t.total_seconds())
        (hours, mins) = divmod(seconds, 3600)
        (minutes, seconds) = divmod(mins, 60)
        return "{0}:{1:02d}:{2:02d}".format(hours, minutes, seconds)
    return ""


def get_location(cords):
    """
    Return the city or village along with the department number corresponding
    to a pair of (latitude, longitude) coordinates

    :param cords: a pair of (latitude, longitude) coordinates
    :type cords: a list or a tuple

    :param geolocator: an instance of a geocoder capable of reverse locating
    """
    if cords is None:
        return None
    max_attempts = 4
    attempts = 0
    while True:
        try:
            # location = geolocator.reverse(cords)
            location = geocoder.osm("{lat},{lon}".format(lat=cords.lat, lon=cords.lon))
            if location.json is None:
                return None
            location_dict = location.json
            city = ""
            code = ""
            for key in ('hamlet', 'village', 'city', 'town', 'state'):
                if key in location_dict:
                    city = location_dict[key]
                    break
            if location_dict['country'] == 'France' and 'postal' in location_dict:
                code = ' (' + location_dict['postal'][0:2] + ')'
            return city + code
        except:
            attempts += 1
            if attempts > max_attempts:
                break
