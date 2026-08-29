# Nexus Skill Registry Certification — 2026-08-29

The initial Nexus library contains 14 real SKILL.md contracts under
`skills/nexus/`. They reference actual Nexus services, reports, TruthKernel,
Hermes routes, or explicitly bounded future dependencies; none contains
credentials. The canonical registry is `data/runtime/nexus_skill_registry.json`.

The resolver is tested for successful selection, missing skill, authority
mismatch, and executor mismatch. It does not fall back to arbitrary shell or
unknown tools. Skills with no certified executor remain descriptive and are
not promoted to operational status.

`SKILL_LOADING_PROVEN=YES`
`SKILL_RESOLUTION_PROVEN=YES`
`SKILL_AUTHORITY_FAIL_CLOSED=YES`
`SKILL_EXECUTOR_ALLOWLIST_ENFORCED=YES`
