#!/usr/local/bin/python

# Make sure that Python interpreter referenced by the shebang line has access to stravalib


# Make sure to print this line first (ending with \n\n) to notify
# that the answer has JSON format.
print 'Content-type: application/json\n\n'

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
ans = strava_instance.get_activities(json_output=True)
strava_instance.close()

print ans
