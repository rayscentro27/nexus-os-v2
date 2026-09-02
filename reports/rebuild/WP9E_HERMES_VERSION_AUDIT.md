# WP9E Hermes version audit

Local Hermes source: `~/.hermes/hermes-agent`, package version `0.14.0`, git
commit `cea87d9139044870752aafdcdf9ca253049ae175` (describe:
`v2026.5.16-1082-gcea87d9139`). The active Oracle service is a containerized
Hermes runtime; its image is running, but its exact package version was not
changed or inferred from the process name.

Official upstream evidence reviewed: Hermes v0.17.0 (2026-06-19) is the latest
release visible in the official repository during this audit. Current local
runtime is therefore BEHIND. The release line includes platform/reach and
security/runtime changes, but a cutover has not been validated.

Recommendation: `STAGE_FIRST`. Do not replace production. Oracle staging is
feasible in principle because Podman, 22 GiB RAM and an existing Hermes
container are present, but a new isolated staging image/config and adapter
regression are still required.
