# Frontend application boundaries

- `apps/website/`: public marketing/docs, interactive Three.js GLB, static legal pages.
- `apps/customer-portal/`: workspace/project-scoped customer management and billing.
- `apps/operator-console/`: restricted staff administration with independent layouts and CSS.
- `packages/ui/`: **only** shared black/silver tokens, Geist styles, components and motion.
- `packages/client/`: safe network request machinery; customer and operator auth are distinct.
- `packages/contracts/`: public API/event data contracts, not internal secrets.

The portal has `app/` for providers/layout/router and `modules/<feature>/pages/` for
individual features. The operator console similarly owns `app/` and staff `modules/`.
No customer feature is imported directly into the operator application. Support pages
have their own context and permissions; staff are not granted automatic access to private
customer files or keys. The public application has no private dashboard imports.

React build and browser tests remain blocked until reviewed npm lockfile and all npm
dependencies are available. Static TS import/syntax checks and 21 frontend logic checks
are not substitutes for actual rendering or WebGL verification.
