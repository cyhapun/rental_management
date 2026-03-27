import os
import sys

api_dir = os.path.dirname(os.path.abspath(__file__))
proj_root = os.path.dirname(api_dir) 

if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

from mangum import Mangum

try:
    from main import app 
except ImportError:
    from app.main import app

handler = Mangum(app)