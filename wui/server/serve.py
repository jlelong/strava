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
from stravaview.stravadb import StravaRequest
from stravaview.stravadb import StravaView
import athletewhitelist


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
        athlete_id = cherrypy.session.get(self.ATHLETE_ID)
        if athlete_id is not None and cherrypy.session.get(self.TOKEN) is not None:
            if not athletewhitelist.isauthorized(athlete_id):
                return open(os.path.join(self.rootdir, 'forbid.html'))
            cookie = cherrypy.response.cookie
            cookie['connected'] = 1
        else:
            self.disconnect()
        return open(os.path.join(self.rootdir, 'index.html'))

    @cherrypy.expose
    def disconnect(self):
        cookie = cherrypy.response.cookie
        cookie['connected'] = 0
        cookie['connected']['expires'] = 0
        cherrypy.session[self.ATHLETE_ID] = None
        cherrypy.session[self.TOKEN] = None
        return open(os.path.join(self.rootdir, 'index.html'))

    @cherrypy.expose
    def getRuns(self):
        """
        Ajax query /getRuns to extract data from the database
        """
        # Keep session alive
        cherrypy.session[self.DUMMY] = 'MyStravaGetRuns'
        athlete_id = cherrypy.session.get(self.ATHLETE_ID)
        if athlete_id is None:
            activities = json.dumps(None)
        else:
            if not athletewhitelist.isauthorized(athlete_id):
                return open(os.path.join(self.rootdir, 'forbid.html'))
            view = StravaView(self.config, cherrypy.session.get(self.ATHLETE_ID))
            activities = view.get_activities(json_output=True)
            view.close()
        # Cherrypy has a decorator to return a JSON object but as the get_activities method
        # already return a JSON object, we cannot rely on it.
        cherrypy.response.headers["Content-Type"] = "application/json"
        return activities

    @cherrypy.expose
    def getAthleteProfile(self):
        """
        Get the url of the profile picture.
        """
        cherrypy.session[self.DUMMY] = 'MyStravaGetRuns'
        cherrypy.response.headers["Content-Type"] = "text/html"
        stravaInstance = StravaRequest(self.config, cherrypy.session.get(self.TOKEN))
        profile = stravaInstance.athlete_profile
        return profile

    @cherrypy.expose
    def updatelocaldb(self):
        """
        Ajax query /updatelocaldb to update the database
        """
        view = StravaView(self.config, cherrypy.session.get(self.ATHLETE_ID))
        stravaRequest = StravaRequest(self.config, cherrypy.session.get(self.TOKEN))
        view.create_gears_table()
        view.create_activities_table()
        view.update_bikes(stravaRequest)
        view.update_shoes(stravaRequest)
        view.update_activities(stravaRequest)
        view.close()

    @cherrypy.expose
    def upgradelocaldb(self):
        """
        Ajax query /upgradelocaldb to upgrade the database
        """
        view = StravaView(self.config, cherrypy.session.get(self.ATHLETE_ID))
        stravaRequest = StravaRequest(self.config, cherrypy.session.get(self.TOKEN))
        view.create_gears_table()
        view.create_activities_table()
        view.update_bikes(stravaRequest)
        view.update_shoes(stravaRequest)
        stravaRequest.upgrade_activities()
        view.close()

    @cherrypy.expose
    def updateactivity(self, id):
        """
        Ajax query /updateactivity to update a single activity from its id
        """
        view = StravaView(self.config, cherrypy.session.get(self.ATHLETE_ID))
        stravaRequest = StravaRequest(self.config, cherrypy.session.get(self.TOKEN))
        activity = stravaRequest.client.get_activity(id)
        view.update_activity(activity, stravaRequest)
        view.close()

    @cherrypy.expose
    def connect(self):
        """
        Connect to Strava and grant authentification.
        """
        # Keep session alive
        print "connect - {}".format(cherrypy.session.id)
        cherrypy.session[self.DUMMY] = 'MyStravaConnect'
        client = stravalib.Client()
        redirect_url = cherrypy.url(path='/authorized', script_name='/')
        print redirect_url
        authentification_url = client.authorization_url(
            client_id=self.config['client_id'], scope='view_private',
            redirect_uri=redirect_url)
        print authentification_url
        raise cherrypy.HTTPRedirect(authentification_url)

    @cherrypy.expose
    def authorized(self, state=None, code=None):
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
        raise cherrypy.HTTPRedirect(cherrypy.url(path='/', script_name=''))


if __name__ == '__main__':
    if not os.path.exists(SESSION_DIR):
        os.mkdir(SESSION_DIR)
    conf = {
        '/': {
            # 'tools.proxy.on': True,
            # 'tools.proxy.base': 'http://localhost/mystrava',
            # 'tools.proxy.local': "",
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
# cherrypy.quickstart(StravaUI(ROOT_DIR), '/mystrava', conf)
cherrypy.quickstart(StravaUI(ROOT_DIR), '/', conf)
