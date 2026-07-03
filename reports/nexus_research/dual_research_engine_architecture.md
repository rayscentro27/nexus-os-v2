# Dual Research Engine Architecture

**Generated**: 2026-07-03  
**Status**: Design — no code changes  
**Principle**: Hermes Alpha and Nexus Hermes are separate systems with separate data, separate outputs, and separate approval paths.

---

## Overview

Nexus OS v2 operates two distinct research engines:

1. **Hermes Alpha Research Engine** — Business opportunities, marketing, trading, AI tools
2. **Nexus Credit & Funding Research Engine** — Credit repair, business funding, GoClear client support

They share no data, no Supabase connection, no client data access, and no output pipeline.

---

## Hermes Alpha Research Engine

### Owner
Hermes Alpha (separate from Nexus Hermes)

### Phase 1 Constraint
**No Supabase connection.** Alpha operates entirely on local files, local reports, and approved external research.

### Sources
| Source | Status |
|--------|--------|
| Local Alpha research inbox (`hermes_alpha/research_inbox/`) | Created, 8 subdirs (README placeholders) |
| YouTube API metadata cache (`data/cache/youtube/`) | Active, cached data exists |
| NotebookLM exports (`data/exports/notebooklm/`) | Active, research bundles exist |
| Transcripts (`data/transcripts/`) | Available |
| Tool/repo research (`configs/repo_research_targets.json`) | Configured |
| Trading notes | Available |
| Eval fixtures (`hermes_alpha/evaluations/`) | Phase 1 complete |

### Outputs
| Output | Format | Approval |
|--------|--------|----------|
| Alpha reports | Markdown in `reports/hermes_alpha/` | Auto-generated, Ray Review for external use |
| Opportunity scorecards | Local JSON/Markdown | Auto-generated |
| Marketing drafts | Local Markdown | Draft-only, Ray Review before publish |
| Trading plans | Local Markdown | Draft-only, no execution |
| Ray Review proposals | Local JSON | Requires Ray approval |

### Blocked
- Client data access
- Production mutation
- Supabase connection
- Oanda execution
- Email sending
- Social publishing
- Payment charging

---

## Nexus Credit & Funding Research Engine

### Owner
Nexus Hermes / GoClear

### Allowed Future Connection
Nexus/Supabase through approved knowledge/report pipeline only. Not connected in Phase 1.

### Sources
| Source | Status |
|--------|--------|
| Approved credit/funding research artifacts | To be collected in `nexus_research/research_inbox/` |
| Public education notes | To be collected |
| Lender/program notes | To be collected |
| Grant notes | To be collected |
| Affiliate/referral notes | Config exists, research to be collected |
| GoClear policies | Config exists |
| Client-uploaded credit reports | Through existing secure client workflow only (not connected) |

### Outputs
| Output | Format | Approval |
|--------|--------|----------|
| Readiness checklists | Markdown/JSON | Admin-only until approved |
| Admin review notes | Markdown | Admin-only |
| Client-safe education | Markdown | Requires Ray Review |
| $97 review support | Scorecard/report draft | Requires Ray Review |
| Business funding recommendations | Markdown | Requires Ray Review |
| Utilization improvement recommendations | Markdown | Requires Ray Review |
| Fundability checklist research | Markdown | Requires Ray Review |
| Ray Review proposals | JSON | Requires Ray approval |

### Blocked
- Guaranteed approvals
- Fake funding claims
- Unauthorized legal advice
- Direct disputes without approval
- Payments
- Publishing
- External sending without approval
- Supabase connection (until explicitly approved)
- Client data access (until secure workflow built)

---

## Separation Rules

### Data Separation
| Rule | Alpha | Nexus |
|------|-------|-------|
| Supabase | No connection | Future approved pipeline only |
| Client data | No access | Through secure workflow only |
| Credit reports | No access | Through approved workflow only |
| Research inbox | `hermes_alpha/research_inbox/` | `nexus_research/research_inbox/` |
| Reports | `reports/hermes_alpha/` | `reports/nexus_research/` |
| Configs | `hermes_alpha/` | `src/config/` + `configs/` |

### Output Separation
| Rule | Alpha | Nexus |
|------|-------|-------|
| Client-facing | No | Only after Ray Review |
| Admin-only | Yes | Yes |
| Draft-only | Yes | Yes |
| Auto-publish | No | No |
| External send | No | No |

### Approval Separation
| Rule | Alpha | Nexus |
|------|-------|-------|
| Ray Review required | For external use | For all client-facing |
| Admin approval | For publish | For all recommendations |
| Affiliate approval | For activation | For all promotions |
| Compliance review | Not required | Required for all credit/funding |

---

## Shared Infrastructure (But Not Shared Data)

| Infrastructure | Used By | Notes |
|----------------|---------|-------|
| Hermes Brain Pipeline | Both | Same pipeline, different area maps |
| Readiness Registry | Nexus only | Alpha does not use |
| Operating Commands | Both | Different question sets |
| Ray Review | Both | Same approval mechanism, different queues |
| Build/Test | Both | Same repo, separate test files |

---

## Implementation Phases

### Phase 1: Current (Design Only)
- Alpha: No Supabase, local research inbox, local reports
- Nexus: $97 review workflow, readiness registry, local reports
- No cross-connection

### Phase 2: Research Collection (Future)
- Alpha: Populate research inbox with real artifacts
- Nexus: Populate credit/funding research inbox with real artifacts
- Both remain local-only

### Phase 3: Adapter Build (Future)
- Alpha: Research file adapter v1 (already designed)
- Nexus: Credit/funding research adapter v1 (to be designed)
- Both remain draft-only, approval-gated

### Phase 4: Supabase Connection (Future, Nexus Only)
- Nexus connects to Supabase through approved pipeline
- Alpha remains no-Supabase
- Client data flows through secure workflow only

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Alpha accidentally accesses client data | No Supabase connection, no client data paths |
| Nexus makes unauthorized credit claims | Compliance classifiers, Ray Review gates |
| Research artifacts contain false information | Evidence quality scoring, compliance review |
| Affiliate promotions without approval | Approval gates, all programs `not_applied` |
| Funding guarantees | Explicit disclaimers, no lender connections |
| Legal advice without license | Education-only framing, compliance notes |
