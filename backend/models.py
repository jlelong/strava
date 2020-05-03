import sqlalchemy as db
from sqlalchemy.ext.declarative import declarative_base

from backend.constants import ActivityTypes

Base = declarative_base()

def make_gear_model(tablename):
    class Gear(Base):
        __tablename__ = tablename
        id = db.Column(db.String(45), primary_key=True)
        name = db.Column(db.String(256), nullable=True)
        type = db.Column(db.Enum(ActivityTypes.HIKE, ActivityTypes.RUN, ActivityTypes.ROAD, ActivityTypes.MTB, ActivityTypes.CX, ActivityTypes.TT), nullable=True)
        frame_type = db.Column(db.Integer, default=0)

        def to_json(self):
            return {
                "id": self.id,
                "name": self.name,
                "type": self.type,
                "frame_type": self.frame_type
            }

    return Gear

def make_activity_model(tablename):
    class Activity(Base):
        __tablename__ = tablename
        id = db.Column(db.BigInteger, primary_key=True)
        athlete = db.Column(db.Integer, default=0)
        name = db.Column(db.String(256), default='') # COLLATE utf8mb4_bin DEFAULT NULL,
        location = db.Column(db.String(256), default='')
        date = db.Column(db.DateTime, nullable=True)
        distance = db.Column(db.Float, default=0)
        elevation = db.Column(db.Float, default=0)
        moving_time = db.Column(db.Time, default=0)
        elapsed_time = db.Column(db.Time, default=0)
        gear_id = db.Column(db.String(45), default='')
        average_speed = db.Column(db.Float, default=0)
        max_heartrate = db.Column(db.Integer, default=0)
        average_heartrate = db.Column(db.Float, default=0)
        suffer_score = db.Column(db.Integer, default=0)
        red_points = db.Column(db.Integer, default=0)
        description = db.Column(db.Text, default='') # COLLATE utf8mb4_bin DEFAULT NULL,
        commute = db.Column(db.Boolean, default=False)
        calories = db.Column(db.Float, default=0)
        type = db.Column(db.Enum(ActivityTypes.RIDE, ActivityTypes.RUN, ActivityTypes.HIKE, ActivityTypes.NORDICSKI), default='')

        def to_json(self):
            return {
                "id": self.id,
                "athlete": self.athlete,
                "name": self.name,
                "location": self.location,
                "date": self.date.strftime("%Y-%m-%d"),
                "distance": self.distance,
                "elevation": self.elevation,
                "moving_time": self.moving_time.strftime("%H:%M"),
                "elapsed_time": self.elapsed_time.strftime("%H:%M"),
                "gear_id": self.gear_id,
                "average_speed": self.average_speed,
                "max_heartrate": self.max_heartrate,
                "average_heartrate": self.average_heartrate,
                "suffer_score": self.suffer_score,
                "red_points": self.red_points,
                "description": self.description if self.description is not None else '',
                "commute": self.commute,
                "calories": self.calories,
                "activity_type": self.type
            }

    return Activity
