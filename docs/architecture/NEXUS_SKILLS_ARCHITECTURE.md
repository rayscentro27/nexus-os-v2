# Nexus Skills Architecture

Nexus-owned skills live under `skills/nexus/<skill-id>/SKILL.md` and remain
separate from upstream Hermes skills and profile state. Each file declares
purpose, authority, side effects, model policy, worker/profile, executor
allowlist, validation, receipt, retry, handoff, and security boundaries.

`scripts/nexus_agent_platform/loops/skill_resolver.py` parses only the bounded
frontmatter and fails closed with `NO_SKILL_MATCH`,
`SKILL_BLOCKED_AUTHORITY`, or `SKILL_EXECUTOR_NOT_ALLOWED`. A skill describes
how a capability may be used; it does not grant capability. TruthKernel and
Nexus policy remain authoritative.
