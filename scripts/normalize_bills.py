"""Wrapper: delegate to async implementation normalize_bills_async.py

Kept as a thin shim so existing calls to this script keep working.
"""
import os
import sys
import asyncio
from importlib import util

HERE = os.path.dirname(os.path.abspath(__file__))
ASYNC_PATH = os.path.join(HERE, 'normalize_bills_async.py')

if not os.path.exists(ASYNC_PATH):
    print('Missing async implementation:', ASYNC_PATH)
    sys.exit(1)

spec = util.spec_from_file_location('normalize_bills_async', ASYNC_PATH)
module = util.module_from_spec(spec)
spec.loader.exec_module(module)  # type: ignore

try:
    asyncio.run(module.main())
except Exception as e:
    print('Error running async script:', e)
    raise
