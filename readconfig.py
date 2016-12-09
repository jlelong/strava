import ConfigParser
import sys


def read_config(inifile):
    """
    Read the content of the init file and return it as dictionnary with keys
        mysql_user, mysql_password, mysql_base, mysql_bikes_table, mysql_activities_table, strava_token
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
