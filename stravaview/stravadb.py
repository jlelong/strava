#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import stravalib.client
import stravalib.model
import stravalib.unithelper
import pymysql.cursors
import pymysql.converters
import json
import datetime
import itertools
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut


def _format_timedelta(t):
    """
    Turn a timedelta object into a string representation "hh:mm:ss" with a resolution of one second.

    :param t: a timedelta object
    """
    if (t is not None):
        assert(isinstance(t, datetime.timedelta))
        seconds = int(t.total_seconds())
        (hours, mins) = divmod(seconds, 3600)
        (minutes, seconds) = divmod(mins, 60)
        return "{0}:{1:02d}:{2:02d}".format(hours, minutes, seconds)
    else:
        return ""


def _get_location(cords, geolocator):
    """
    Return the city or village along with the department number corresponding
    to a pair of (latitude, longitude) coordinates

    :param cords: a pair of (latitude, longitude) coordinates
    :type cords: a list or a tuple

    :param geolocator: an instance of a geocoder capable of reverse locating
    """
    if cords is None:
        return None
    max_attempts = 4
    attempts = 0
    while True:
        try:
            location = geolocator.reverse(cords)
            if location.raw is None or 'address' not in location.raw:
                return None
            address = location.raw['address']
            city = ""
            code = ""
            for key in ('hamlet', 'village', 'city', 'town', 'state'):
                if key in address:
                    city = address[key]
                    break
            if address['country'] == 'France' and 'postcode' in address:
                code = ' (' + address['postcode'][0:2] + ')'
            return city + code
        except GeocoderTimedOut:
            attempts += 1
            if attempts > max_attempts:
                break


class ExtendedEncoder(json.JSONEncoder):
    """
    Extend the JSON encoding facilities from datetime objects
    """
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return "%s" % obj
        elif isinstance(obj, datetime.timedelta):
            return _format_timedelta(obj)
        else:
            return json.JSONEncoder.default(self, obj)


class ActivityTypes:
    """
    This class acts as a dictionnary of the possible activity types
    """
    CX = 'CX'
    TT = 'TT'
    MTB = 'MTB'
    ROAD = 'Road'
    RIDE = stravalib.model.Activity.RIDE
    HIKE = stravalib.model.Activity.HIKE
    RUN = stravalib.model.Activity.RUN
    FRAME_TYPES = {0: "", 1: MTB, 3: ROAD, 2: CX, 4: TT}
    ACTIVITY_TYPES = {HIKE, RUN, RIDE, ROAD, MTB, CX, TT}


class StravaRequest:
    """
    Request the Strava API
    """
    activityTypes = ActivityTypes()

    def __init__(self, config, token):
        """
        Initialize the StravaRequest class.

        Create a connection to the mysql server and prepare the dialog with the Strava api

        :param config: a dictionnary as returned by readconfig.read_config

        :param token: an access token returned by Strava, must be at list view_private.
        """
        self.token = token
        self.client = stravalib.Client(access_token=token)
        self.with_points = config['with_points']
        self.with_description = config['with_description']
        self.client_id = config['client_id']
        self.client_secret = config['client_secret']
        try:
            self.athlete = self.client.get_athlete()
            self.athlete_id = self.athlete.id
            self.athlete_profile = self.athlete.profile_medium
        except:
            self.athlete = None
            self.athlete_id = 0
            self.athlete_profile = ""

    def get_points(self, activity):
        """
        Request the points for an activity

        :param activity: a Strava activity
        :type activity: Activity
        """

        if ((not self.with_points) or (activity.suffer_score is None)):
            return 0
        try:
            zones = activity.zones
            if len(zones) == 0:
                return 0
            for z in zones:
                if z.type == 'heartrate':
                    return z.points
        except:
            return 0

    def get_description(self, activity):
        """
        Request the description of an activity

        :param activity: a Strava activity
        :type activity: Activity
        """
        if not self.with_description:
            return None
        detailed_activity = self.client.get_activity(activity.id)
        description = detailed_activity.description
        return description


