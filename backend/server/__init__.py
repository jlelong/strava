import os
import cherrypy
from backend.server.serve import StravaUI
from backend import readconfig


def app(app_dir):
    config = readconfig.read_config(os.path.join(app_dir, 'setup.ini'))
    session_dir = config['session_dir']
    frontend_dir = os.path.join(app_dir, 'frontend')
    if not os.path.exists(session_dir):
        os.mkdir(session_dir)
    conf = {
        '/': {
            # 'tools.proxy.on': True,
            # 'tools.proxy.base': 'http://localhost/mystrava',
            # 'tools.proxy.local': "",
            'tools.encode.text_only': False,
            'tools.sessions.on': True,
            'tools.sessions.storage_class': cherrypy.lib.sessions.FileSession,
            'tools.sessions.storage_path': session_dir,
            'tools.sessions.timeout': 60 * 24 * 30,  # 1 month
            'tools.staticdir.on': True,
            'tools.staticdir.root': frontend_dir,
            'tools.staticdir.dir': '',
            'tools.response_headers.on': True,
            'log.access_file': "{0}/log/access.log".format(app_dir),
            'log.error_file': "{0}/log/error.log".format(app_dir),
        },
    }

    print(conf['/'])
    cherrypy.config.update({'server.socket_host': '127.0.0.1', 'server.socket_port': 8080})
    # cherrypy.quickstart(StravaUI(WUI_DIR), '/mystrava', conf)
    cherrypy.quickstart(StravaUI(frontend_dir, config), '/', conf)
