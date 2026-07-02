# Hermes Layer Test Matrix

| Layer / transcript | Test coverage | Expected result |
|---|---|---|
| Safety decision memory | Email send -> why blocked | Safety explanation, no fallback |
| Approvals provenance | Pending approvals -> source question | Trace/source response, no session hijack |
| Client empty success | Mock `client_profiles` success/0 | `empty_success`, zero rows, no failure contradiction |
| Stale report vs recommendation | Reports -> next -> business recommendation -> why | Recommendation wins; report session paused |
| Report cursor | Reports -> review -> next -> next | Focus advances report 1 -> 2 -> 3 |
| Business blockers | Opportunity review -> highest -> blockers | Active focus and blocker themes returned |
| Active-target Ray Review | Opportunity review -> highest -> draft that | Conversation-only target draft and action proof |
| Response modes | System health -> CEO -> audit | Short CEO answer; audit source metadata; no fallback |
| Timeline | Yesterday recap | Verified journal or explicit missing-source answer |
| Global provenance | Domain answer -> where from | Last successful answer/trace wins |
| Default renderer | System/advisor answers | No raw paths, UUIDs, or route debug blocks |
| Session isolation/reset | Existing master/structural suites | Scoped memory; clear chat clears session/decision state |

Focused consolidation suite: `tests/hermes_state_arbiter_consolidation.test.ts`.

Compatibility suites include `hermes_structural_refactor`, `hermes_production_polish`, `hermes_master_contracts`, route dominance, topic boundary, common advisor, opportunity advisor, and all existing repository tests.

Final result: 719/719 tests passed across 27 files; production build passed.
