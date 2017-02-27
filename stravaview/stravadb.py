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


# def _escape_string(s):
#     """
#     Escape a string unless is None
#
#     :param s: a basestring
#     """
#     if (s is not None):
#         assert(isinstance(s, basestring))
#         return pymysql.converters.escape_string(s)
#     else:
#         return ""

# Apparently, we do not need to escape strings when using the form
# .execute(query, (vars))
def _escape_string(s):
    return s


def _get_location(cords, geolocator):
    """
    Return the city or village along with the department number corresponding
    to a pair of (latitude, longitude) coordinates

    :param cords: a pair of (latitude, longitude) coordinates
    :type cords: a list or a tuple

    :param geolocator: an instance of a geocoder capable of reverse locating
    """
    location = geolocator.reverse(cords)
    if location.raw is None or 'address' not in location.raw:
        return None
    attempts = 0
    while True:
        try:
            address = location.raw['address']
            city = ""
            code = ""
            for key in ('hamlet', 'village', 'city_district', 'city', 'town'):
                if key in address:
                    city = address[key]
                    break
            if address['country'] == 'France' and 'postcode' in address:
                code = ' (' + address['postcode'][0:2] + ')'
            return city + code
        except GeocoderTimedOut:
            attempts += 1
            if attempts > 4:
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


