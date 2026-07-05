# NotebookLM — Existing Parser Audit

**Generated**: 2026-07-05
**Phase**: F

## Summary

| Field | Value |
|-------|-------|
| Scripts Found | 21 in scripts/activation/ |
| Access Mode | legacy_adapter |
| CLI Callable | NO |
| Legacy Adapter Callable | YES |
| Browser Automation | NOT ALLOWED |
| Export Bundles | 3 files in data/exports/notebooklm/ |
| Research Reports | 10 in reports/research/ |
| Scoring Thresholds | Documented in reports/research/nexus_research_scoring_thresholds.md |

## Existing Scripts (DO NOT REBUILD)

| Script | Purpose | Status |
|--------|---------|--------|
| notebooklm_connector_common.py | Shared: CLI discovery, legacy adapter, env check | COMPLETE |
| audit_notebooklm_access.py | Audits API access | COMPLETE |
| list_notebooklm_notebooks.py | Lists notebooks | COMPLETE |
| audit_old_notebooklm_connector.py | Audits legacy connector | COMPLETE |
| run_notebooklm_source_import.py | Source import | COMPLETE |
| recover_notebooklm_legacy_adapter.py | Legacy adapter recovery | COMPLETE |
| export_youtube_bundle_for_notebooklm.py | YouTube bundle export | COMPLETE |
| connect_notebooklm_notebook_to_lane.py | Notebook-lane connection | COMPLETE |
| build_notebooklm_automation_registry.py | Automation registry | COMPLETE |
| notebooklm_legacy_adapter_v2.py | Legacy adapter v2 | COMPLETE |
| audit_notebooklm_automation_options.py | Automation options | COMPLETE |
| validate_notebooklm_tool_access.py | Tool access validation | COMPLETE |
| build_notebooklm_hermes_brief.py | Hermes brief builder | COMPLETE |
| connect_notebooklm_selected_notebooks.py | Selected notebook connection | COMPLETE |
| build_notebooklm_ray_review_cards.py | Ray review cards | COMPLETE |
| export_research_bundle_for_notebooklm.py | Research bundle export | COMPLETE |
| build_notebooklm_research_memory.py | Research memory builder | COMPLETE |
| prepare_notebooklm_dropzone.py | Dropzone preparation | COMPLETE |
| build_oanda_vibe_notebooklm_activation_reports.py | OANDA/Vibe reports | COMPLETE |
| sync_selected_notebooklm_notebooks.py | Notebook sync | COMPLETE |
| find_notebooklm_cli_connectors.py | CLI connector discovery | COMPLETE |

## Existing Export Format

Current NotebookLM export (`final_daily_research_memory_latest.json`):
```json
{
  "generated_at": "...",
  "source_count": N,
  "opportunity_count": N,
  "lane_summary": {...},
  "top_opportunities": [...],
  "safety": {...}
}
```

## Current Nexus Scoring Format (Alpha/Research)

| Factor | Range | Description |
|--------|-------|-------------|
| Content Quality | 0-30 | Transcript quality, source credibility, density, actionability |
| Relevance | 0-25 | Match to Nexus topics, timeliness, uniqueness |
| Monetization Potential | 0-25 | Revenue clarity, complexity, time to value, scalability |
| Actionability | 0-20 | Next steps, resources, risk, dependencies |

**Total**: 0-100

| Score Range | Classification | Action |
|-------------|---------------|--------|
| 0-39 | Low value | Archive only |
| 40-59 | Medium value | Research archive |
| 60-79 | Opportunity candidate | Alpha/Hermes visibility |
| 80-100 | High value | Ray Review required |

## Proposed Unified Scoring Fields

| Field | NotebookLM Has? | Nexus Alpha Has? | Alignment |
|-------|----------------|-----------------|-----------|
| source_id | via filename | Yes | ALIGNED |
| title | via filename | Yes | ALIGNED |
| source_type | Not explicit | Yes | NEEDS MAPPING |
| captured_at | generated_at | Yes | ALIGNED |
| summary | Not in export | Yes | NEEDS ADDITION |
| monetization_score | Not in export | Yes (0-25) | NEEDS MAPPING |
| implementation_effort | Not in export | Yes | NEEDS MAPPING |
| urgency | Not in export | Yes | NEEDS MAPPING |
| confidence | Not in export | Yes | NEEDS MAPPING |
| risk_level | safety section | Yes | NEEDS MAPPING |
| relevance_to_nexus | lane_summary | Yes (0-25) | NEEDS MAPPING |
| recommended_route | Not in export | Yes | NEEDS ADDITION |
| current_decision | Not in export | Yes | NEEDS ADDITION |
| next_action | Not in export | Yes | NEEDS ADDITION |
| citations_or_receipts | Not in export | Yes | NEEDS ADDITION |
| status | Not in export | Yes | NEEDS ADDITION |

## Alignment Gap

NotebookLM exports use a different format than Nexus Alpha scoring. The `top_opportunities` array contains opportunities but not in the unified scoring format. The `lane_summary` provides routing info but not field-by-field alignment.

## What Already Works

1. 21 scripts for NotebookLM automation
2. Legacy adapter is callable
3. Export bundles exist with data
4. Scoring thresholds documented
5. Automation registry ready
6. Watched folders configured

## What Needs Alignment

1. Map NotebookLM `top_opportunities` fields to unified scoring format
2. Add missing fields (summary, recommended_route, current_decision, next_action, citations, status)
3. Create a normalization layer between NotebookLM export and Nexus Alpha intake

## Recommendation

DO NOT rebuild the parser. Create a small normalization shim that:
1. Reads NotebookLM export bundles
2. Maps fields to unified scoring format
3. Writes to `data/research_memory/notebooklm_scored_items_latest.json`

## Final Status

**NOTEBOOKLM_EXISTING_PARSER_ALIGNED** — 21 scripts exist, legacy adapter works, export bundles present. Scoring alignment needs a normalization shim, not a rebuild.
