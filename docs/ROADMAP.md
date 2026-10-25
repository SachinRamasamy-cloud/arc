# Delivery roadmap

Arc is being published as a sequence of reviewable increments. This roadmap
describes delivery scope; it does not claim that unpublished components are
available in this repository or set artificial completion dates.

| Increment | Scope | Verification before publication |
| --- | --- | --- |
| 1. Native processing core | Repository conventions, C++ library, JSON/CSV worker, native tests | Release build, CTest, command-line smoke checks |
| 2. Backend foundation | Configuration, database access, migrations, identity and tenant boundaries | Migration and identity/authorization checks |
| 3. Customer API and workers | Projects, scoped credentials, processing jobs, files and events | API contracts, worker lifecycle and tenant-isolation checks |
| 4. Customer and operator applications | Shared UI/client packages, portal and staff console | Dependency lockfile, typechecks and application builds |
| 5. Public website and developer tools | Marketing site, product documentation and SDKs | Website build and SDK contract checks |
| 6. Billing and integrations | Metering, credit ledger, Stripe test flows and managed PostgreSQL configuration | Billing regressions and provider integration checks |
| 7. Local operations and release checks | Compose stack, startup tooling, end-to-end checks and deployment guidance | Full-stack smoke checks and documented release limitations |

The initial publication contains increment 1. Later pushes should update this
document and the root README to describe what that checkout can actually run.

Each commit should have a descriptive message and cover one coherent change.
Publish history uses the actual commit dates. Credentials, local databases,
runtime logs, installed dependencies and build outputs stay outside Git.
