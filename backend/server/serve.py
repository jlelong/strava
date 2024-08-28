# -*- coding: utf-8 -*-
import os
import os.path
import time
import cherrypy
import stravalib
import requests

from backend.stravadb import StravaRequest, StravaView


class StravaUI:
    COOKIE_NAME = "MyStrava_AthleteID"
    ATHLETE_ID = 'athlete'
    ATHLETE_IS_PREMIUM = "is_premium"
    ACCESS_TOKEN = 'access_token'
    DUMMY = 'dummy'  # Used to keep session alive by writing data.
    REFRESH_TOKEN = 'refresh_token'
    EXPIRES_AT = 'deadline'

    def __init__(self, rootdir, config):
        self.rootdir = rootdir
        self.config = config
        self.athlete_whitelist = config['athlete_whitelist']

    def isAuthorized(self, athlete_id):
        """
        Return True if the athlete_id is authorized to use the application

        :param athlete_id: a Strava athlete_id
        """
        # Empty list
        if not self.athlete_whitelist:
            return True
        if athlete_id in self.athlete_whitelist:
            return True
        return False


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
            if not self.isAuthorized(athlete_id):
                return open(os.path.join(self.rootdir, 'forbid.html'), encoding='utf8')
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
        return open(os.path.join(self.rootdir, 'index.html'), encoding='utf8')

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
        return open(os.path.join(self.rootdir, 'index.html'), encoding='utf8')

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def getRuns(self):
        """
        Ajax query /getRuns to extract data from the database
        """
        # Keep session alive
        cherrypy.session[self.DUMMY] = 'MyStravaGetRuns'
        athlete_id = cherrypy.session.get(self.ATHLETE_ID)
        if athlete_id is None or not self.isAuthorized(athlete_id):
            activities = ""
        else:
            view = StravaView(self.config, cherrypy.session.get(self.ATHLETE_ID))
            activities = view.get_activities()
            view.close()
        return activities

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def getGears(self):
        """
        Ajax query /getGears to extract gears from the database
        """
        # Keep session alive
        cherrypy.session[self.DUMMY] = 'MyStravaGetGears'
        athlete_id = cherrypy.session.get(self.ATHLETE_ID)
        if athlete_id is None or not self.isAuthorized(athlete_id):
            gears = ""
        else:
            view = StravaView(self.config, cherrypy.session.get(self.ATHLETE_ID))
            gears = view.get_gears()
            view.close()
        return gears


    @cherrypy.expose
    def getAthleteProfile(self):
        """
        Get the url of the profile picture.
        """
        cherrypy.session[self.DUMMY] = 'MyStravaGetAthleteProfile'
        cherrypy.response.headers["Content-Type"] = "text/html"
        stravaInstance = StravaRequest(self.config, self._getOrRefreshToken())
        profile = stravaInstance.athlete_profile
        return profile

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def updateactivities(self):
        """
        Ajax query /updateactivities to update the activities database
        """
        cherrypy.session[self.DUMMY] = 'MyStravaUpdateActivities'
        view = StravaView(self.config, cherrypy.session.get(self.ATHLETE_ID))
        stravaRequest = StravaRequest(self.config, self._getOrRefreshToken())
        list_ids = view.update_activities(stravaRequest)
        activities = view.get_activities(list_ids=list_ids)
        view.close()
        return activities

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def updategears(self):
        """
        Ajax query /updatelocaldb to update the database
        """
        view = StravaView(self.config, cherrypy.session.get(self.ATHLETE_ID))
        stravaRequest = StravaRequest(self.config, self._getOrRefreshToken())
        view.update_gears(stravaRequest)
        gears = view.get_gears()
        view.close()
        return gears

    @cherrypy.expose
    def rebuildactivities(self):
        """
        Ajax query /upgradelocaldb to upgrade the database
        """
        view = StravaView(self.config, cherrypy.session.get(self.ATHLETE_ID))
        stravaRequest = StravaRequest(self.config, self._getOrRefreshToken())
        view.rebuild_activities(stravaRequest)
        view.close()

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def updateactivity(self, activity_id):
        """
        Ajax query /updateactivity to update a single activity from its id
        """
        cherrypy.session[self.DUMMY] = 'MyStravaUpdateActivity'
        view = StravaView(self.config, cherrypy.session.get(self.ATHLETE_ID))
        stravaRequest = StravaRequest(self.config, self._getOrRefreshToken())
        if isinstance(activity_id, str):
            activity_id = int(activity_id)
        try:
            activity = stravaRequest.client.get_activity(activity_id)
            view.update_activity(activity, stravaRequest)
            activity = view.get_activities(list_ids=activity_id)
        except requests.exceptions.HTTPError:
            # Page not found. Probably a deleted activity.
            activity = []
        view.close()
        return activity

    @cherrypy.expose
    def deleteactivity(self, activity_id):
        """
        Ajax query /deleteactivity to delete a single activity using its id
        """
        cherrypy.session[self.DUMMY] = 'MyStravaDeleteActivity'
        view = StravaView(self.config, cherrypy.session.get(self.ATHLETE_ID))
        view.delete_activity(activity_id)
        view.close()
        cherrypy.response.headers["Content-Type"] = "text/html"
        return "Activity deleted"

    @cherrypy.expose
    def connect(self):
        """
        Connect to Strava and grant authentification.
        """
        # Keep session alive
        print(f"Connect - Session ID : {cherrypy.session.id}")
        cherrypy.session[self.DUMMY] = 'MyStravaConnect'
        client = stravalib.Client()
        redirect_url = cherrypy.url(path='/authorized', script_name='')
        #print(redirect_url)
        authentification_url = client.authorization_url(
            client_id=self.config['client_id'], scope=["read_all", "activity:read_all", "profile:read_all"], approval_prompt='auto',
            redirect_uri=redirect_url)
        print(f"Authentification_URL : {authentification_url}")
        raise cherrypy.HTTPRedirect(authentification_url)

    @cherrypy.expose
    def authorized(self, scope=None, state=None, code=None):
        """
        Exchange code for a token and set token and athlete_id in the current session

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
        print(f"authorization - {cherrypy.session.id}")
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
        print(f"athlete: {cherrypy.session.get(self.ATHLETE_ID)}")
        print(f"token: {cherrypy.session.get(self.ACCESS_TOKEN)}")
        print(f"refresh token: {cherrypy.session.get(self.REFRESH_TOKEN)}")
        print(f"expires at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(cherrypy.session.get(self.EXPIRES_AT)))}")
        print(f"Session ID : {cherrypy.session.id}")
        print(f"Access code : {code}")
        print("-------")

        raise cherrypy.HTTPRedirect(cherrypy.url(path='/', script_name=''))

    @cherrypy.expose
    def updatesporttype(self,trail_seuil):
        stravaRequest = StravaRequest(self.config, self._getOrRefreshToken())
        view = StravaView(self.config, cherrypy.session.get(self.ATHLETE_ID))
        view.fix_sport_type_all_activities(stravaRequest, trail_seuil)
