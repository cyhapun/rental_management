import sys
from pathlib import Path

# Ensure project root is on sys.path so tests can import application packages
ROOT = Path(__file__).resolve().parent.parent
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)
