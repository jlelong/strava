import ssl
import certifi
from geopy.geocoders import Nominatim, options as geooptions
from geopy.exc import GeopyError

def get_location(cords):
    """
    Return the city or village along with the department number corresponding
    to a pair of (latitude, longitude) coordinates

    :param cords: a pair of (latitude, longitude) coordinates
    :type cords: a list or a tuple
    """
    if cords is None:
        return None
    max_attempts = 4
    attempts = 0
    ctx = ssl.create_default_context(cafile=certifi.where())
    geooptions.default_ssl_context = ctx
    geolocator = Nominatim(user_agent="StravaView")
    while True:
        try:
            location = geolocator.reverse((cords.lat, cords.lon))
            if location.raw is None:
                return None
            location_dict = location.raw['address']
            city = ""
            code = ""
            for key in ('village', 'hamlet', 'city', 'town', 'state'):
                if key in location_dict:
                    city = location_dict[key]
                    break
            if location_dict['country'] == 'France' and 'postcode' in location_dict:
                code = ' (' + location_dict['postcode'][0:2] + ')'
            return city + code
        except GeopyError as e:
            attempts += 1
            if attempts > max_attempts:
                print(f"Error getting reverse location for {cords.lat},{cords.lon}", e)
                return ""
