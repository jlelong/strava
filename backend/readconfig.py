from __future__ import print_function
try:
    import configparser
except ImportError:
    import ConfigParser as configparser
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
    parser = configparser.RawConfigParser()
    parser.read(inifile)
    config = {}
    try:
        config['mysql_user'] = parser.get('mysql', 'user')
    except configparser.NoOptionError:
        print("No mysql user provided")
        sys.exit()
    try:
        config['mysql_password'] = parser.get('mysql', 'password')
    except configparser.NoOptionError:
        config['mysql_password'] = ""

    try:
        config['mysql_base'] = parser.get('mysql', 'base')
    except configparser.NoOptionError:
        print("No name provided for the mysql base")
        sys.exit()

    try:
        config['mysql_bikes_table'] = parser.get('mysql', 'bikes_table')
    except configparser.NoOptionError:
        print("No name provided for the bikes table")
        sys.exit()

    try:
        config['mysql_activities_table'] = parser.get('mysql', 'activities_table')
    except configparser.NoOptionError:
        print("No name provided for the activities table")
        sys.exit()

    try:
        config['client_id'] = parser.get('strava', 'client_id')
    except configparser.NoOptionError:
        print("No Strava client id provided")
        sys.exit()

    try:
        config['client_secret'] = parser.get('strava', 'client_secret')
    except configparser.NoOptionError:
        print("No Strava client secret provided")
        sys.exit()

    try:
        config['with_points'] = parser.getboolean('strava', 'with_points')
    except (configparser.NoOptionError, ValueError):
        config['with_points'] = False

    try:
        config['with_description'] = parser.getboolean('strava', 'with_description')
    except (configparser.NoOptionError, ValueError):
        config['with_description'] = False

    try:
        config['session_dir'] = parser.get('server', 'session_dir')
    except configparser.NoOptionError:
        print("No session directory defined")
        sys.exit()

    return config
