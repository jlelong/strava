#!/usr/local/bin/python

# Compute the path of stravaview
import os
import sys
script_path = os.path.abspath(sys.argv[0])
script_dir = os.path.dirname(script_path)
py_level = os.path.join(script_dir, '..', '..')
sys.path.append(py_level)


from readconfig import read_config
from stravaview.stravadb import Strava

config = read_config(os.path.join(py_level, 'setup.ini'))
strava_instance = Strava(config)
strava_instance.update_bikes()
strava_instance.update_activities()
strava_instance.close()
print('Content-type: text/plain\n\n')
