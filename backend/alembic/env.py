"""Backward-compatible Alembic location; delegate on every invocation.

Importing database.env here would cache its module and silently skip migrations
for a second database in the same process. run_path deliberately executes it.
"""
from pathlib import Path
from runpy import run_path
run_path(str(Path(__file__).resolve().parents[1] / 'database' / 'env.py'))
