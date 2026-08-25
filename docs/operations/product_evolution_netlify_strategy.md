# Product Evolution release transport boundary

`NETLIFY_EXACT_SHA_CLI` is the only enabled and certified production strategy.
It builds from a detached immutable SHA, uploads the resulting artifact with
the fixed Netlify adapter, and verifies the returned immutable deploy identity
before any custom-domain verification.

`NETLIFY_GIT_RELEASE_BRANCH` is a documented, disabled fallback. It must use a
dedicated production release branch or tag, never `main`, and must remain bound
to the exact approved SHA, target, release ID, and rollback deploy. Promotion
would require an existing Level 3 Ray approval and a provider deploy identity
check. Returning to the CLI strategy requires the same exact-SHA artifact and
verification contract; no automatic production configuration change is part of
failover.

Failover is recommended only after at least three independent transport or
provider failures across two or more releases. Application, parser, CORS, and
production-artifact verification failures do not qualify. The fallback remains
disabled until separately certified and explicitly governed.
