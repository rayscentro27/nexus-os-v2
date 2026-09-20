# Nexus Department Queue Adoption Template V1

Use this template when certifying a department against
`NEXUS_DEPARTMENT_WORK_QUEUE_STANDARD_V1.md`. Complete the inventory first;
do not migrate storage merely to satisfy the template.

## Department contract

```yaml
DEPARTMENT: ""
WORK_CLASSES: []
CAPABILITIES: []
PRIORITY_MAPPING: {}
WORKER_REGISTRY: []
QUEUE_VIEW: ""
PROJECT_AGGREGATION: ""
RETRY_POLICY: ""
HANDOFF_INPUTS: []
HANDOFF_OUTPUTS: []
NOVA_VISIBILITY: ""
```

## Required evidence

| Area | Evidence required |
|---|---|
| Queue persistence | Durable work IDs, objective IDs, states, timestamps |
| Routing | Required capabilities, certified candidates, routing receipt |
| Leases | Claim owner, expiry, collision and recovery evidence |
| Fairness | Priority order plus eventual progress for lower classes |
| Retries | Changed strategy, backoff, exhaustion, external-block handling |
| Follow-ups | Parent/child links and duplicate prevention |
| Project aggregation | Multi-child status, required/optional semantics, blockers |
| Nova inspection | Queue, project, worker, lease, blocker, and next-action reads |
| Handoffs | Source/destination lineage and receiving-queue consumption |

## Certification checklist

- [ ] queue persists and distinguishes historical from active work
- [ ] work classes map to universal priority semantics
- [ ] capability registry is authoritative for routing
- [ ] leases claim, expire, recover, and cannot double-claim
- [ ] fairness prevents permanent starvation
- [ ] retries change strategy and terminate honestly
- [ ] follow-ups preserve parent lineage and deduplicate active requests
- [ ] project aggregation cannot complete prematurely
- [ ] optional monitoring does not block required completion
- [ ] blockers distinguish local, capability, objective, and external causes
- [ ] handoffs create destination child work and are consumed
- [ ] Nova can explain why a project is not complete
- [ ] Admin/monitor exposes the same canonical state

## Adoption result

```yaml
INITIAL_STATUS: ""
DEFECTS_FOUND: []
REPAIRS: []
RETEST_STATUS: ""
FINAL_STATUS: ""
MIGRATION_RISK: ""
NEXT_ACTION: ""
```
