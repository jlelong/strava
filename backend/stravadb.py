#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import stravalib.client
import stravalib.model
import stravalib.unithelper
import pymysql.cursors
import pymysql.converters
import sqlalchemy

from backend.constants import ActivityTypes
from backend.utils import get_location
from backend.models import Base


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
            if not zones:
                return 0
            for z in zones:
                if z.type == 'heartrate':
                    return z.points
        except:
            return 0
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

    def __init__(self, config, athlete_id, Gear, Activity):
        """
        Initialize the StravaView class.

        Create a connection to the mysql server and prepare the dialog with the Strava api

        :param config:  a dictionnary as returned by readconfig.read_config

        :param athlete: the strava id of the athlete logged in
        """
        self.db_uri = 'mysql+pymysql://{user}:{passwd}@localhost/{base}'.format(user=config['mysql_user'], passwd=config['mysql_password'], base=config['mysql_base'])
        db_engine = sqlalchemy.create_engine(self.db_uri)
        self.Gear = Gear
        self.Activity = Activity
        # Create the table if they do not exist
        Base.metadata.create_all(db_engine)
        self.session: sqlalchemy.orm.Session = sqlalchemy.orm.sessionmaker(bind=db_engine)()

        self.connection = None
        self.cursor = None
        self.activities_table = None
        self.gears_table = None
        self.athlete_id = athlete_id

    def close(self):
        self.session.close()

    def update_gears(self, stravaRequest: StravaRequest):
        """
        Update the gears table with bikes and shoes

        :param stravaRequest: an instance of StravaRequest to send requests to the Strava API
        """
        gears = list(stravaRequest.athlete.bikes)
        gears.extend(list(stravaRequest.athlete.shoes))

        for bike in stravaRequest.athlete.bikes:
            desc = stravaRequest.client.get_gear(bike.id)
            new_bike = self.Gear(name=desc.name, id=desc.id, type=self.activityTypes.FRAME_TYPES[desc.frame_type], frame_type=desc.frame_type)
            old_bike = self.session.query(self.Gear).filter_by(id=bike.id).first()
            if old_bike is not None:
                old_bike = new_bike
            else:
                self.session.add(new_bike)
            self.session.commit()

        for shoe in stravaRequest.athlete.shoes:
            desc = stravaRequest.client.get_gear(shoe.id)
            new_shoe = self.Gear(name=desc.name, id=desc.id, type=self.activityTypes.RUN)
            old_shoe = self.session.query(self.Gear).filter_by(id=shoe.id).first()
            if old_shoe is not None:
                old_shoe = new_shoe
            else:
                self.session.add(new_shoe)
            self.session.commit()

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
                sql = "UPDATE {} SET name=%s, type=%s, frame_type=%s where id=%s".format(self.gears_table)
                self.cursor.execute(sql, (desc.name, self.activityTypes.FRAME_TYPES[desc.frame_type], desc.frame_type, desc.id))
            else:
                sql = "INSERT INTO {} (id, name, type, frame_type) VALUES (%s, %s, %s, %s)".format(self.gears_table)
                self.cursor.execute(sql, (desc.id, desc.name, self.activityTypes.FRAME_TYPES[desc.frame_type], desc.frame_type))
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
                sql = "UPDATE {} SET name=%s where id=%s".format(self.gears_table)
                self.cursor.execute(sql, (desc.name, desc.id))
            else:
                sql = "INSERT INTO {} (id, name, type) VALUES (%s, %s, %s)".format(self.gears_table)
                self.cursor.execute(sql, (desc.id, desc.name, self.activityTypes.RUN))
            self.connection.commit()

    def push_activity(self, activity):
        """
        Add the activity `activity` to the activities table

        :param activity: an object of class:`stravalib.model.Activity`
        """
        # Check if activity is already in the table
        sql = "SELECT name, elevation, gear_id, commute FROM {} WHERE id=%s LIMIT 1".format(self.activities_table)
        if (self.cursor.execute(sql, activity.id) > 0):
            entry = self.cursor.fetchone()
            if entry['name'] != activity.name:
                sql = "UPDATE {} SET name=%s where id=%s".format(self.activities_table)
                self.cursor.execute(sql, (activity.name, activity.id))
            if entry['gear_id'] != activity.gear_id:
                sql = "UPDATE {} SET gear_id=%s where id=%s".format(self.activities_table)
                self.cursor.execute(sql, (activity.gear_id, activity.id))
            if entry['commute'] != activity.commute:
                sql = "UPDATE {} SET commute=%s where id=%s".format(self.activities_table)
                self.cursor.execute(sql, (activity.commute, activity.id))
            if activity.total_elevation_gain is not None:
                elevation = "%0.0f" % stravalib.unithelper.meters(activity.total_elevation_gain).get_num()
                if entry['elevation'] != elevation:
                    sql = "UPDATE {} SET elevation=%s where id=%s".format(self.activities_table)
                    self.cursor.execute(sql, (elevation, activity.id))
            self.connection.commit()
            print("Activity '{}' was already in the local db. Updated.".format(activity.name.encode('utf-8')))
            return

        if (activity.type not in self.activityTypes.ACTIVITY_TYPES):
            print("Activity '%s' is not a ride nor a run" % (activity.name.encode('utf-8')))
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
        moving_time = format_timedelta(activity.moving_time)
        elapsed_time = format_timedelta(activity.elapsed_time)
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

    def update_activity_extra_fields(self, activity, stravaRequest):
        """
        Update a given activity already in the local db

        :param activity: a Strava activity

        :param stravaRequest: an instance of StravaRequest to send requests to the Strava API
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
        new_location = get_location(activity.start_latlng)
        if red_points == 0 and suffer_score > 0:
            new_red_points = stravaRequest.get_points(activity)
        new_description = stravaRequest.get_description(activity)
        if (new_location != location or new_description != description or new_red_points != red_points):
            sql = "UPDATE {} SET location=%s, description=%s, red_points=%s where id=%s".format(self.activities_table)
            self.cursor.execute(sql, (new_location, new_description, new_red_points, activity.id))
            self.connection.commit()
        print("Update the description, points and location of activity {} ".format(activity.id))

    def update_activity(self, activity, stravaRequest):
        """
        Update a given activity already in the local db

        :param activity: a Strava activity

        :param stravaRequest: an instance of StravaRequest to send requests to the Strava API

        :param geolocator:
        """
        self.push_activity(activity)
        self.update_activity_extra_fields(activity, stravaRequest)

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
        list_ids = []
        for activity in new_activities:
            self.push_activity(activity)
            print("{} - {}".format(activity.id, activity.name.encode('utf-8')))
            list_ids.append(activity.id)
        for activity in new_activities:
            self.update_activity_extra_fields(activity, stravaRequest)
        return list_ids

    def rebuild_activities(self, stravaRequest):
        """
        Get the whole list of activities from Strava and updates the local db accordingly.
        The activities already in the local db are updated if needed.

        :param stravaRequest: an instance of StravaRequest to send requests to the Strava API
        """
        all_activities = stravaRequest.client.get_activities()
        for activity in all_activities:
            self.push_activity(activity)
            print("{} - {}".format(activity.id, activity.name.encode('utf-8')))
        for activity in all_activities:
            self.update_activity_extra_fields(activity, stravaRequest)

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
        print("{7}: {1} | {2} | {3} | {4} | {5} | {6} | https://www.strava.com/activities/{0}".format(identifier, name, date, distance, elevation, moving_time, elapsed_time, bike_type))

    def get_activities(self, before=None, after=None, name=None, activity_type=None, list_ids=None):
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

        :param list_ids: a list of activities ids
        :type list_ids: a list or an integer
        """
        # sql = """SELECT a.id, a.name, a.location, DATE(a.date) AS date, a.distance, a.elevation,
        # a.average_speed, a.elapsed_time, a.moving_time, a.suffer_score, a.red_points, a.calories,
        # a.max_heartrate, a.average_heartrate, a.description, a.commute, a.type as activity_type,
        # IF(a.type='Ride', b.type, NULL) bike_type, b.name AS gear_name
        # FROM %s AS a LEFT JOIN %s AS b ON a.gear_id = b.id
        # """ % (self.activities_table, self.gears_table)

        query = self.session.query(self.Activity, self.Gear.name, self.Gear.type) \
            .outerjoin(self.Gear, self.Gear.id == self.Activity.gear_id) \
            .filter(self.Activity.athlete == self.athlete_id)
        if before is not None:
            query = query.filter(self.Activity.date <= before)
        if after is not None:
            query = query.filter(self.Activity.date >= after)
        if name is not None:
            query = query.filter(self.Activity.name.contains(name))
        if activity_type is not None:
            # We consider FRAME_TYPES as activities on their owns.
            if not (activity_type in self.activityTypes.ACTIVITY_TYPES):
                print("{0} is not a valid activity. Use {1}".format(activity_type, ", ".join(self.activityTypes.ACTIVITY_TYPES)))
                activity_type = None
            else:
                if activity_type in (self.activityTypes.HIKE, self.activityTypes.RUN, self.activityTypes.RIDE):
                    query = query.filter(self.Activity.type == activity_type)
                else:
                    query = query.filter(self.Gear.type == activity_type)
        if list_ids is not None and isinstance(list_ids, int):
            list_ids = [list_ids]
        if list_ids is not None:
            query = query.filter(self.Activity.id.in_(list_ids))
        out = []
        for row in query.order_by(self.Activity.date.desc()).all():
            ans = row[0].to_json()
            ans['gear_name'] = row[1]
            ans['bike_type'] = row[2] if ans['activity_type'] == self.activityTypes.RIDE else ''
            out.append(ans)
        return out


    def get_gears(self):
        """
        Return the jsonified list of gears
        """
        # sql = "SHOW TABLES LIKE %s"
        # if (self.cursor.execute(sql, self.gears_table) == 0):
        # sql = """SELECT name, type FROM %s""" % (self.gears_table)
        # self.cursor.execute(sql)
        # return json.dumps(self.cursor.fetchall(), cls=ExtendedEncoder)
        gears = self.session.query(self.Gear).all()
        return [g.to_json() for g in gears]

