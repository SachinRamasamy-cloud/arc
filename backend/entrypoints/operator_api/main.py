"""Dedicated operator_api process composition root."""
from entrypoints.application import create_app
app = create_app(surface='operator')
