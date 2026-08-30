# Nova Architecture Decision

Campaign: `HG-WP6.5-NOVA-CONVERSATIONAL-CORE-VS-OUTER-LAYERS-AUDIT-20260830-01`

## Recommendation

`KEEP_NOVA_CORE_REBUILD_OUTER_LAYERS`

Keep the original conversational Nova core from `a962c19`: isolated Telegram
worker, Nova SOUL, bounded session memory, model gateway, and natural response
behavior.

Remove or rebuild only the outer behavior that currently forces a single tool
before Nova understands the question. The replacement should expose a compact
allowlisted capability catalog and let semantic reasoning select resources,
then apply deterministic TruthKernel validation to retrieved claims and all
operational requests.

### Keep

- Nova conversational identity and plain-language response style
- session continuity and bounded memory
- Telegram authorization and delivery receipts
- TruthKernel, report quarantine, cost policy, privacy controls
- shared capability permission boundary
- Nexus governed request intake and Alpha governed intake

### Remove or narrow

- pre-model source forcing for non-deterministic advisory/research questions
- fallback wording that turns a provider error into broad inability
- any global interpretation of degraded Nexus state
- context injection that treats a derived report as current truth

### Rebuild

1. semantic information-need planning before tool selection;
2. capability discovery over public web, Alpha, company data, Nexus reads, and
   governed request submission;
3. provider fallback with service-specific failure envelopes;
4. evidence retrieval and contradiction checks;
5. post-retrieval claim validation and natural-language synthesis.

### Do not touch

- direct Nexus execution prohibition;
- TruthKernel authority;
- Active Operator semantics;
- cost/privacy boundaries;
- historical evidence and quarantine records.

## Scoring (1–5)

| Criterion | A: repair current | B: keep core/rebuild outer | C: Nova V2 |
|---|---:|---:|---:|
| Conversational freedom | 3 | 5 | 5 |
| Business-partner behavior | 3 | 5 | 4 |
| Current web/tool selection | 2 | 5 | 4 |
| Alpha/Nexus integration | 4 | 5 | 3 |
| Truth/authority safety | 4 | 5 | 3 |
| Hermes feature use | 3 | 5 | 4 |
| Failure isolation | 2 | 5 | 3 |
| Maintainability | 2 | 4 | 2 |
| Migration risk (higher is safer) | 4 | 4 | 1 |
| Time to real-world proof | 3 | 4 | 1 |
| Weighted overall | 2.9 | 4.8 | 2.9 |

## Phased future implementation plan

1. Freeze and instrument the current Nova core.
2. Replace pre-model source forcing with semantic information-need planning.
3. Add capability discovery and service-specific failure envelopes.
4. Repair public search/provider fallback and page retrieval boundaries.
5. Integrate Alpha handoff and returned-artifact tracking.
6. Preserve Nexus as operational resource and authority boundary.
7. Apply TruthKernel validation after retrieval, not as a global precondition.
8. Run fresh real Telegram A/B tests and compare full user-visible answers.
9. Cut over by feature flag with immediate rollback to the current graph.

No implementation was performed in this audit campaign.
