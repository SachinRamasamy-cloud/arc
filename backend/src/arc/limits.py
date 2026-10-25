"""Backward compatibility only; new code imports modules.rate_limits.infrastructure.limiter."""
from importlib import import_module as _load
import sys as _sys
_sys.modules[__name__] = _load('modules.rate_limits.infrastructure.limiter')
