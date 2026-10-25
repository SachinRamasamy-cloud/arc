"""Backward compatibility only; new code imports modules.identity.interfaces.auth."""
from importlib import import_module as _load
import sys as _sys
_sys.modules[__name__] = _load('modules.identity.interfaces.auth')
