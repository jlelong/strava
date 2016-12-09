from __future__ import print_function

import stravalib.client
import pymysql.cursors


class Strava:
    FRAME_TYPES = {0: "none", 1: "mtb", 3: "road", 2: "cx", 4: "tt"}

    def __init__(self, config):
        """
        Initialize the StravaView class.

        Create a connection to the mysql server and prepare the dialog with the Strava api

        :param config:  a dictionnary as returned by readconfig.read_config
        """
        self.config = config
        self.connection = pymysql.connect(host='localhost', user=config['mysql_user'], password=config['mysql_password'], db=config['mysql_base'])
        self.cursor = self.connection.cursor()
        self.stravaClient = stravalib.Client()
        self.stravaClient.access_token = config['strava_token']

    def update_bikes(self):
        """
        Update the database of bikes
        """
        # Connect to the database
        table = self.config['mysql_bikes_table']
        bikes = self.stravaClient.get_athlete().bikes
        for bike in bikes:
            desc = self.stravaClient.get_gear(bike.id)
            print("%s, %s, %s" % (desc.name, desc.id, self.FRAME_TYPES[desc.frame_type]))

            # Check if the bike already exists
            sql = "select * from %s where id='%s' limit 1" % (table, bike.id)
            if (self.cursor.execute(sql) > 0):
                continue

            sql = "insert into %s (id, name, type, frame_type) values ('%s','%s', '%s', '%d')" % (table, desc.id, desc.name, self.FRAME_TYPES[desc.frame_type], desc.frame_type)
            self.cursor.execute(sql)
            self.connection.commit()

    def create_bikes_table(self):
        """
        Create the bike table if it does not already exist
        """
        # Check if table already exists
        table = self.config['mysql_bikes_table']
        sql = "SHOW TABLES LIKE '%s'" % table
        if (self.cursor.execute(sql) > 0):
            print("The table '%s' already exists" % table)
            return

        sql = """CREATE TABLE 'bikes' (
        'id' varchar(45) NOT NULL,
        'name' varchar(256) DEFAULT NULL,
        'type' enum('road','mtb','cx','tt') DEFAULT NULL,
        'frame_type' int(11) DEFAULT NULL,
        PRIMARY KEY ('id'),
        UNIQUE KEY 'strid_UNIQUE' ('id')
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8;"""
        self.cursor.execute(sql)
        self.connection.commit()

    def close(self):
        self.cursor.close()
        self.connection.close()
