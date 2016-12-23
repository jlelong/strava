#!/usr/bin/env python

import json

ans = "Python call succeeded"
print 'Content-type: application/json\n\n'
print json.dumps(ans)
