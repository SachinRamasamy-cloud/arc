# Delivery roadmap

Arc is being published as a sequence of reviewable increments. This roadmap
describes delivery scope; it does not claim that unpublished components are
available in this repository or set artificial completion dates.

| Increment | Scope | Verification before publication |
| --- | --- | --- |
| 1. Native processing core | Repository conventions, C++ library, JSON/CSV worker, native tests | Release build, CTest, command-line smoke checks |
| 2. Backend foundation | Configuration, database access, migrations, identity and tenant boundaries | Migration and identity/authorization checks |
| 3a. Customer identity | Sign-up, verification, login, recovery, sessions, MFA and local mailbox | Identity lifecycle, request security and single-use token checks |
| 3b. Customer API and workers | Projects, scoped credentials, processing jobs, files and events | API contracts, worker lifecycle and tenant-isolation checks |
| 4. Customer and operator applications | Shared UI/client packages, portal and staff console | Dependency lockfile, typechecks and application builds |
| 5. Public website and developer tools | Marketing site, product documentation and SDKs | Website build and SDK contract checks |
| 6. Billing and integrations | Metering, credit ledger, Stripe test flows and managed PostgreSQL configuration | Billing regressions and provider integration checks |
| 7. Local operations and release checks | Compose stack, startup tooling, end-to-end checks and deployment guidance | Full-stack smoke checks and documented release limitations |

The current publication contains increments 1, 2 and 3a. Customer identity now has
an independent HTTP surface. Project/job/file APIs and workers remain increment
3b; the other application and integration increments are still pending.
Later pushes should update this document and the root README to describe what
that checkout can actually run.

Each commit should have a descriptive message and cover one coherent change.
Publish history uses the actual commit dates. Credentials, local databases,
runtime logs, installed dependencies and build outputs stay outside Git.
