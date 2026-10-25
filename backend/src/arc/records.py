"""Backward compatibility only; new code imports modules.application_data.interfaces.records."""
from importlib import import_module as _load
import sys as _sys
_sys.modules[__name__] = _load('modules.application_data.interfaces.records')
