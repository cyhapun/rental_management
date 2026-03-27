import os
import sys

proj_root = os.path.dirname(os.path.dirname(__file__))
if proj_root not in sys.path:
	sys.path.insert(0, proj_root)

from mangum import Mangum
from app.main import app

handler = Mangum(app)