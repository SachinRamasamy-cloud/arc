# Arc

Arc is a modular API platform being published in focused development increments.
The published milestones introduce the native processing core and the backend
foundation used by subsequent components.

## Published milestones

Milestone 2 adds validated configuration, database migrations, password and token
primitives, identity/session models, tenant-access policies, and a health-only
FastAPI application. See [backend foundation setup](docs/FOUNDATION.md) for
installation, migration, startup, and test commands.

Milestone 1 provides the native C++20 processing engine:

- Validation of JSON records and required fields.
- Record normalization, including field mapping, trimming, and ASCII lowercasing.
- Conversion between CSV and JSON.
- Bounded input processing and consistent invalid-input responses.
- A reusable static library, a command-line worker, and CTest regression checks.

Customer API routes and workers, web applications, billing adapters, and
deployment configuration will be introduced in later increments. The database
baseline includes model definitions for later domains so the existing migration
chain remains consistent; it does not expose those features as APIs.

## Run the backend foundation

Use Python 3.12 or later and an activated virtual environment:

```bash
python -m pip install -e './backend[test]'
python scripts/bootstrap.py
arc-foundation migrate
python -m uvicorn entrypoints.foundation_api.main:create_app --factory --host 127.0.0.1 --port 8000
```

Readiness is available at `http://127.0.0.1:8000/health/ready`. The bootstrap
command creates a local `.env` only when one does not already exist. To run the
isolated tests:

```bash
python -m pytest -c backend/pyproject.toml backend/foundation_tests -q
```

## Build and test the native engine

The current CMake configuration targets Linux with GCC. Install CMake 3.20 or
later, a C++20 compiler, Make, and Boost.JSON development headers. For example,
on Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y cmake g++ make libboost-json-dev

cmake -S native -B native/build -DCMAKE_BUILD_TYPE=Release
cmake --build native/build --parallel 2
ctest --test-dir native/build --output-on-failure
```

On Windows, use a Linux environment such as WSL for these commands.

## Try the engine

The worker reads one JSON request from standard input and writes one JSON result.

```bash
printf '%s\n' '{"operation":"normalize","data":[{"email":" ADA@EXAMPLE.TEST "}],"lowercase":["email"]}' | native/build/arc-engine
```

```json
{"ok":true,"engine_version":"1.0.0","records":1,"format":"json","output":[{"email":"ada@example.test"}]}
```

## Source layout

```text
backend/
  foundation/              Configuration, database, cryptography and errors
  database/                Schema registry and frozen migration history
  modules/                 Domain models and authorization policies
  entrypoints/             Foundation migration CLI and health API
  foundation_tests/        Independent migration, security and access tests
native/
  include/arc/             Public native interfaces
  engines/validation/      JSON record and CSV validation
  engines/transformation/  Normalization and conversion
  worker/                  Command-line entry point
  tests/                   Native regression checks
docs/
  FOUNDATION.md            Backend setup and milestone boundaries
  ROADMAP.md               Planned delivery increments
```

See the [delivery roadmap](docs/ROADMAP.md) for the next milestones. Each
increment should include its own verification and updated setup instructions.
