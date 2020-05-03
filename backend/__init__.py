import sys
import os
from backend.readconfig import read_config

app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
config = read_config(os.path.join(app_dir, 'setup.ini'))
