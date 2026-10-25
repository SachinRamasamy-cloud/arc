"""Backward compatibility only; new code imports entrypoints.operator_api.legacy_router."""
from importlib import import_module as _load
import sys as _sys
_sys.modules[__name__] = _load('entrypoints.operator_api.legacy_router')