class StravaView:
    """
    Interact with the local database containing gears and activities.
    """
    activityTypes = ActivityTypes()

    def __init__(self, config, athlete_id):
        """
        Initialize the StravaView class.

        Create a connection to the mysql server and prepare the dialog with the Strava api

        :param config:  a dictionnary as returned by readconfig.read_config

        :param athlete: the strava id of the athlete logged in
        """
        self.connection = pymysql.connect(host='localhost', user=config['mysql_user'], password=config['mysql_password'], db=config['mysql_base'], charset='utf8')
        self.cursor = self.connection.cursor(pymysql.cursors.DictCursor)
        self.activities_table = config['mysql_activities_table']
        self.gears_table = config['mysql_bikes_table']
        self.athlete_id = athlete_id

    def close(self):
        self.cursor.close()
        self.connection.close()

    def create_gears_table(self):
        """
        Create the gears table if it does not already exist
        """
        # Check if table already exists
        sql = "SHOW TABLES LIKE %s"
        if (self.cursor.execute(sql, self.gears_table) > 0):
            print("The table '%s' already exists" % self.gears_table)
            return

        sql = """CREATE TABLE {} (
        id varchar(45) NOT NULL,
        name varchar(256) DEFAULT NULL,
        type enum(%s,%s,%s,%s,%s,%s) DEFAULT NULL,
        frame_type int(11) DEFAULT 0,
        PRIMARY KEY (id),
        UNIQUE KEY strid_UNIQUE (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8""".format(self.gears_table)
        self.cursor.execute(sql, (self.activityTypes.HIKE, self.activityTypes.RUN, self.activityTypes.ROAD, self.activityTypes.MTB, self.activityTypes.CX, self.activityTypes.TT))
        self.connection.commit()

    def create_activities_table(self):
        """
        Create the activities table if it does not already exist
        """
        # Check if table already exists
        sql = "SHOW TABLES LIKE %s"
        if (self.cursor.execute(sql, self.activities_table) > 0):
            print("The table '%s' already exists" % self.activities_table)
            return

        sql = """CREATE TABLE {} (
        id int(11) NOT NULL,
        athlete int(11) DEFAULT 0,
        name varchar(256) DEFAULT NULL,
        location varchar(256) DEFAULT NULL,
        date datetime DEFAULT NULL,
        distance float DEFAULT 0,
        elevation float DEFAULT 0,
        moving_time time DEFAULT 0,
        elapsed_time time DEFAULT 0,
        gear_id varchar(45) DEFAULT NULL,
        average_speed float DEFAULT 0,
        max_heartrate int DEFAULT 0,
        average_heartrate float DEFAULT 0,
        suffer_score int DEFAULT 0,
        red_points int DEFAULT 0,
        description text DEFAULT NULL,
        commute tinyint(1) DEFAULT 0,
        calories float DEFAULT 0,
        type enum(%s, %s, %s) DEFAULT NULL,
        PRIMARY KEY (id),
        UNIQUE KEY strid_UNIQUE (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8""".format(self.activities_table)
        self.cursor.execute(sql, (self.activityTypes.RIDE, self.activityTypes.RUN, self.activityTypes.HIKE))
        self.connection.commit()

    def update_bikes(self, stravaRequest):
        """
        Update the gears table with bikes

        :param stravaRequest: an instance of StravaRequest to send requests to the Strava API
        """
        # Connect to the database
        bikes = stravaRequest.athlete.bikes
        for bike in bikes:
            desc = stravaRequest.client.get_gear(bike.id)

            # Check if the gear already exists
            sql = "SELECT * FROM %s WHERE id='%s' LIMIT 1" % (self.gears_table, bike.id)
            if (self.cursor.execute(sql) > 0):
                continue

            sql = "INSERT INTO %s (id, name, type, frame_type) VALUES ('%s','%s', '%s', '%d')" % (
                self.gears_table, desc.id, desc.name, self.activityTypes.FRAME_TYPES[desc.frame_type], desc.frame_type)
            self.cursor.execute(sql)
            self.connection.commit()

    def update_shoes(self, stravaRequest):
        """
        Update the gears table with shoes

        :param stravaRequest: an instance of StravaRequest to send requests to the Strava API
        """
        # Connect to the database
        shoes = stravaRequest.athlete.shoes
        for shoe in shoes:
            desc = stravaRequest.client.get_gear(shoe.id)

            # Check if the gear already exists
            sql = "SELECT * FROM %s WHERE id='%s' LIMIT 1" % (self.gears_table, shoe.id)
            if (self.cursor.execute(sql) > 0):
                continue

            sql = "INSERT INTO %s (id, name, type) VALUES ('%s','%s', '%s')" % (self.gears_table, desc.id, desc.name, self.activityTypes.RUN)
            self.cursor.execute(sql)
            self.connection.commit()

    def push_activity(self, activity):
        """
        Add the activity `activity` to the activities table

        :param activity: an object of class:`stravalib.model.Activity`
        """
        # Check if activity is already in the table
        sql = "SELECT name, gear_id FROM {} WHERE id=%s LIMIT 1".format(self.activities_table)
        if (self.cursor.execute(sql, activity.id) > 0):
            entry = self.cursor.fetchone()
            if entry['name'] != activity.name:
                sql = "UPDATE {} SET name=%s where id=%s".format(self.activities_table)
                self.cursor.execute(sql, (activity.name, activity.id))
                self.connection.commit()
            if entry['gear_id'] != activity.gear_id:
                sql = "UPDATE {} SET gear_id=%s where id=%s".format(self.activities_table)
                self.cursor.execute(sql, (activity.gear_id, activity.id))
                self.connection.commit()
            print("Activity '{}' was already in the local db. Updated.".format(activity.name.encode('utf-8')))
            return

        if (activity.type != activity.RIDE and activity.type != activity.RUN and activity.type != activity.HIKE):
            print("Activity '%s' is not a ride nor a run" % (activity.name))
            return

        # Default values
        distance = 0
        elevation = 0
        average_heartrate = 0
        average_speed = 0
        max_heartrate = 0
        suffer_score = 0
        red_points = 0
        calories = 0
        location = None
        description = None

        # Get the real values
        name = activity.name
        athlete_id = activity.athlete.id
        if activity.distance is not None:
            distance = "%0.2f" % stravalib.unithelper.kilometers(activity.distance).get_num()
        if activity.total_elevation_gain is not None:
            elevation = "%0.0f" % stravalib.unithelper.meters(activity.total_elevation_gain).get_num()
        date = activity.start_date_local
        moving_time = _format_timedelta(activity.moving_time)
        elapsed_time = _format_timedelta(activity.elapsed_time)
        gear_id = activity.gear_id
        if activity.average_speed is not None:
            average_speed = "%0.1f" % stravalib.unithelper.kilometers_per_hour(activity.average_speed).get_num()
        if activity.average_heartrate is not None:
            average_heartrate = "%0.0f" % activity.average_heartrate
            max_heartrate = activity.max_heartrate
            if activity.suffer_score is not None:
                suffer_score = activity.suffer_score
        if activity.calories is not None:
            calories = activity.calories
        commute = int(activity.commute)
        activity_type = activity.type

        sql = """INSERT INTO {} (id, athlete, name, distance, elevation, date, location, moving_time,
        elapsed_time, gear_id, average_speed, average_heartrate, max_heartrate, suffer_score,
        description, commute, type, red_points, calories) VALUES (%s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """.format(self.activities_table)
        self.cursor.execute(sql, (activity.id, athlete_id, name, distance, elevation, date, location,
                                  moving_time, elapsed_time, gear_id, average_speed, average_heartrate, max_heartrate,
                                  suffer_score, description, commute, activity_type, red_points, calories))
        self.connection.commit()

    def update_activity_extra_fields(self, activity, stravaRequest, geolocator=None):
        """
        Update a given activity already in the local db

        :param activity: a Strava activity

        :param stravaRequest: an instance of StravaRequest to send requests to the Strava API

        :param geolocator:
        """
        sql = "SELECT location, description, red_points, suffer_score FROM {} WHERE id=%s".format(self.activities_table)
        self.cursor.execute(sql, activity.id)
        self.connection.commit()
        entry = self.cursor.fetchone()
        # Drop activities which are not rides or runs.
        if entry is None:
            return
        location = entry.get('location')
        red_points = entry.get('red_points')
        suffer_score = entry.get('suffer_score')
        description = entry.get('description')
        new_location = location
        new_description = description
        new_red_points = red_points
        # if location is None or location == "":
        new_location = _get_location(activity.start_latlng, geolocator)
        if red_points == 0 and suffer_score > 0:
            new_red_points = stravaRequest.get_points(activity)
        new_description = stravaRequest.get_description(activity)
        if (new_location != location or new_description != description or new_red_points != red_points):
            sql = "UPDATE {} SET location=%s, description=%s, red_points=%s where id=%s".format(self.activities_table)
            self.cursor.execute(sql, (new_location, new_description, new_red_points, activity.id))
            self.connection.commit()
        print("Update the description, points and location of activity {} ".format(activity.id))

    def update_activity(self, activity, stravaRequest, geolocator=None):
        """
        Update a given activity already in the local db

        :param activity: a Strava activity

        :param stravaRequest: an instance of StravaRequest to send requests to the Strava API

        :param geolocator:
        """
        self.push_activity(activity)
        if geolocator is None:
            geolocator = Nominatim()
        self.update_activity_extra_fields(activity, stravaRequest, geolocator)

    def delete_activity(self, activity_id):
        """
        Delete a given activity from the local db

        :param activity_id: the id of an activity.
        """
        if activity_id is None:
            return
        sql = "DELETE FROM {} WHERE id=%s".format(self.activities_table)
        self.cursor.execute(sql, activity_id)
        self.connection.commit()
        print("Activity deleted")

    def update_activities(self, stravaRequest):
        """
        Fetch new activities and push into the local db.

        :param stravaRequest: an instance of StravaRequest to send requests to the Strava API
        """
        # Get the most recent activity
        sql = "SELECT date FROM {} WHERE athlete = %s ORDER BY date DESC LIMIT 1".format(self.activities_table)
        if (self.cursor.execute(sql, (self.athlete_id)) == 0):
            after = None
        else:
            after = self.cursor.fetchone()['date']
        new_activities = stravaRequest.client.get_activities(after=after)
        geolocator = Nominatim()
        list_ids = []
        for activity in new_activities:
            self.push_activity(activity)
            print("{} - {}".format(activity.id, activity.name.encode('utf-8')))
            list_ids.append(activity.id)
        for activity in new_activities:
            self.update_activity_extra_fields(activity, stravaRequest, geolocator)
        return list_ids

    def rebuild_activities(self, stravaRequest):
        """
        Get the whole list of activities from Strava and updates the local db accordingly.
        The activities already in the local db are updated if needed.

        :param stravaRequest: an instance of StravaRequest to send requests to the Strava API
        """
        all_activities = stravaRequest.client.get_activities()
        geolocator = Nominatim()
        for activity in all_activities:
            self.push_activity(activity)
            print("{} - {}".format(activity.id, activity.name.encode('utf-8')))
        for activity in all_activities:
            self.update_activity_extra_fields(activity, stravaRequest, geolocator)

    def print_row(self, row):
        """
        Print a row retrieved from the activities table

        :param row: a result from a SQL fetch function
        :type row: a dictionnary
        """
        name = row['name'].encode('utf-8')
        identifier = row['id']
        date = row['date']
        distance = row['distance']
        elevation = row['elevation']
        elapsed_time = row['elapsed_time']
        moving_time = row['moving_time']
        bike_type = row['bike_type']
        print ("{7}: {1} | {2} | {3} | {4} | {5} | {6} | https://www.strava.com/activities/{0}".format(identifier, name, date, distance, elevation, moving_time, elapsed_time, bike_type))

    def get_activities(self, before=None, after=None, name=None, activity_type=None, json_output=False):
        """
        Get all the activities matching the criterions

        :param before: lower-bound on the date of the activity
        :type before: str or datetime.date or datetime.datetime

        :param after: upper-bound on the date of the activity
        :type after: str or datetime.date or datetime.datetime

        :param name: a substring of the activity name
        :type name: str

        :param activity_type: the type of activity. Can be 'Walk', 'Run', 'Ride', 'Road', 'MTB', 'CX', 'TT'.
        :type activity_type: str

        :param json_output: do we return a JSON encoded result of the query
        :type json_output: bool
        """
        # Return if activity table does not exist
        sql = "SHOW TABLES LIKE %s"
        if (self.cursor.execute(sql, self.activities_table) == 0):
            return json.dumps([])

        before_sql = ""
        after_sql = ""
        name_sql = ""
        conds = list()
        conds.append("athlete = '%s'" % self.athlete_id)
        if before is not None:
            before_sql = "a.date <= '%s'" % before
            conds.append(before_sql)

        if after is not None:
            after_sql = "a.date >= '%s'" % after
            conds.append(after_sql)

        if name is not None:
            name_sql = "a.name LIKE '%%%s%%'" % name
            conds.append(name_sql)

        if activity_type is not None:
            # We consider FRAME_TYPES as activities on their owns.
            if not (activity_type in self.activityTypes.ACTIVITY_TYPES):
                print("{0} is not a valid activity. Use {1}".format(activity_type, ", ".join(self.activityTypes.ACTIVITY_TYPES)))
                activity_type = None
            else:
                if activity_type in (self.activityTypes.HIKE, self.activityTypes.RUN, self.activityTypes.RIDE):
                    activity_type_sql = "a.type = '%s'" % activity_type
                else:
                    activity_type_sql = "b.type = '%s'" % activity_type
                conds.append(activity_type_sql)

        sql = """SELECT a.id, a.name, a.location, DATE(a.date) AS date, a.distance, a.elevation,
        a.average_speed, a.elapsed_time, a.moving_time, a.suffer_score, a.red_points, a.calories,
        a.max_heartrate, a.average_heartrate, a.description, a.commute, a.type as activity_type,
        IF(a.type='Ride', b.type, NULL) bike_type, b.name AS equipment_name
        FROM %s AS a LEFT JOIN %s AS b ON a.gear_id = b.id
        """ % (self.activities_table, self.gears_table)
        if len(conds) > 0:
            where = " AND ".join(conds)
            sql = sql + " WHERE " + where
        sql = sql + " ORDER BY date DESC"
        # print(sql + "\n")
        self.cursor.execute(sql)
        if json_output:
            return json.dumps(self.cursor.fetchall(), cls=ExtendedEncoder)
        else:
            for row in self.cursor.fetchall():
                self.print_row(row)

    def get_list_activities(self, list_ids):
        """
        Return the jsonified data corresponding to the activities with ids in list_ids

        :param list_ids: a list of activities ids
        """
        # Return if activity table does not exist
        sql = "SHOW TABLES LIKE %s"
        if (self.cursor.execute(sql, self.activities_table) == 0):
            return json.dumps([])
        # Make sure we ot a list of ids
        if isinstance(list_ids, int):
            list_ids = [list_ids]
        if len(list_ids) == 0:
            return json.dumps([])

        sql = """SELECT a.id, a.name, a.location, DATE(a.date) AS date, a.distance, a.elevation,
        a.average_speed, a.elapsed_time, a.moving_time, a.suffer_score, a.red_points, a.calories,
        a.max_heartrate, a.average_heartrate, a.description, a.commute, a.type as activity_type,
        IF(a.type='Ride', b.type, NULL) AS bike_type, b.name AS equipment_name
        FROM %s AS a LEFT JOIN %s AS b ON a.gear_id = b.id
        """ % (self.activities_table, self.gears_table)

        in_ph = ', '.join(itertools.repeat('%s', len(list_ids)))
        sql = sql + " WHERE a.athlete=%s AND a.id IN (" + in_ph + ")"
        sql_args = []
        sql_args.append(self.athlete_id)
        sql_args.extend(list_ids)
        self.cursor.execute(sql, sql_args)
        return json.dumps(self.cursor.fetchall(), cls=ExtendedEncoder)
