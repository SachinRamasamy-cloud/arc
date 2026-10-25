"""Backward compatibility only; new code imports modules.metering.application.accounting."""
from importlib import import_module as _load
import sys as _sys
_sys.modules[__name__] = _load('modules.metering.application.accounting')
