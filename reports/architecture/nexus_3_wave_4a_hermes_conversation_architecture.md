# Nexus OS 3.0 Wave 4A — Hermes Conversation Architecture

Generated: 2026-07-18

## 1. Starting checkpoint

- Branch verified: `main`
- Starting HEAD verified: `0726ef5ceb9a91eaf0ab58a0c09ae41be3534e97`
- Expected commit message verified: `build nexus 3 knowledge layer and governed ai brains`
- Remote status verified before implementation: `origin/main` at the same commit.

## 2. Worktree safety

The worktree contained a large pre-existing dirty set, primarily Alpha, Telegram, runtime cache, report, temp, and local artifact files. These were treated as unrelated and protected.

Wave 4A edited only Hermes conversation architecture, Command Center visibility, Capability OS registration, tests, and Wave 4A reports/runtime artifacts.

## 3. Complete router audit

Primary Hermes layers found:

| Layer | Evidence | Current disposition |
|---|---|---|
| Response router | `src/lib/hermesResponseRouter.ts` | Adapter to canonical conversation engine for conversational, status, advisory, selection, task, approval, and command modes |
| Brain pipeline | `src/lib/hermesBrainPipeline.ts` | Existing rich workroom pipeline retained; canonical contract tested alongside it |
| Priority router | `src/lib/hermesPriorityRouter.ts` | Existing route-policy engine retained |
| Executive advisor | `src/lib/executive/hermesExecutiveAdvisor.ts` | Evidence-backed Executive status/advice source |
| Knowledge context | `src/lib/intelligence/contextAssembler.ts` | Governed context source used by canonical engine where relevant |
| Advisory continuity | `src/lib/hermesAdvisoryContinuity.ts` | Legacy compatibility source; superseded for new canonical session contract |
| Selection memory | `src/lib/hermesConversationState.ts`, `src/lib/hermesMemoryStores.ts` | Retained for existing workroom routes; canonical resolver added for Wave 4A |
| Local casual templates | `src/lib/hermesConversationBrain.ts`, `src/lib/hermesCommonConversation.ts` | Retained, with robotic wording reduced where directly identified |

Known conflict repaired: simple conversation could reach older canned identity/preference wording. The canonical conversation engine now owns obvious social/casual modes before route-level operational context.

## 4. Canonical pipeline

Implemented:

```text
User message
  -> session resolution
  -> Hermes brain profile assumption
  -> conversation-mode classification
  -> advisory/selection memory resolution
  -> governed context retrieval where relevant
  -> deterministic safety/action policy
  -> response-strategy selection
  -> natural response generation
  -> explicit action extraction only
  -> memory update
  -> sanitized trace and quality evidence
```

Code:

- `src/lib/hermes/hermesConversationEngine.ts`
- `src/lib/hermes/hermesConversationTypes.ts`

## 5. Mode classification

Implemented deterministic top-level modes in `src/lib/hermes/hermesModeClassifier.ts`.

Modes include social greeting, casual conversation, Executive advice, follow-up advice, system status, factual/explanation, selection reference, task request, approval request, command, clarification, and blocked/unsupported.

Classification occurs before narrow intent routing.

## 6. Memory hierarchy

Implemented in `src/lib/hermes/hermesMemoryResolver.ts`.

Priority:

1. Current message
2. Immediate prior turn
3. Active advisory context
4. Active selection context
5. Task context placeholder
6. Executive decision memory via existing systems
7. Approved knowledge/context when relevant
8. Page context
9. Safe fallback

## 7. Advisory continuity

Canonical advisory context supports:

- advisory ID
- topic
- summary
- recommendations
- preferred recommendation
- evidence IDs
- expiry

Follow-ups such as “is that realistic,” “what would stop us,” and “what would it cost” resolve against the bounded advisory context.

## 8. Selection resolution

Implemented in `src/lib/hermes/hermesReferenceResolver.ts`.

