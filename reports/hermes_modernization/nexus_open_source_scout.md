# Nexus Open Source Scout Workflow

## Purpose

The open-source scout is an Alpha workflow for finding whether an existing
project already solves a capability Nexus is considering building or buying.

It is not a new agent.

## Required Nexus-first audit

Before recommending a project, the scout must check:

1. existing Nexus source and report references
2. package manifests and dependencies
3. integrations, plugins, skills, and workflows
4. runtime configuration and reports
5. equivalent capabilities under different names

## Nexus state classifications

- `ALREADY_INSTALLED`
- `ALREADY_INTEGRATED`
- `PARTIALLY_INTEGRATED`
- `EQUIVALENT_CAPABILITY_EXISTS`
- `NOT_PRESENT`
- `STALE_UNUSED`
- `CONFLICTING`

## Candidate evaluation fields

- project
- repository
- purpose
- license
- maintenance status
- release activity
- security considerations
- API
- MCP support
- agent friendliness
- self-hosting burden
- Nexus overlap
- integration effort
- monthly cost displaced
- new business capability
- maintenance burden

## Recommendation classes

- `ADOPT`
- `EXTEND_EXISTING`
- `WRAP`
- `PILOT`
- `WATCH`
- `REJECT`

## Deterministic-first workflow

SOURCE
→ Python/API collection
→ normalize
→ dedupe
→ hash
→ classify source
→ extract deterministic metadata
→ compare against known evidence
→ material change?
  - NO: store and stop
  - YES: use the lowest necessary AI tier
→ structured evidence
→ opportunity engine

## Guardrails

- No automatic installation
- No new persistent identity
- No client PII
- No unrestricted writes
- No production cutover
- Audit first, reuse second, extend third, create only if missing
