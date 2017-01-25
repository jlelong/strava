import os
import os.path
import sys
import cherrypy
import stravalib
import json

ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), '..')
SESSION_DIR = '/tmp/MyStrava'
py_level_dir = os.path.join(ROOT_DIR, '..')
sys.path.append(py_level_dir)
from readconfig import read_config
from stravaview.stravadb import StravaClient
from stravaview.stravadb import StravaView


class StravaUI(object):
    COOKIE_NAME = "MyStrava_AthleteID"
    ATHLETE_ID = 'athlete'
    TOKEN = 'token'
    DUMMY = 'dummy'  # Used to keep session alive by writing data.

    def __init__(self, rootdir):
        self.rootdir = rootdir
        self.config = read_config(os.path.join(py_level_dir, 'setup.ini'))

    @cherrypy.expose
    def index(self):
        """
        Default is to Load index.html.
        """
        # Keep session alive
        cherrypy.session[self.DUMMY] = 'MyStrava'
        return open(os.path.join(self.rootdir, 'index.html'))

    @cherrypy.expose
    def getRuns(self):
        """
        Ajax query /getRuns to extract data from the database
        """
        # Keep session alive
        cherrypy.session[self.DUMMY] = 'MyStravaGetRuns'
        if cherrypy.session.get(self.ATHLETE_ID) is None:
            activities = json.dumps(None)
        else:
            view = StravaView(self.config, cherrypy.session.get(self.ATHLETE_ID))
            activities = view.get_activities(json_output=True)
            view.close()
        # Cherrypy has a decorator to return a JSON object but as the get_activities method
        # already return a JSON object, we cannot rely on it.
        cherrypy.response.headers["Content-Type"] = "application/json"
        return activities

    @cherrypy.expose
    def updatelocaldb(self):
        """
        Ajax query /updatelocaldb to update the database
        """
        view = StravaView(self.config, cherrypy.session.get(self.ATHLETE_ID))
        view.create_gears_table()
        view.create_activities_table()
        view.close()
        stravaInstance = StravaClient(self.config, cherrypy.session.get(self.TOKEN))
        stravaInstance.update_bikes()
        stravaInstance.update_shoes()
        stravaInstance.update_activities()
        stravaInstance.close()

    @cherrypy.expose
    def connect(self):
        """
        Connect to Strava and grant authentification.
        """
        # Keep session alive
        print "connect - {}".format(cherrypy.session.id)
        cherrypy.session[self.DUMMY] = 'MyStravaConnect'
        client = stravalib.Client()
        url = client.authorization_url(
            client_id=self.config['client_id'], scope='view_private',
            redirect_uri='http://127.0.0.1:{}/authorize'.format(cherrypy.server.socket_port))
        raise cherrypy.HTTPRedirect(url)

    @cherrypy.expose
    def authorize(self, state=None, code=None):
        """
        Echange code for a token and set token and athlete_id in the current session

        :param state: the state variable passed to Strava authentification url and returned here.
        We do not use it, so it is always None but we have to keep it in the argument list
        as it is part of the url.

        :param code: the code returned by Strava authentification to be
        further exchanged for a token.
        """
        print cherrypy.request.cookie['session_id']
        print "authorization - {}".format(cherrypy.session.id)
        # Keep session alive
        cherrypy.session[self.DUMMY] = 'MyStravaAuthorized'
        client = stravalib.Client()
        token = client.exchange_code_for_token(client_id=self.config['client_id'],
                                               client_secret=self.config['client_secret'],
                                               code=code)
        cherrypy.session[self.TOKEN] = token
        client = stravalib.Client(access_token=token)
        cherrypy.session[self.ATHLETE_ID] = client.get_athlete().id
        print "athlete: {}".format(cherrypy.session.get(self.ATHLETE_ID))
        print "token: {}".format(cherrypy.session.get(self.TOKEN))
        raise cherrypy.HTTPRedirect('/')


if __name__ == '__main__':
    if not os.path.exists(SESSION_DIR):
        os.mkdir(SESSION_DIR)
    conf = {
        '/': {
            'tools.sessions.on': True,
            'tools.sessions.storage_class': cherrypy.lib.sessions.FileSession,
            'tools.sessions.storage_path': SESSION_DIR,
            'tools.sessions.timeout': 60 * 24 * 30,  # 1 month
            'tools.staticdir.on': True,
            'tools.staticdir.root': ROOT_DIR,
            'tools.staticdir.dir': '',
            'tools.response_headers.on': True,
        },
    }

print(conf['/'])
cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8080})
cherrypy.quickstart(StravaUI(ROOT_DIR), '/', conf)