Supports numbered references, ordinal references, pronouns, preferred recommendation, and named recommendation matching. Clarification is used only when confidence is materially low.

## 9. Response strategy

Implemented in `src/lib/hermes/hermesResponseStrategy.ts`.

Strategy rules:

- Deterministic: greetings, status, blocked commands, explicit task/approval boundaries.
- Hybrid: Executive advice, follow-up advice, selection references.
- Model-assisted class reserved for nuanced explanation/idea review, but no external provider is activated in this wave.
- Safe fallback: only when no safe grounded response exists.

## 10. Provider/fallback behavior

External model providers were not activated. The canonical pipeline uses Nexus-native deterministic and hybrid responses. Fallback preserves conversational intent and does not show unrelated menus.

## 11. Action separation

Ordinary questions do not create tasks, approvals, work orders, or jobs.

Explicit requests such as “turn number 2 into a work request” return a conversation-only governed action draft with `requiresApproval: true`. No persistence is performed by the conversation engine.

## 12. Status honesty

Canonical status answers distinguish:

- Stripe: test mode; live deferred.
- Trading: live execution blocked by policy.
- Alpha Supabase/client data: prohibited.
- GitHub MCP: Reader registered but not configured; Writer disabled.
- Web search: unrestricted live search not available from this chat.

## 13. Page-context discipline

Social and casual modes ignore page context. Page context remains available for explicit page questions through existing adapters.

## 14. Response-quality evaluator

Implemented in `src/lib/hermes/hermesResponseQuality.ts`.

Scored dimensions:

- intent alignment
- continuity
- memory correctness
- naturalness
- directness
- evidence honesty
- action separation
- repetition control
- length fitness

## 15. Certification corpus

Implemented durable corpus in `getHermesCertificationCorpus()`.

Coverage:

- greetings and casual conversation
- historical bad response regressions
- Executive advice
- follow-up advice
- selection references
- action separation
- status honesty
- page-context conflict

## 16. Historical regression results

Focused run:

- `tests/hermes_conversation_engine.test.ts`: PASS
- `tests/hermes_conversation_certification.test.ts`: PASS
- `tests/hermes_route_dominance_repair.test.ts`: PASS
- `tests/hermes_common_advisor_polish.test.ts`: PASS

Historical regression score: 100%.

## 17. Browser results

Browser certification passed after implementation.

- Executive Command Center browser suite: PASS, 7/7.
- Authenticated client/admin browser suite: PASS, 18/18.
- Responsive coverage: desktop, laptop, tablet, and mobile from the existing Executive suite plus authenticated client/admin responsive checks.

The Executive Command Center exposes `data-testid="executive-hermes-conversation-health"` for ongoing browser certification.

## 18. Security results

- No external framework installed.
- No GitHub MCP activation.
- No live Stripe activation.
- No live trading activation.
- No Alpha Supabase expansion.
- No credential values stored.
- Sanitized traces only.

## 19. Legacy-router disposition

| Component | Disposition |
|---|---|
| `hermesResponseRouter.ts` | Adapter to canonical engine for Wave 4A modes |
| `hermesBrainPipeline.ts` | Retained canonical workroom pipeline pending later consolidation |
| `hermesPriorityRouter.ts` | Retained policy route engine |
| `hermesConversationBrain.ts` | Retained legacy local conversation helper; robotic responses reduced |
| `hermesAdvisoryContinuity.ts` | Compatibility source |
| `hermesConversationState.ts` | Compatibility source for existing workroom memory |

No legacy router was deleted in Wave 4A.

## 20. Known limitations

- Durable database-backed conversational memory was not added; current canonical memory is bounded session state.
- The rich workroom pipeline remains a separate consumer path and should be migrated further in a later router retirement wave.
- External model-assisted generation remains unactivated by policy.

## 21. Recommendation for Department Operations

Proceed to Department Operations only if final full regression, browser certification, and production build remain passing.
