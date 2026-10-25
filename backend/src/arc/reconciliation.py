"""Backward compatibility only; new code imports modules.payments.application.reconciliation."""
from importlib import import_module as _load
import sys as _sys
_sys.modules[__name__] = _load('modules.payments.application.reconciliation')