class StravaClient:
    """
    Create a local Strava instance with its own local database containing only the funny rides (no commute).
    """
    activityTypes = ActivityTypes()

    def __init__(self, config, token):
        """
        Initialize the StravaView class.

        Create a connection to the mysql server and prepare the dialog with the Strava api

        :param config: a dictionnary as returned by readconfig.read_config

        :param token: an access token returned by Strava, must be at list view_private.
        """
        self.connection = pymysql.connect(host='localhost', user=config['mysql_user'], password=config['mysql_password'], db=config['mysql_base'], charset='utf8')
        self.cursor = self.connection.cursor(pymysql.cursors.DictCursor)
        self.token = token
        self.stravaClient = stravalib.Client(access_token=token)
        self.activities_table = config['mysql_activities_table']
        self.gears_table = config['mysql_bikes_table']
        self.with_points = config['with_points']
        self.client_id = config['client_id']
        self.client_secret = config['client_secret']
        self.athlete = self.stravaClient.get_athlete().id

    def close(self):
        self.cursor.close()
        self.connection.close()

    def update_bikes(self):
        """
        Update the bikes table
        """
        # Connect to the database
        bikes = self.stravaClient.get_athlete().bikes
        for bike in bikes:
            desc = self.stravaClient.get_gear(bike.id)

            # Check if the bike already exists
            sql = "SELECT * FROM %s WHERE id='%s' LIMIT 1" % (self.gears_table, bike.id)
            if (self.cursor.execute(sql) > 0):
                continue

            sql = "INSERT INTO %s (id, name, type, frame_type) VALUES ('%s','%s', '%s', '%d')" % (
                self.gears_table, desc.id, desc.name, self.activityTypes.FRAME_TYPES[desc.frame_type], desc.frame_type)
            self.cursor.execute(sql)
            self.connection.commit()

    def update_shoes(self):
        """
        Update the gears table with shoes
        """
        # Connect to the database
        shoes = self.stravaClient.get_athlete().shoes
        for shoe in shoes:
            desc = self.stravaClient.get_gear(shoe.id)

            # Check if the bike already exists
            sql = "SELECT * FROM %s WHERE id='%s' LIMIT 1" % (self.gears_table, shoe.id)
            if (self.cursor.execute(sql) > 0):
                continue

            sql = "INSERT INTO %s (id, name, type) VALUES ('%s','%s', '%s')" % (self.gears_table, desc.id, desc.name, self.activityTypes.RUN)
            self.cursor.execute(sql)
            self.connection.commit()

    def _get_points(self, activity):
        """
        Get the red points for an activity

        :param activity: a Strava activity
        :type activity: Activity
        """

        if ((not self.with_points) or (not activity.has_heartrate)):
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

    def push_activity(self, activity):
        """
        Add the activity `activity` to the activities table

        :param activity: an object of class:`stravalib.model.Activity`
        """
        # Check if activity is already in the table
        sql = "SELECT name FROM {} WHERE id=%s LIMIT 1".format(self.activities_table)
        if (self.cursor.execute(sql, activity.id) > 0):
            entry = self.cursor.fetchone()
            if entry['name'] != activity.name:
                sql = "UPDATE {} SET name=%s where id=%s".format(self.activities_table)
                self.cursor.execute(sql, (activity.name, activity.id))
                self.connection.commit()
                print("Activity '%s' already exists in table" % (activity.name))
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
        name = _escape_string(activity.name)
        athlete = activity.athlete.id
        if activity.distance is not None:
            distance = "%0.2f" % stravalib.unithelper.kilometers(activity.distance).get_num()
        if activity.total_elevation_gain is not None:
            elevation = "%0.0f" % stravalib.unithelper.meters(activity.total_elevation_gain).get_num()
        date = activity.start_date_local
        moving_time = _format_timedelta(activity.moving_time)
        elapsed_time = _format_timedelta(activity.elapsed_time)
        gear_id = _escape_string(activity.gear_id)
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
        self.cursor.execute(sql, (activity.id, athlete, name, distance, elevation, date, location,
                                  moving_time, elapsed_time, gear_id, average_speed, average_heartrate, max_heartrate,
                                  suffer_score, description, commute, activity_type, red_points, calories))
        self.connection.commit()

    def update_activity_location(self, activity, geolocator):
        """
        Update the location of an activity already in the db.

        :param activity: an object of class:`stravalib.model.Activity`

        :param an instance of a geocoder capable of reverse search
        """
        location = _get_location(activity.start_latlng, geolocator)
        sql = "UPDATE {} SET location=%s where id=%s".format(self.activities_table)
        self.cursor.execute(sql, (location, activity.id))
        self.connection.commit()

    def update_activity_description(self, activity):
        """
        Update the location of an activity already in the db.

        :param activity: an object of class:`stravalib.model.Activity`
        """
        detailed_activity = self.stravaClient.get_activity(activity.id)
        description = detailed_activity.description
        if description is not None and description != "":
            sql = "UPDATE {} SET description=%s where id=%s".format(self.activities_table)
            self.cursor.execute(sql, (description, activity.id))
            self.connection.commit()

    def update_activity_points(self, activity):
        """
        Update the location of an activity already in the db.

        :param activity: an object of class:`stravalib.model.Activity`
        """
        red_points = self._get_points(activity)
        if red_points != 0:
            sql = "UPDATE {} SET red_points=%s where id=%s".format(self.activities_table)
            self.cursor.execute(sql, (red_points, activity.id))
            self.connection.commit()

    def update_activities(self):
        """
        Update the activities table
        """
        # Get the most recent activity
        sql = "SELECT date FROM {} WHERE athlete = %s ORDER BY date DESC LIMIT 1".format(self.activities_table)
        if (self.cursor.execute(sql, (self.athlete)) == 0):
            after = None
        else:
            after = self.cursor.fetchone()['date']
        new_activities = self.stravaClient.get_activities(after=after)
        geolocator = Nominatim()
        for activity in new_activities:
            self.push_activity(activity)
            print("{} - {}".format(activity.id, activity.name.encode('utf-8')))
        for activity in new_activities:
            self.update_activity_location(activity, geolocator)
            print("Update the location of activity {} ".format(activity.id))
            self.update_activity_description(activity)
            print("Update the description of activity {} ".format(activity.id))
            self.update_activity_points(activity)
            print("Update the points of activity {} ".format(activity.id))

    def upgrade_activities(self):
        """
        Upgrade all the activities
        """
        all_activities = self.stravaClient.get_activities()
        geolocator = Nominatim()
        for activity in all_activities:
            self.push_activity(activity)
            print("{} - {}".format(activity.id, activity.name.encode('utf-8')))
        for activity in all_activities:
            sql = "SELECT location, description, red_points, suffer_score FROM {} WHERE id=%s".format(self.activities_table)
            self.cursor.execute(sql, activity.id)
            self.connection.commit()
            entry = self.cursor.fetchone()
            if entry is None:
                # This happens for activities which are not rides or runs and therefore are not stored in the local db.
                continue
            location = entry.get('location')
            red_points = entry.get('red_points')
            suffer_score = entry.get('suffer_score')
            if location is None or location == "":
                self.update_activity_location(activity, geolocator)
                print("Update the location of activity {} ".format(activity.id))
            if red_points == 0 and suffer_score > 0:
                self.update_activity_points(activity)
                print("Update the points of activity {} ".format(activity.id))
            self.update_activity_description(activity)
            print("Update the description of activity {} ".format(activity.id))


class StravaView:
    """
    Create a local Strava instance with its own local database containing only the funny rides (no commute).
    """
    activityTypes = ActivityTypes()

    def __init__(self, config, athlete):
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
        self.with_points = config['with_points']
        self.client_id = config['client_id']
        self.client_secret = config['client_secret']
        self.athlete = athlete

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
            return ""

        before_sql = ""
        after_sql = ""
        name_sql = ""
        conds = list()
        conds.append("athlete = '%s'" % self.athlete)
        if before is not None:
            before_sql = "a.date <= '%s'" % before
            conds.append(before_sql)

        if after is not None:
            after_sql = "a.date >= '%s'" % after
            conds.append(after_sql)

        if name is not None:
            name_sql = "a.name LIKE '%%%s%%'" % _escape_string(name)
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
        b.type AS bike_type, b.name AS bike_name FROM %s AS a LEFT JOIN %s AS b ON a.gear_id = b.id
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
