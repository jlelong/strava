import sys
import os
from backend.server import app

app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
app(app_dir)
