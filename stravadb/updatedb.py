import stravalib.client
import pymysql.cursors

FRAME_TYPES = {0: "none", 1: "mtb", 3: "road", 2: "cx", 4: "tt"}


def update_bikes(config):
    """
    Update the database of bikes
    Arg:
        config  a dictionnary as returned by readconfig.read_config
    """

    # Connect to the database
    connection = pymysql.connect(host='localhost', user=config['mysql_user'], password=config['mysql_password'], db=config['mysql_base'])
    table = config['mysql_bikes_table']
    cursor = connection.cursor()

    stravaClient = stravalib.Client()
    stravaClient.access_token = config['strava_token']
    bikes = stravaClient.get_athlete().bikes
    for bike in bikes:
        desc = stravaClient.get_gear(bike.id)
        print "%s, %s, %s" % (desc.name, desc.id, FRAME_TYPES[desc.frame_type])

        # Check if the bike already exists
        sql = "select * from %s where id='%s' limit 1" % (table, bike.id)
        if (cursor.execute(sql) > 0):
            continue

        sql = "insert into %s (id, name, type, frame_type) values ('%s','%s', '%s', '%d')" % (table, desc.id, desc.name, FRAME_TYPES[desc.frame_type], desc.frame_type)
        cursor.execute(sql)
        connection.commit()
    cursor.close()
    connection.close()
