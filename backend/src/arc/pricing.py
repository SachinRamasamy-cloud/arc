"""Backward compatibility only; new code imports modules.pricing.application.pricing."""
from importlib import import_module as _load
import sys as _sys
_sys.modules[__name__] = _load('modules.pricing.application.pricing')
