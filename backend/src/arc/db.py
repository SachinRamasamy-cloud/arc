"""Backward compatibility only; new code imports foundation.database.session."""
from importlib import import_module as _load
import sys as _sys
_sys.modules[__name__] = _load('foundation.database.session')
