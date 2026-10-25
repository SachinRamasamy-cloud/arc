"""Backward compatibility only; new code imports entrypoints.contracts."""
from importlib import import_module as _load
import sys as _sys
_sys.modules[__name__] = _load('entrypoints.contracts')
