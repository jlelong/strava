import ConfigParser
import sys


def read_config(inifile):
    """
    Read the content of the init file and return it as dictionnary with keys
    mysql_base: the name of a MYSQL database
    mysql_bikes_table: the name of a table inside mysql_base to store the different bikes
    mysql_activities_table: the name of a table inside mysql_base to store the activities
    mysql_user: a user authorized to access mysql_base
    mysql_password: the password associated to the user mysql_user
    strava_token: the access token to access Strava API
    """
    parser = ConfigParser.RawConfigParser()
    parser.read(inifile)
    config = {}
    try:
        config['mysql_user'] = parser.get('mysql', 'user')
    except ConfigParser.NoOptionError:
        print "No mysql user provided"
        sys.exit()
    try:
        config['mysql_password'] = parser.get('mysql', 'password')
    except ConfigParser.NoOptionError:
        config['mysql_password'] = ""

    try:
        config['mysql_base'] = parser.get('mysql', 'base')
    except ConfigParser.NoOptionError:
        print "No name provided for the mysql base"
        sys.exit()

    try:
        config['mysql_bikes_table'] = parser.get('mysql', 'bikes_table')
    except ConfigParser.NoOptionError:
        print "No name provided for the bikes table"
        sys.exit()

    try:
        config['mysql_activities_table'] = parser.get('mysql', 'activities_table')
    except ConfigParser.NoOptionError:
        print "No name provided for the activities table"
        sys.exit()

    try:
        config['client_id'] = parser.get('strava', 'client_id')
    except ConfigParser.NoOptionError:
        print "No Strava client id provided"
        sys.exit()

    try:
        config['client_secret'] = parser.get('strava', 'client_secret')
    except ConfigParser.NoOptionError:
        print "No Strava client secret provided"
        sys.exit()

    try:
        config['with_points'] = parser.getboolean('strava', 'with_points')
    except (ConfigParser.NoOptionError, ValueError):
        config['with_points'] = False

    return config
