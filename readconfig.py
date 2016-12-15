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
        print "No mysql user provided"
        sys.exit()

    try:
        config['mysql_bikes_table'] = parser.get('mysql', 'bikes_table')
    except ConfigParser.NoOptionError:
        print "No mysql user provided"
        sys.exit()

    try:
        config['mysql_activities_table'] = parser.get('mysql', 'activities_table')
    except ConfigParser.NoOptionError:
        print "No mysql user provided"
        sys.exit()

    try:
        config['strava_token'] = parser.get('strava', 'token')
    except ConfigParser.NoOptionError:
        print "No mysql user provided"
        sys.exit()
    return config
