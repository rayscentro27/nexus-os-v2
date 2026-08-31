# Nova / Hermes Migration Decision

**Decision:** `KEEP_NOVA_CORE_REPLACE_SELECTED_CUSTOM_WITH_HERMES_NATIVE`  
**Confidence:** Medium-high for direction; low for immediate cutover readiness.

## Why

Hermes Agent 0.20.6 is real and installed. Its native tool registry, tool-call
continuation, provider adapters, sessions, memory, skills, and delegation
overlap with custom Nova plumbing. The current direct OpenRouter path and text
envelope tool protocol therefore leave useful Hermes functionality unused and
create avoidable failure surfaces.

A full move would be premature. Hermes does not replace Nexus TruthKernel,
receipts, work orders, approval authority, privacy policy, or cost policy. Its
native Alpha/delegation primitives are not the same as the existing durable
Alpha artifact lifecycle. The current Nova core is also valuable and should be
preserved.

## Keep

- Nova's SOUL, business-partner identity, and conversational core
- five-stage graph as the current safety/compatibility shell during migration
- Nexus TruthKernel, live truth, receipts, approvals, work orders, and authority
- granular company/Google/privacy/cost boundaries
- existing proven web providers and Alpha lifecycle until native adapters prove parity

## Replace selectively later

- text-based capability envelope with Hermes native tool calls
- custom model continuation with native tool-result continuation
- provider/fallback plumbing with Hermes-native adapters where cost and telemetry remain equivalent
- duplicated generic session/skill metadata where Hermes can supply it without stale-state regression
- generic fallback with a tool-aware native continuation/fallback

## Do not touch in this decision

- Nova personality/SOUL
- direct Nexus write authority
- TruthKernel semantics
- unapproved spend policy
- Google write capabilities
- Alpha/Nexus governed lifecycle
- current live Telegram cutover

## Option scores (1 = weak, 5 = strong)

| Dimension | A: current custom | B: core + selected Hermes | C: Hermes primary |
|---|---:|---:|---:|
| Reasoning quality | 3 | 4 | 4 |
| Tool reliability | 2 | 4 | 4 |
| Resource awareness | 3 | 4 | 4 |
| Recommendation quality | 4 | 4 | 4 |
| Multi-model support | 2 | 3 | 4 |
| Current research | 2 | 4 | 4 |
| Alpha delegation | 3 | 4 | 3 |
| Session continuity | 3 | 4 | 4 |
| Fallback robustness | 2 | 4 | 4 |
| Truth integration | 5 | 5 | 3 |
| Authority safety | 5 | 5 | 3 |
| Cost control | 4 | 4 | 3 |
| Privacy | 4 | 4 | 3 |
| Maintainability | 2 | 4 | 3 |
| Custom code reduction | 1 | 4 | 5 |
| Migration risk | 5 | 3 | 1 |
| Rollback | 5 | 4 | 2 |
| Time to real proof | 3 | 3 | 1 |

These are architecture-audit scores, not a claim of production performance.

## Phased plan, not executed

0. Checkpoint current Nova and capture Telegram/runtime telemetry.
1. Run a Hermes-native shadow agent with the same Nova SOUL/profile.
2. Keep the same model baseline and compare prompts/session behavior.
3. Expose PUBLIC_WEB through a bounded native tool adapter.
4. Add bounded Nexus read tool with TruthKernel provenance.
5. Integrate Alpha as native short-task delegation plus existing durable intake.
6. Add granular Google read only if already authenticated and approved.
7. Pilot provider/reasoning tiers under cost controls.
8. Optionally test MoA only for selected high-value decisions.
9. Run paired development and Telegram tests with receipts.
10. Cut over only after parity; retain immediate rollback to current Nova worker.

## Final recommendation

`KEEP_NOVA_CORE_REPLACE_SELECTED_CUSTOM_WITH_HERMES_NATIVE` is the least
disruptive path that addresses the proven duplication while preserving Nexus's
non-replaceable authority and Nova's identity.

