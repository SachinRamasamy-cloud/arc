"""Backward compatibility only; new code imports modules.realtime_events.interfaces.streams."""
from importlib import import_module as _load
import sys as _sys
_sys.modules[__name__] = _load('modules.realtime_events.interfaces.streams')
