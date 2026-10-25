"""Backward compatibility only; new code imports modules.invoices.application.billing_views."""
from importlib import import_module as _load
import sys as _sys
_sys.modules[__name__] = _load('modules.invoices.application.billing_views')
