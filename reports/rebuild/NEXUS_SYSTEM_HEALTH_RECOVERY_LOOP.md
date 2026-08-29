# System Health / Recovery Loop — 2026-08-29

The loop definition and `system-recovery` / `failure-recovery` skills are
implemented in the v2 registry. Its scope is read-only health inspection,
failure classification, bounded follow-up, and receipt creation. Destructive
repair and service restart are excluded. Status remains `READY_FOR_INTERNAL`
until a fresh bounded execution is certified.
