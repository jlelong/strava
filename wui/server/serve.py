import os
import os.path
import sys
import cherrypy
import stravalib
import json
import requests
import time

WUI_DIR = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), '..')
SESSION_DIR = '/tmp/MyStrava'
APP_TOPLEVEL_DIR = os.path.join(WUI_DIR, '..')
sys.path.append(APP_TOPLEVEL_DIR)
from readconfig import read_config
from stravaview.stravadb import StravaRequest
from stravaview.stravadb import StravaView
import athletewhitelist


class StravaUI(object):
    COOKIE_NAME = "MyStrava_AthleteID"
    ATHLETE_ID = 'athlete'
    ATHLETE_IS_PREMIUM = "is_premium"
    ACCESS_TOKEN = 'access_token'
    DUMMY = 'dummy'  # Used to keep session alive by writing data.
    REFRESH_TOKEN = 'refresh_token'
    EXPIRES_AT = 'deadline'

    def __init__(self, rootdir):
        self.rootdir = rootdir
        self.config = read_config(os.path.join(APP_TOPLEVEL_DIR, 'setup.ini'))

    def _getOrRefreshToken(self):
        """
        Check/Update for short-lived token
        """
        response = cherrypy.session[self.ACCESS_TOKEN]
        if time.time() > cherrypy.session[self.EXPIRES_AT]:
            client = stravalib.Client(access_token=response)
            new_auth_response = client.refresh_access_token(client_id=self.config['client_id'], client_secret=self.config['client_secret'], refresh_token=cherrypy.session[self.REFRESH_TOKEN])
            cherrypy.session[self.ACCESS_TOKEN] = new_auth_response['access_token']
            cherrypy.session[self.REFRESH_TOKEN] = new_auth_response['refresh_token']
            cherrypy.session[self.EXPIRES_AT] = new_auth_response['expires_at']
            response = new_auth_response['access_token']

        return response

    @cherrypy.expose
    def index(self):
        """
        Default is to Load index.html.
        """
        # Keep session alive
        cherrypy.session[self.DUMMY] = 'MyStrava'
        athlete_id = cherrypy.session.get(self.ATHLETE_ID)
        if athlete_id is not None and cherrypy.session.get(self.ACCESS_TOKEN) is not None:
            if not athletewhitelist.isauthorized(athlete_id):
                return open(os.path.join(self.rootdir, 'forbid.html'))
            cookie = cherrypy.response.cookie
            athlete_is_premium = cherrypy.session.get(self.ATHLETE_IS_PREMIUM)
            if athlete_is_premium is None:
                athlete_is_premium = 0
            cookie['connected'] = 1
            cookie['is_premium'] = int(athlete_is_premium)
        else:
            self.disconnect()

        #cookie = cherrypy.request.cookie
        #print("SESSION ID : {}".format(cookie['session_id'].value))
        #print("ACCESS TOKEN : {}".format(cherrypy.session.get(self.ACCESS_TOKEN)))
        #print("REFRESH TOKEN : {}".format(cherrypy.session.get(self.REFRESH_TOKEN)))
        #print("EXPIRES_AT : {}".format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(cherrypy.session.get(self.EXPIRES_AT)))))
        return open(os.path.join(self.rootdir, 'index.html'))

    @cherrypy.expose
    def disconnect(self):
        cookie = cherrypy.response.cookie
        cookie['connected'] = 0
        cookie['connected']['expires'] = 0
        cherrypy.session[self.ATHLETE_ID] = None
        cherrypy.session[self.ACCESS_TOKEN] = None
        cookie['session_id'] = 0
        cookie['session_id']['expires'] = 0
        cookie['is_premium'] = 0
        cookie['is_premium']['expires'] = 0
        return open(os.path.join(self.rootdir, 'index.html'))

    @cherrypy.expose
    def getRuns(self):
        """
        Ajax query /getRuns to extract data from the database
        """
        # Keep session alive
        cherrypy.session[self.DUMMY] = 'MyStravaGetRuns'
        athlete_id = cherrypy.session.get(self.ATHLETE_ID)
        if athlete_id is None or not athletewhitelist.isauthorized(athlete_id):
            activities = json.dumps("")
        else:
            view = StravaView(self.config, cherrypy.session.get(self.ATHLETE_ID))
            activities = view.get_activities(json_output=True)
            view.close()
        # Cherrypy has a decorator to return a JSON object but as the get_activities method
        # already return a JSON object, we cannot rely on it.
        cherrypy.response.headers["Content-Type"] = "application/json"
        return activities.encode('utf8')

    @cherrypy.expose
    def getAthleteProfile(self):
        """
        Get the url of the profile picture.
        """
        cherrypy.session[self.DUMMY] = 'MyStravaGetRuns'
        cherrypy.response.headers["Content-Type"] = "text/html"
        stravaInstance = StravaRequest(self.config, self._getOrRefreshToken())
        profile = stravaInstance.athlete_profile
        return profile

    @cherrypy.expose
    def updateactivities(self):
        """
        Ajax query /updateactivities to update the activities database
        """
        cherrypy.session[self.DUMMY] = 'MyStravaUpdateActivities'
        view = StravaView(self.config, cherrypy.session.get(self.ATHLETE_ID))
        stravaRequest = StravaRequest(self.config, self._getOrRefreshToken())
        view.create_activities_table()
        list_ids = view.update_activities(stravaRequest)
        activities = view.get_list_activities(list_ids)
        view.close()
        cherrypy.response.headers["Content-Type"] = "application/json"
        return activities.encode('utf8')

    @cherrypy.expose
    def updategears(self):
        """
        Ajax query /updatelocaldb to update the database
        """
        view = StravaView(self.config, cherrypy.session.get(self.ATHLETE_ID))
        stravaRequest = StravaRequest(self.config, self._getOrRefreshToken())
        view.create_gears_table()
        view.update_bikes(stravaRequest)
        view.update_shoes(stravaRequest)
        view.close()

    @cherrypy.expose
    def rebuildactivities(self):
        """
        Ajax query /upgradelocaldb to upgrade the database
        """
        view = StravaView(self.config, cherrypy.session.get(self.ATHLETE_ID))
        stravaRequest = StravaRequest(self.config, self._getOrRefreshToken())
        view.create_activities_table()
        view.rebuild_activities(stravaRequest)
        view.close()

    @cherrypy.expose
    def updateactivity(self, id):
        """
        Ajax query /updateactivity to update a single activity from its id
        """
        cherrypy.session[self.DUMMY] = 'MyStravaUpdateActivity'
        view = StravaView(self.config, cherrypy.session.get(self.ATHLETE_ID))
        stravaRequest = StravaRequest(self.config, self._getOrRefreshToken())
        try:
            activity = stravaRequest.client.get_activity(id)
            view.update_activity(activity, stravaRequest)
            activity = view.get_list_activities((id,))
        except requests.exceptions.HTTPError:
            # Page not found. Probably a deleted activity.
            activity = ""
        view.close()
        cherrypy.response.headers["Content-Type"] = "application/json"
        return activity

    @cherrypy.expose
    def deleteactivity(self, id):
        """
        Ajax query /deleteactivity to delete a single activity using its id
        """
        cherrypy.session[self.DUMMY] = 'MyStravaDeleteActivity'
        view = StravaView(self.config, cherrypy.session.get(self.ATHLETE_ID))
        view.delete_activity(id)
        view.close()
        cherrypy.response.headers["Content-Type"] = "text/html"
        return "Activity deleted"

    @cherrypy.expose
    def connect(self):
        """
        Connect to Strava and grant authentification.
        """
        # Keep session alive
        print("Connect - Session ID : {}".format(cherrypy.session.id))
        cherrypy.session[self.DUMMY] = 'MyStravaConnect'
        client = stravalib.Client()
        redirect_url = cherrypy.url(path='/authorized', script_name='')
        #print(redirect_url)
        authentification_url = client.authorization_url(
            client_id=self.config['client_id'], scope=["read_all", "activity:read_all", "profile:read_all"], approval_prompt='auto',
            redirect_uri=redirect_url)
        print("Authentification_URL : {}".format(authentification_url))
        raise cherrypy.HTTPRedirect(authentification_url)

    @cherrypy.expose
    def authorized(self, scope=None, state=None, code=None):
        """
        Echange code for a token and set token and athlete_id in the current session

        :param scope: the scope variable passed to Strava authentification url and returned here.
        We do not use it, so it is always None but we have to keep it in the argument list
        as it is part of the url.

        :param state: the state variable passed to Strava authentification url and returned here.
        We do not use it, so it is always None but we have to keep it in the argument list
        as it is part of the url.

        :param code: the code returned by Strava authentification to be
        further exchanged for a token.
        """
        print(cherrypy.request.cookie['session_id'])
        print("authorization - {}".format(cherrypy.session.id))
        # Keep session alive
        cherrypy.session[self.DUMMY] = 'MyStravaAuthorized'
        client = stravalib.Client()
        auth_response = client.exchange_code_for_token(client_id=self.config['client_id'], client_secret=self.config['client_secret'], code=code)
        token = auth_response['access_token']
        refresh_token = auth_response['refresh_token']
        expires_at = auth_response['expires_at']

        cherrypy.session[self.ACCESS_TOKEN] = token
        cherrypy.session[self.REFRESH_TOKEN] = refresh_token
        cherrypy.session[self.EXPIRES_AT] = expires_at

        client = stravalib.Client(access_token=token)
        athlete = client.get_athlete()
        cherrypy.session[self.ATHLETE_ID] = athlete.id
        cherrypy.session[self.ATHLETE_IS_PREMIUM] = athlete.premium

        print("-------")
        print("athlete: {}".format(cherrypy.session.get(self.ATHLETE_ID)))
        print("token: {}".format(cherrypy.session.get(self.ACCESS_TOKEN)))
        print("refresh token: {}".format(cherrypy.session.get(self.REFRESH_TOKEN)))
        print("expires at: {}".format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(cherrypy.session.get(self.EXPIRES_AT)))))
        print("Session ID : {}".format(cherrypy.session.id))
        print("Access code : {}".format(code))
        print("-------")

        raise cherrypy.HTTPRedirect(cherrypy.url(path='/', script_name=''))


if __name__ == '__main__':
    if not os.path.exists(SESSION_DIR):
        os.mkdir(SESSION_DIR)
    conf = {
        '/': {
            # 'tools.proxy.on': True,
            # 'tools.proxy.base': 'http://localhost/mystrava',
            # 'tools.proxy.local': "",
            'tools.encode.text_only': False,
            'tools.sessions.on': True,
            'tools.sessions.storage_class': cherrypy.lib.sessions.FileSession,
            'tools.sessions.storage_path': SESSION_DIR,
            'tools.sessions.timeout': 60 * 24 * 30,  # 1 month
            'tools.staticdir.on': True,
            'tools.staticdir.root': WUI_DIR,
            'tools.staticdir.dir': '',
            'tools.response_headers.on': True,
            'log.access_file': "{0}/log/access.log".format(APP_TOPLEVEL_DIR),
            'log.error_file': "{0}/log/error.log".format(APP_TOPLEVEL_DIR),
        },
    }

print(conf['/'])
cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8080})
# cherrypy.quickstart(StravaUI(WUI_DIR), '/mystrava', conf)
cherrypy.quickstart(StravaUI(WUI_DIR), '/', conf)
