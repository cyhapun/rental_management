import os
import sys

api_dir = os.path.dirname(os.path.abspath(__file__))

# Find a directory that contains the `app` package by walking upwards from the
# current file location. This handles Vercel's runtime which may expose this
# file as `/var/task/api/index.py` while the package lives at `/var/task/app`.
def find_repo_root(start_dir):
	cur = start_dir
	for _ in range(6):
		if os.path.isdir(os.path.join(cur, 'app')):
			return cur
		parent = os.path.dirname(cur)
		if parent == cur:
			break
		cur = parent
	return None

proj_root = find_repo_root(api_dir) or os.getcwd()
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