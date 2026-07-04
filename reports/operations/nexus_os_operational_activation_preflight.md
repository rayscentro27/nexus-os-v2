# Nexus OS Operational Activation Preflight

> INTERNAL OPERATIONS — DRAFT ONLY — RAY REVIEW REQUIRED — NO REAL CLIENT DATA

- Branch: `main`
- Starting commit: `ffac2c8 finish local GoClear readiness research workflow foundation`
- Dirty files at lock:
```text
M data/cache/youtube/api_metadata/alec_delpuech.json
 M data/cache/youtube/api_metadata/credit_plug.json
 M data/cache/youtube/api_metadata/michael_ionita.json
 M data/cache/youtube/api_metadata/stedman_waiters.json
 M data/cache/youtube/api_metadata/video_zbAmmnMh5ew.json
 M data/exports/notebooklm/research_bundles/final_daily_research_memory_latest.json
 M reports/manual_publish/daily_operating_cycle_latest.md
 M reports/manual_publish/evening_closeout_cycle_latest.md
 M reports/manual_publish/research_to_money_pipeline_latest.md
 M reports/runtime/ray_review_queue_latest.json
 M src/admin/NexusAdminUI.jsx
?? reports/operations/
?? scripts/run_nexus_daily_closeout.ts
?? scripts/run_nexus_operational_cycle.py
?? scripts/run_nexus_research_cycle.ts
?? src/components/NexusOperationsPanel.jsx
?? src/hermes/alpha/alphaSeoMoneyOpportunityEngine.ts
?? src/hermes/alpha/alphaTradingResearchPipeline.ts
?? src/hermes/alpha/hermesAlphaOpportunityBrain.ts
?? src/hermes/nexus/affiliateApiSetupCenter.ts
?? src/hermes/nexus/hermesDualBrainRouter.ts
?? src/hermes/nexus/hermesNexusOperatorBrain.ts
?? src/hermes/nexus/marketingAssetStudio.ts
?? src/hermes/nexus/nexusAllDayResearchRunner.ts
?? src/hermes/nexus/nexusConnectorRegistry.ts
?? src/hermes/nexus/nexusOperationalMetrics.ts
?? src/hermes/nexus/nexusSchedulerRegistry.ts
```

## Current foundation

- Command Center, system health, reports, Ray Review, GoClear readiness, dual research layers, Alpha offline workroom, schedulers, trading demo tooling, marketing drafts, Supabase safety plans, Netlify config, YouTube cache, and NotebookLM exports already existed.
- UI entry point added: `#operations` / **Nexus Operations**.
- Hermes Nexus is the local/operator lane. Hermes Alpha remains separate, local-file oriented, no-Supabase, and client-data prohibited.
- Existing scheduler conventions are present; this sprint does not load launchd.
- Existing trading code includes Oanda practice/read and paper tooling; funded/live execution remains blocked.
- Existing connector references include Supabase, Netlify, GitHub, Resend, Meta, YouTube, NotebookLM, Stripe test, Oanda practice, OpenRouter, and local model routing.
- Safe to proceed: yes. Dirty files matched the user-declared runtime/cache set and were not modified by this cycle.
