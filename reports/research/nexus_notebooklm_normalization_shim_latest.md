# NotebookLM — Normalization Shim

**Generated**: 2026-07-05
**Phase**: I

## Status: NOTEBOOKLM_NORMALIZATION_SHIM_ACTIVE

## What Was Created

Script: `scripts/research/notebooklm_normalization_shim.py`

Converts legacy NotebookLM export format to unified scoring fields.

## Normalization Results

| Source File | Items Normalized |
|-------------|-----------------|
| final_daily_research_memory_latest.json | 25 |
| nexus_research_bundle_latest.json | 0 |
| **Total** | **25** |

## Route Distribution

| Route | Count |
|-------|-------|
| funding_credit | 17 |
| stripe_payments | 7 |
| client_portal | 1 |
| hermes | 0 |
| alpha | 0 |
| creative | 0 |
| research | 0 |
| operations | 0 |
| telegram | 0 |
| scheduler_recovery | 0 |

## Output Files

| File | Path |
|------|------|
| Sources | data/research_memory/notebooklm_sources_latest.json |
| Scored Items | data/research_memory/notebooklm_scored_items_latest.json |
| Alpha Intake | reports/research/nexus_notebooklm_alpha_intake_latest.json |

## Unified Scoring Fields

All 17 fields mapped:
- source_id, source_type, title, source_path_or_url, captured_at
- summary, monetization_score, implementation_effort, urgency
- confidence, risk_level, relevance_to_nexus
- recommended_route, current_decision, next_action
- citations_or_receipts, status

## How to Re-Run

```bash
python3 scripts/research/notebooklm_normalization_shim.py
```
