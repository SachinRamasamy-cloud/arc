# ARC v0.3 Playground and Service Catalog Fix

## Scope
Target: `API_Provider_Modular_Clean_Architecture_v0_3.zip`.
This is a focused source update, not a full production qualification or a new API product release.

## Defects confirmed
1. `Playground.tsx` called `parseData(operation, input)` when the shared helper expects `parseData(input, operation)`. It therefore attempted to JSON-parse the operation name and could not send the customer's JSON/CSV input.
2. `Playground.tsx` rendered `ExecutionDetail` without importing it; the source-only syntax checker cannot detect unbound JSX component symbols.
3. The Playground did not expose the existing backend `mappings` capability, so customers could not configure field renaming from that screen.
4. The Service Catalog routed the implemented `Application data` product to the processing Playground rather than its own `/data` section.

## Applied fixes
- Added a pure, tested `packages/client/src/playground.ts` adapter for validated request construction, field detection, mapping, file source references, and credit bounds. Published as `@arc/client/playground`.
- Rebuilt the Playground page to call this adapter and correctly import the execution inspector.
- The form now shows JSON/CSV field names detected from user input and allows configuration of required fields, lowercase output fields, and source-to-destination field mappings.
- The form can use inline text (up to 1.5 MB) or an existing compatible verified file from the Files page. Uploading a NEW file is still handled by the Files module.
- Available operations are filtered from the server's service catalog rather than presenting arbitrary unimplemented operations.
- Edited input/configuration invalidates stale cost previews; the original authenticated session, rate limit and billing admission flows are retained.
- Corrected the Application Data catalog navigation to `/data` and supplied the appropriate icon.
- Added narrowly scoped styles matching the existing black/silver design.

### Example
For `normalize`, with input:

```json
[{"company_name":" ARC ","contact":" INFO@EXAMPLE.TEST "}]
```

Set `Rename fields: contact -> email` and `Lowercase output fields: email`.

Native C++ output:

```json
[{"company_name":"ARC","email":"info@example.test"}]
```

Note: field mapping **renames** existing fields; it does not synthesize an entirely new computed field or create a new API service. Adding a new JSON field to the input retains it in normalization output. Advanced transformations need an actual new native operation and published schema.

## Actual catalog in v0.3
| Catalog service | Operations | Availability |
|---|---|---|
| Data processing | `validate`, `normalize`, `csv_to_json`, `json_to_csv` | Available |
| Files for processing | `upload`, `download`, `delete` | Available (size and format limits) |
| Execution events | `sse`, `webhooks` | Available for processing execution |
| Application data | `read`, `write`, `list`, `delete` | Available as bounded encrypted JSON records |
| Identity | No public product operations | Roadmap only |
| Application realtime | No public product operations | Roadmap only |

Custom Processing Workflows are implemented separately from the catalog as compositions of the above four data-processing operations. Stripe is used for our platform billing, NOT offered as a first-party payment processing product.

## Test evidence (this environment)
- `tsc --noEmit --target es2022 --moduleResolution bundler --module esnext --strict packages/client/src/core.ts packages/client/src/playground.ts`: passed.
- `node scripts/test_playground.cjs`: 12 passed.
- `node scripts/test_frontend_logic.cjs`: 12 passed.
- `node scripts/test_billing_uploads.cjs`: 9 passed.
- `node scripts/check_frontend.cjs`: 60 files parsed, no reported syntax/local import errors.
- Native C++ CMake build + `ctest`: 2 passed.
- Native CLI run with custom field mapping, CSV input and validation: actual outputs matched expectations.
- `PYTHONPATH=backend python -m pytest -q backend/tests backend/modules --disable-warnings`: **161 passed** (compiled native engine installed at `native/build/arc-engine` during testing).

## Limitations
A full Vite build and browser/UI interaction run were **not** completed: the npm dependency cache lacks `@playwright/test` and offline installation fails. Existing v0.3 deployment still needs browser testing, real R2/Stripe qualification, PostgreSQL load/security qualification, and the broader release checklist. No new billing product, database migration or public API operation was added by this patch.

## Applying the change
1. Back up current source and environment secrets.
2. Replace the source with the complete archive or overlay the patch archive onto the existing v0.3 root.
3. Rebuild frontend dependencies when network/package registry access is available: `npm install && npm run typecheck && npm run build`.
4. Rebuild the C++ native executable if missing: `cmake -S native -B native/build -DCMAKE_BUILD_TYPE=Release && cmake --build native/build -j2`.
5. Run `node scripts/test_playground.cjs`, `node scripts/check_frontend.cjs` and Python tests as above.
6. Restart the customer portal; no SQL migration or Stripe configuration change is required by this fix.
