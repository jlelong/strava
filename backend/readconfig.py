from __future__ import print_function
try:
    import configparser
except ImportError:
    import ConfigParser as configparser
import sys


def read_config(infile):
    """
    Read the content of the init file and return it as dictionary with keys

    See the comments inside setup.ini.dist for explanations on the different fields
    """
    parser = configparser.RawConfigParser()
    parser.read(infile)
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
        config['with_details'] = parser.getboolean('strava', 'with_details')
    except (configparser.NoOptionError, ValueError):
        config['with_details'] = False

    try:
        config['session_dir'] = parser.get('server', 'session_dir')
    except configparser.NoOptionError:
        print("No session directory defined")
        sys.exit()

    try:
        config['proxy_base'] = parser.get('server', 'base_proxy')
    except configparser.NoOptionError:
        config['proxy_base'] = None
        print("No proxy defined")

    try:
        config['athlete_whitelist'] = [int(x) for x in parser.get('server', 'athlete_whitelist').split('\n')]
    except configparser.NoOptionError:
        print('No athlete_whitelist provided.')
        config['athlete_whitelist'] = ()

    return config
