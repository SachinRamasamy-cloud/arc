# Upgrade from ARC v0.3.2 to v0.3.3

**Scope:** UX, team-access read permission, public docs, service discovery and navigation. No database migration or pricing model change.

1. Back up the current database, object metadata and environment secrets. Preserve your existing `.env`, R2, Stripe and encryption keys.
2. Replace application code with v0.3.3. Do not overwrite a production data directory. Reuse existing database and migration history.
3. Update the Portal/Website build and restart the FastAPI application. If using the supplied Envoy reference, deploy its `/docs` routes too.
4. Verify `/docs` on the portal (`:5173`) and public API (`:8000`), and verify the protected customer/operator APIs still require authorization.
5. Verify Team & access as an owner and as a viewer. The viewer may read the directory but cannot invite or remove.
6. Run regression tests and staged browser tests before production deployment.

**Optionality boundaries:** Customer MFA remains optional; directory read-only access no longer requires team-management permission. Owner/admin invitation rights, staff MFA, tenant isolation, Stripe signature checks, live entitlement gates and scoped API credentials stay enforced.

Service availability remains five implemented development categories and five roadmap categories. No new commercial user-management, general realtime or storage engine is created by this UI upgrade.
