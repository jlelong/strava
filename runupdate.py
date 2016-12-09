from readconfig import read_config
from stravaview.stravadb import Strava

config = read_config('setup.ini')
strava_instance = Strava(config)
strava_instance.create_bikes_table()
strava_instance.update_bikes()
