# Nexus Department / Skill / Loop Matrix

Canonical source: `data/runtime/nexus_department_registry.json` and the
department mappings in `data/runtime/nexus_skill_registry.json`.

| Department | Primary loops | Skills | Workers | Target | Authority |
|---|---|---|---|---|---|
| OPERATIONS | Daily Operations; System Health Recovery | system-operations, system-recovery, python-executor, failure-recovery, work-order-management | Operations, Review | Mac / hybrid | internal read-only |
| RESEARCH_ALPHA | Research Intelligence; Repo Intelligence | research-intelligence, repo-intelligence, model-routing | Research, Review | hybrid | read-only |
| CREDIT_BUSINESS_FUNDING | Credit/Business/Funding; Ray Review | credit-readiness, business-bankability, funding-readiness | Funding, Review | Mac | internal review |
| CLIENT_LIFECYCLE | Ray Review | client-lifecycle, ray-review | Client Lifecycle, Review | Mac | human authority required |
| MARKETING_CREATIVE | Ray Review | marketing-content-draft, ray-review | Content, Review | Mac / hybrid | internal review |
| GOVERNANCE_REVIEW | Ray Review | ray-review, work-order-management, failure-recovery, model-routing | Review, Operations | Mac / hybrid | human review |
| SYSTEM_ENGINEERING | Repo Intelligence; Ray Review | repo-intelligence, python-executor, model-routing | Research, Review | Mac / hybrid | internal read-only |

Shared support skills intentionally occur in multiple departments; one-skill /
one-loop ownership is not assumed.
