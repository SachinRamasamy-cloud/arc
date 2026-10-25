"""Backward compatibility only; new code imports modules.authorization.application.access."""
from importlib import import_module as _load
import sys as _sys
_sys.modules[__name__] = _load('modules.authorization.application.access')
