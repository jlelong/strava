from stravadb import (readconfig, updatedb)

config = readconfig.read_config('setup.ini')
updatedb.update_bikes(config)
