# Arc

Arc is a modular API platform being published in focused development increments.
This first milestone introduces the native processing core and the repository
conventions used by subsequent components.

## Current milestone

The C++20 engine provides:

- Validation of JSON records and required fields.
- Record normalization, including field mapping, trimming, and ASCII lowercasing.
- Conversion between CSV and JSON.
- Bounded input processing and consistent invalid-input responses.
- A reusable static library, a command-line worker, and CTest regression checks.

The backend services, web applications, billing adapters, and deployment
configuration will be introduced in later increments. This checkout currently
builds the native engine independently.

## Build and test

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
native/
  include/arc/             Public native interfaces
  engines/validation/      JSON record and CSV validation
  engines/transformation/  Normalization and conversion
  worker/                  Command-line entry point
  tests/                   Native regression checks
docs/
  ROADMAP.md               Planned delivery increments
```

See the [delivery roadmap](docs/ROADMAP.md) for the next milestones. Each
increment should include its own verification and updated setup instructions.
