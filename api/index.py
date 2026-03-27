import os
import sys

api_dir = os.path.dirname(__file__)
app_dir = os.path.dirname(api_dir)
proj_root = os.path.dirname(app_dir)
if proj_root not in sys.path:
	sys.path.insert(0, proj_root)

from mangum import Mangum

# Prefer importing the package entrypoint `app.main:app`.
try:
	from app.main import app
except Exception:
	# Fall back to importing a top-level `main` module if the layout is different.
	from main import app

handler = Mangum(app)