# Architecture checks

Run `PYTHONPATH=backend:backend/src pytest -q backend/tests/test_clean_architecture.py` and
`python scripts/verify_architecture.py` from repository root.

The checks verify module ownership, preserved table metadata, allowed imports, route surface
isolation, and worker composition. They do not substitute for PostgreSQL/R2/Stripe staging tests.
