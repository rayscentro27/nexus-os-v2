# Nexus Process Receipt Standard

**Generated**: 2026-07-05

---

## Standard Receipt Shape

Every Nexus process should produce a receipt in this format:

```json
{
  "process_id": "",
  "department": "",
  "activation_mode": "",
  "last_run_time": "",
  "input_source": "",
  "output_files": [],
  "supabase_project": "",
  "supabase_tables": [],
  "ui_visibility": "",
  "alpha_visibility": "",
  "nexus_hermes_visibility": "",
  "external_action_taken": false,
  "cost_estimate": "",
  "errors": [],
  "score": 0,
  "recommendation": "",
  "ray_review_required": false,
  "next_action": ""
}
```

---

## Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `process_id` | string | Unique identifier for the process |
| `department` | string | Which department owns this process |
| `activation_mode` | enum | OBSERVE / DRY_RUN / SANDBOX_TEST / APPROVED_LIVE |
| `last_run_time` | ISO 8601 | When the process last ran |
| `input_source` | string | Where input data comes from |
| `output_files` | string[] | Files produced by the process |
| `supabase_project` | string | Which Supabase project (or "none" / "local_only") |
| `supabase_tables` | string[] | Tables read/written |
| `ui_visibility` | string | Where output appears in Nexus OS2 UI |
| `alpha_visibility` | string | Whether Alpha brain can see the output |
| `nexus_hermes_visibility` | string | Whether Hermes can route to this process |
| `external_action_taken` | boolean | Whether any real external action was performed |
| `cost_estimate` | string | Estimated cost (API calls, tokens, etc.) |
| `errors` | string[] | Any errors encountered |
| `score` | number | 0-100 readiness score |
| `recommendation` | string | What should happen next |
| `ray_review_required` | boolean | Whether Ray needs to review before proceeding |
| `next_action` | string | Specific next step |

---

## Receipt Validation Rules

1. `process_id` must be non-empty
2. `activation_mode` must be one of: OBSERVE, DRY_RUN, SANDBOX_TEST, APPROVED_LIVE
3. If `external_action_taken` is true, `ray_review_required` must be true
4. If `activation_mode` is APPROVED_LIVE, `score` must be >= 81
5. `output_files` should list actual file paths if files were generated
6. `errors` should be empty array if no errors occurred

---

## Example Receipts

### Got Funding Landing Page
```json
{
  "process_id": "got_funding_landing_page",
  "department": "marketing",
  "activation_mode": "APPROVED_LIVE",
  "last_run_time": "2026-07-05T00:00:00Z",
  "input_source": "netlify_deployment",
  "output_files": ["dist/got-funding/index.html"],
  "supabase_project": "none",
  "supabase_tables": [],
  "ui_visibility": "public_url",
  "alpha_visibility": "full",
  "nexus_hermes_visibility": "full",
  "external_action_taken": false,
  "cost_estimate": "netlify_free_tier",
  "errors": [],
  "score": 85,
  "recommendation": "monitor_form_submissions",
  "ray_review_required": false,
  "next_action": "verify_lead_capture_pipeline"
}
```

### YouTube Researcher
```json
{
  "process_id": "youtube_researcher",
  "department": "research",
  "activation_mode": "DRY_RUN",
  "last_run_time": "2026-07-04T00:00:00Z",
  "input_source": "data/cache/youtube/",
  "output_files": ["reports/manual_publish/youtube_research_*.md"],
  "supabase_project": "none",
  "supabase_tables": [],
  "ui_visibility": "research_panel",
  "alpha_visibility": "research_inbox",
  "nexus_hermes_visibility": "research_route",
  "external_action_taken": false,
  "cost_estimate": "youtube_api_quota",
  "errors": [],
  "score": 55,
  "recommendation": "connect_to_live_api",
  "ray_review_required": false,
  "next_action": "test_with_real_channel_query"
}
```
