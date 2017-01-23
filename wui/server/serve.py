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

    def _set_session_cookie(self, id=None):
        """
        Set cookie session_id to id if not None and set its expiring date

        :param id: the id a the session to create or None to use the current session
        """
        if id is not None:
            cherrypy.response.cookie['session_id'] = id
        cherrypy.response.cookie['session_id']['max-age'] = 3600 * 24 * 30  # 1 month
        cherrypy.response.cookie['session_id']['expires'] = 3600 * 24 * 30  # 1 month

    @cherrypy.expose
    def index(self):
        """
        Default is to Load index.html.
        """
        # Keep session alive
        cherrypy.session[self.DUMMY] = 'MyStrava'
        self._set_session_cookie()
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
        cherrypy.session[self.DUMMY] = 'MyStravaConnect'
        client = stravalib.Client()
        # Make sure to pass the current session_id to withdraw it later when back to our app.
        url = client.authorization_url(
            client_id=self.config['client_id'], scope='view_private',
            state=cherrypy.session.id,
            redirect_uri='http://127.0.0.1:{}/authorization'.format(cherrypy.server.socket_port))
        print "connected to Strava - {}".format(cherrypy.session.id)
        raise cherrypy.HTTPRedirect(url)

    @cherrypy.expose
    def authorization(self, state=None, code=None):
        """
        Redirection url once Strava authentification granted.
        This is only a first step redirection to restore the session id before
        proceeding with token echange.

        :param state: the id of the current session in our app

        :param code: the code returned by Strava authentification to be
        further exchanged for a token.
        """
        # Restore the session_id
        self._set_session_cookie(state)
        raise cherrypy.HTTPRedirect('/authorized?code={}'.format(code))

    @cherrypy.expose
    def authorized(self, code=None):
        """
        Echange code for a token and set token and athlete_id in the current session

        :param code: the code returned by Strava authentification to be
        further exchanged for a token.
        """
        print "authorization - {}".format(cherrypy.session.id)
        cherrypy.session[self.DUMMY] = 'MyStravaAuthorized'
        client = stravalib.Client()
        token = client.exchange_code_for_token(client_id=self.config['client_id'],
                                               client_secret=self.config['client_secret'],
                                               code=code)
        cherrypy.session[self.TOKEN] = token
        client = stravalib.Client(access_token=token)
        cherrypy.session[self.ATHLETE_ID] = client.get_athlete().id
        # cookies = cherrypy.response.cookie
        # # expires = datetime.datetime.utcnow() + datetime.timedelta(days=30)
        # cookies[self.COOKIE_NAME] = cherrypy.session[self.ATHLETE_ID]
        # cookies[self.COOKIE_NAME]['max-age'] = 3600 * 24 * 30
        print "athlete: {}".format(cherrypy.session.get(self.ATHLETE_ID))
        print "token: {}".format(cherrypy.session.get(self.ATHLETE_ID))
        raise cherrypy.HTTPRedirect('/')


if __name__ == '__main__':
    conf = {
        '/': {
            'tools.sessions.on': True,
            'tools.staticdir.on': True,
            'tools.staticdir.root': ROOT_DIR,
            'tools.staticdir.dir': '',
            'tools.response_headers.on': True,
        },
    }

print(conf['/'])
cherrypy.config.update({'server.socket_port': 8080})
cherrypy.quickstart(StravaUI(ROOT_DIR), '/', conf)
