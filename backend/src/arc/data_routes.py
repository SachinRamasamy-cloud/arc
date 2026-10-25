"""Backward compatibility only; new code imports entrypoints.public_data_api.legacy_router."""
from importlib import import_module as _load
import sys as _sys
_sys.modules[__name__] = _load('entrypoints.public_data_api.legacy_router')
