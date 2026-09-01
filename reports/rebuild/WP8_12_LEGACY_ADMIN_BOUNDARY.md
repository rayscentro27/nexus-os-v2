# WP8.12 Legacy Boundary

`/admin` and its existing `NexusAdminUI`/`NexusExperienceAdmin` surface remain compatibility-only. No new Operator features were added there. Reused contracts: `AdminGuard`, `AuthGate`, existing Creative library index, signed media references, and Creative review component.

`LEGACY_ADMIN_FROZEN_AS_NON_CANONICAL=YES`; canonical internal route is `/operator`.
