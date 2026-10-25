"""Backward compatibility only; new code imports modules.processing_capabilities.infrastructure.native."""
from importlib import import_module as _load
import sys as _sys
_sys.modules[__name__] = _load('modules.processing_capabilities.infrastructure.native')
