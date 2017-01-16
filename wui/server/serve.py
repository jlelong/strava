import os
import os.path
import sys
import cherrypy
import stravalib
import json

ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), '..')
py_level_dir = os.path.join(ROOT_DIR, '..')
sys.path.append(py_level_dir)
from readconfig import read_config
from stravaview.stravadb import Strava


class StravaView(object):
    token = None  # Access token for strava

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
        if self.token is None:
            activities = json.dumps(None)
        else:
            strava_instance = Strava(self.config, self.token)
            activities = strava_instance.get_activities(json_output=True)
            strava_instance.close()
        # Cherrypy has a decorator to return a JSON object but as the get_activities method
        # already return a JSON object, we cannot rely on it.
        cherrypy.response.headers["Content-Type"] = "application/json"
        return activities

    @cherrypy.expose
    def updatelocaldb(self):
        """
        Ajax query /updatelocaldb to update the database
        """
        strava_instance = Strava(self.config, self.token)
        strava_instance.create_gears_table()
        strava_instance.update_bikes()
        strava_instance.update_shoes()
        strava_instance.create_activities_table()
        strava_instance.update_activities()
        strava_instance.close()

    @cherrypy.expose
    def connect(self):
        """
        Connect to Strava and get the token
        """
        client = stravalib.Client()
        url = client.authorization_url(client_id=self.config['client_id'], scope='view_private',
                                       redirect_uri='http://127.0.0.1:{}/authorization'.format(cherrypy.server.socket_port))
        raise cherrypy.HTTPRedirect(url)

    @cherrypy.expose
    def authorization(self, state=None, code=None):
        client = stravalib.Client()
        self.token = client.exchange_code_for_token(client_id=self.config['client_id'],
                                                    client_secret=self.config['client_secret'],
                                                    code=code)
        print "token: {}".format(self.token)
        raise cherrypy.HTTPRedirect('/')


if __name__ == '__main__':
    conf = {
        '/': {
            'tools.staticdir.on': True,
            'tools.staticdir.root': ROOT_DIR,
            'tools.staticdir.dir': '',
            'tools.response_headers.on': True,
        },
    }

print(conf['/'])
cherrypy.config.update({'server.socket_port': 8080})
cherrypy.quickstart(StravaView(ROOT_DIR), '/', conf)
