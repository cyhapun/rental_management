import os
import sys
from main import app
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
except Exception as e:
	import traceback
	sys.stderr.write(f"Failed to import 'app.main': {e}\n")
	sys.stderr.write(f"proj_root={proj_root}\n")
	sys.stderr.write(f"cwd={os.getcwd()}\n")
	sys.stderr.write(f"sys.path={repr(sys.path)}\n")
	try:
		sys.stderr.write(f"proj_root listing: {repr(os.listdir(proj_root))}\n")
		app_path = os.path.join(proj_root, 'app')
		sys.stderr.write(f"app path exists: {os.path.exists(app_path)}\n")
		if os.path.isdir(app_path):
			sys.stderr.write(f"app dir listing: {repr(os.listdir(app_path))}\n")
	except Exception as ee:
		sys.stderr.write(f"Error while listing proj_root: {ee}\n")
	# Try a fallback import and include its error if it fails.
	try:
		from main import app
	except Exception as e2:
		sys.stderr.write(f"Fallback import 'main' failed: {e2}\n")
		traceback.print_exc(file=sys.stderr)
		raise

handler = Mangum(app)