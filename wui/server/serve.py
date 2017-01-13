import os
import os.path
import sys
import cherrypy


ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), '..')
py_level_dir = os.path.join(ROOT_DIR, '..')
sys.path.append(py_level_dir)
from readconfig import read_config
from stravaview.stravadb import Strava


class StravaView(object):
    def __init__(self, rootdir):
        self.rootdir = rootdir
        self.config = read_config(os.path.join(py_level_dir, 'setup.ini'))

    @cherrypy.expose
    def index(self):
        """
        Default is to Load index.html.
        """
        return open(os.path.join(self.rootdir, 'index.html'))

    @cherrypy.expose
    def getRuns(self):
        """
        Ajax query /getRuns to extract data from the database
        """
        strava_instance = Strava(self.config)
        ans = strava_instance.get_activities(json_output=True)
        strava_instance.close()
        # Cherrypy has a decorator to return a JSON object but as the get_activities method
        # already return a JSON object, we cannot rely on it.
        cherrypy.response.headers["Content-Type"] = "application/json"
        return ans

    @cherrypy.expose
    def updatelocaldb(self):
        """
        Ajax query /updatelocaldb to update the database
        """
        strava_instance = Strava(self.config)
        strava_instance.create_gears_table()
        strava_instance.update_bikes()
        strava_instance.update_shoes()
        strava_instance.create_activities_table()
        strava_instance.update_activities()
        strava_instance.close()


if __name__ == '__main__':
    conf = {
        '/': {
            # 'tools.sessions.on': True,
            'tools.staticdir.on': True,
            'tools.staticdir.root': ROOT_DIR,
            'tools.staticdir.dir': '',
        }
    }

print(conf['/'])

cherrypy.quickstart(StravaView(ROOT_DIR), '/', conf)
