from __future__ import print_function

import stravalib.client
import stravalib.model
import stravalib.unit_helper
import sqlalchemy

from backend.constants import ActivityTypes
from backend.utils import get_location
from backend.models import Base, Activity, Gear

def set_sport_type_for_ride(activity: type[Activity], gearType: str):
    if activity.sport_type is not None:
        return
    if gearType == ActivityTypes.MTB:
        activity.sport_type = 'MountainBikeRide'
    elif gearType == ActivityTypes.GRAVEL:
        activity.sport_type = 'GravelRide'
    elif gearType == ActivityTypes.ROAD:
        activity.sport_type = 'Ride'


def set_sport_type_for_run(activity: type[Activity], trailThreshold: int):
    if activity.sport_type is not None:
        return
    if activity.elevation > trailThreshold:
        activity.sport_type = 'TrailRun'


class StravaRequest:
    """
    Request the Strava API
    """
    activityTypes = ActivityTypes()

    def __init__(self, config, token):
        """
        Initialize the StravaRequest class.

        Create a connection to the mysql server and prepare the dialog with the Strava api

        :param config: a dictionary as returned by readconfig.read_config

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

    def get_points(self, activity: stravalib.model.SummaryActivity):
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

    def get_description(self, activity: stravalib.model.SummaryActivity):
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

    def __init__(self, config, athlete_id):
        """
        Initialize the StravaView class.

        Create a connection to the mysql server and prepare the dialog with the Strava api

        :param config:  a dictionary as returned by readconfig.read_config

        :param athlete: the strava id of the athlete logged in
        """
        self.athlete_id = athlete_id
        user = config['mysql_user']
        passwd = config['mysql_password']
        base = config['mysql_base']
        self.db_uri = f'mysql+pymysql://{user}:{passwd}@localhost/{base}?charset=utf8mb4'
        db_engine = sqlalchemy.create_engine(self.db_uri)
        # Create the table if they do not exist
        Base.metadata.create_all(db_engine)
        self.session: sqlalchemy.orm.Session = sqlalchemy.orm.sessionmaker(bind=db_engine)()


    def close(self):
        self.session.close()

    def update_gears(self, stravaRequest: StravaRequest):
        """
        Update the gears table with bikes and shoes

        :param stravaRequest: an instance of StravaRequest to send requests to the Strava API
        """
        onlineGears = list(stravaRequest.athlete.bikes)
        onlineGears.extend(list(stravaRequest.athlete.shoes))

        for bike in stravaRequest.athlete.bikes:
            desc = stravaRequest.client.get_gear(bike.id)
            old_bike = self.session.query(Gear).filter_by(id=bike.id).first()
            if old_bike is not None:
                old_bike.name = desc.name
                old_bike.frame_type = desc.frame_type
                old_bike.type = ActivityTypes.FRAME_TYPES[desc.frame_type]
                old_bike.retired = False
            else:
                new_bike = Gear(name=desc.name, id=desc.id, type=ActivityTypes.FRAME_TYPES[desc.frame_type], frame_type=desc.frame_type, athlete=self.athlete_id)
                self.session.add(new_bike)
            self.session.commit()

        for shoes in stravaRequest.athlete.shoes:
            desc = stravaRequest.client.get_gear(shoes.id)
            old_shoes = self.session.query(Gear).filter_by(id=shoes.id).first()
            if old_shoes is not None:
                old_shoes.name = desc.name
                old_shoes.type = ActivityTypes.RUN
                old_shoes.retired = False
            else:
                new_shoes = Gear(name=desc.name, id=desc.id, type=ActivityTypes.RUN, athlete=self.athlete_id)
                self.session.add(new_shoes)
            self.session.commit()

        activeGearIds = [gear.id for gear in onlineGears]
        self.session.query(Gear).filter(Gear.athlete == self.athlete_id).filter(Gear.id.notin_(activeGearIds)).update({Gear.retired: True})
        # for localGear in localGears:
        #     if localGear.id in activeGearIds:
        #         localGear.retired = False
        #     else:
        #         localGear.retired = True
        self.session.commit()


    def push_activity(self, activity: stravalib.model.SummaryActivity):
        """
        Add the activity `activity` to the activities table

        :param activity: an object of class:`stravalib.model.DetailedActivity`
        """
        # Check if activity is already in the table
        old_activity = self.session.query(Activity).filter_by(id=activity.id).first()
        if old_activity is not None:
            old_activity.name = activity.name
            old_activity.gear_id = activity.gear_id
            old_activity.commute = activity.commute
            old_activity.type = activity.type
            old_activity.sport_type = activity.sport_type
            if activity.total_elevation_gain is not None:
                elevation = f"{stravalib.unit_helper.meters(activity.total_elevation_gain).magnitude:.0f}"
                old_activity.elevation = elevation
            self.session.commit()
            print(f"Activity {activity.name.encode('utf-8')} was already in the local db. Updated.")
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

        # Get the real values
        athlete_id = activity.athlete.id
        if activity.distance is not None:
            distance = f"{stravalib.unit_helper.kilometers(activity.distance).magnitude:.2f}"
        if activity.total_elevation_gain is not None:
            elevation = f"{stravalib.unit_helper.meters(activity.total_elevation_gain).magnitude:.0f}"
        date = activity.start_date_local
        moving_time = activity.moving_time
        elapsed_time = activity.elapsed_time
        gear_id = activity.gear_id
        if activity.average_speed is not None:
            average_speed = f"{stravalib.unit_helper.kilometers_per_hour(activity.average_speed).magnitude:.1f}"
        if activity.average_heartrate is not None:
            average_heartrate = f"{activity.average_heartrate:.0f}"
            max_heartrate = activity.max_heartrate
            if activity.suffer_score is not None:
                suffer_score = activity.suffer_score
        if activity.calories is not None:
            calories = activity.calories
        commute = int(activity.commute)
        activity_type = activity.type
        sport_type = activity.sport_type

        new_activity = Activity(id=activity.id, athlete=athlete_id, name=activity.name, distance=distance, elevation=elevation, date=date, moving_time=moving_time, elapsed_time=elapsed_time, gear_id=gear_id, average_speed=average_speed, average_heartrate=average_heartrate, max_heartrate=max_heartrate, suffer_score=suffer_score, commute=commute, type=activity_type, sport_type=sport_type, red_points=red_points, calories=calories)
        self.session.add(new_activity)
        self.session.commit()

    def update_activity_extra_fields(self, activity: stravalib.model.SummaryActivity, stravaRequest: StravaRequest):
        """
        Update a given activity already in the local db

        :param activity: a Strava activity

        :param stravaRequest: an instance of StravaRequest to send requests to the Strava API
        """
        old_activity = self.session.query(Activity).filter_by(id=activity.id).first()
        # Drop activity if they are not already in DB
        if old_activity is None:
            return
        red_points = old_activity.red_points
        suffer_score = old_activity.suffer_score
        # if location is None or location == "":
        location = get_location(activity.start_latlng)
        if red_points == 0 and suffer_score > 0:
            red_points = stravaRequest.get_points(activity)
        description = stravaRequest.get_description(activity)

        old_activity.red_points = red_points
        old_activity.location = location
        old_activity.description = description
        self.session.commit()
        print(f"Update the description, points and location of activity {activity.id}.")

    def update_activity(self, activity: stravalib.model.SummaryActivity, stravaRequest: StravaRequest):
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
        self.session.query(Activity).filter_by(id=activity_id).delete()
        self.session.commit()
        print("Activity deleted")

    def update_activities(self, stravaRequest: StravaRequest):
        """
        Fetch new activities and push into the local db.

        :param stravaRequest: an instance of StravaRequest to send requests to the Strava API
        """
        # Get the most recent activity
        last_activity = self.session.query(Activity.date).filter_by(athlete=self.athlete_id)\
            .order_by(Activity.date.desc()).first()
        if last_activity is not None:
            after = last_activity.date
        else:
            after = None
        new_activities = stravaRequest.client.get_activities(after=after)
        list_ids = []
        for activity in new_activities:
            self.push_activity(activity)
            print(f"{activity.id} - {activity.name.encode('utf-8')}")
            list_ids.append(activity.id)
        for activity in new_activities:
            self.update_activity_extra_fields(activity, stravaRequest)
        return list_ids

    def rebuild_activities(self, stravaRequest: StravaRequest):
        """
        Get the whole list of activities from Strava and updates the local db accordingly.
        The activities already in the local db are updated if needed.

        :param stravaRequest: an instance of StravaRequest to send requests to the Strava API
        """
        all_activities = stravaRequest.client.get_activities()
        for activity in all_activities:
            self.push_activity(activity)
            print(f"{activity.id} - {activity.name.encode('utf-8')}")
        for activity in all_activities:
            self.update_activity_extra_fields(activity, stravaRequest)


    def fix_sport_type_all_activities(self, stravaRequest: StravaRequest, trailThreshold: int = 200):
        """
        Set sport_type for all activities in the local db.

        For a long time, only `type` was set by Strava. A few years ago, new types appeared 'TrailRun', 'GravelRide', 'MountainBikeRide', ... The new field `sport_type` supersets the old value `type`, which will be removed soon.

        :param stravaRequest: an instance of StravaRequest to send requests to the Strava API

        :param trailThreshold: all run activities with more elevation than `trailThreshold` are considered as trail running.
        """
        all_strava_activities = stravaRequest.client.get_activities()
        for strava_activity in all_strava_activities:
            local_activity = self.session.query(Activity, Gear.type).outerjoin(Gear, Gear.id == Activity.gear_id).filter(Activity.id == strava_activity.id).first()
            if local_activity is None:
                continue
            if local_activity[0].sport_type is None:
                if strava_activity.sport_type.root == 'Ride':
                    set_sport_type_for_ride(local_activity[0], local_activity[1])
                elif strava_activity.sport_type.root == 'Run':
                    set_sport_type_for_run(local_activity[0], trailThreshold)
                # set_sport_type_for_{ride,run} may not set sport_type, so we have to test local_activity[0].sport_type again
                if local_activity[0].sport_type is None:
                    local_activity[0].sport_type = strava_activity.sport_type.root
                print(f'Setting sport_type to {local_activity[0].sport_type} for activity {local_activity[0].id}')
            self.session.commit()

    def get_activities(self, before=None, after=None, name: str | None =None, sport_type =None, list_ids: list[int] | int | None =None):
        """
        Get all the activities matching the criterions

        :param before: lower-bound on the date of the activity
        :type before: str or datetime.date or datetime.datetime

        :param after: upper-bound on the date of the activity
        :type after: str or datetime.date or datetime.datetime

        :param name: a substring of the activity name
        :type name: str

        :param sport_type: ActivityTypes.SPORT_TYPES. May be None

        :param list_ids: a list of activities ids
        :type list_ids: a list or an integer
        """
        query = self.session.query(Activity, Gear.name) \
            .outerjoin(Gear, Gear.id == Activity.gear_id) \
            .filter(Activity.athlete == self.athlete_id)
        if before is not None:
            query = query.filter(Activity.date <= before)
        if after is not None:
            query = query.filter(Activity.date >= after)
        if name is not None:
            query = query.filter(Activity.name.contains(name))
        if sport_type is not None:
            query = query.filter(Activity.sport_type == sport_type)
        if list_ids is not None and isinstance(list_ids, int):
            list_ids = [list_ids]
        if list_ids is not None:
            query = query.filter(Activity.id.in_(list_ids))
        out = []
        for row in query.order_by(Activity.date.desc()).all():
            ans = row[0].to_json()
            out.append(ans)
        return out


    def get_gears(self):
        """
        Return the jsonified list of gears
        """
        gears = self.session.query(Gear).filter(Gear.athlete == self.athlete_id).all()
        return [g.to_json() for g in gears]

