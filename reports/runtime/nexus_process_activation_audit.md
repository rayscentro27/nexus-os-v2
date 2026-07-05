# Nexus Process Activation Audit

**Generated**: 2026-07-05

---

## Process-by-Process Activation Classification

### OBSERVE (Read-only, safe to run)

| Process | File | Why Observe |
|---------|------|-------------|
| Supabase Client reads | `src/lib/supabaseClient.ts` | Frontend reads only, anon key |
| DB Service reads | `src/services/db.ts` | Admin reads only, requires auth |
| Hermes Context Adapter | `src/lib/hermesSupabaseContextAdapter.ts` | READ from 11 tables |
| Client Dashboard Data | `src/services/clientDashboardLiveData.ts` | READ from 3 tables |
| YouTube metadata cache | `data/cache/youtube/` | Local files, no external action |
| NotebookLM exports | `data/exports/notebooklm/` | Local files, no external action |
| Report index reading | `reports/manual_publish/report_registry_latest.md` | Read-only |
| Config reading | `configs/*.json` | Read-only |

### DRY_RUN (Generate without sending)

| Process | File | Why Dry Run |
|---------|------|-------------|
| Department Feeders (18) | `src/config/nexusDepartmentFeeders.ts` | Would write to Supabase via service role |
| Social publish job | `scripts/run_social_publish_job.py` | Would post to Meta platforms |
| Nexus runner | `scripts/nexus_runner.py` | Would process agent jobs |
| Email sending (Resend) | Via env `RESEND_API_KEY` | Would send real emails |
| YouTube research scripts | `scripts/research/` | Would call YouTube API |
| Research-to-money pipeline | `scripts/research/` | Would generate reports |
| Opportunity scoring | `src/hermes/alpha/alphaScoring.ts` | Would score opportunities |
| Report generation | `scripts/reports/` | Would write report files |

### SANDBOX_TEST (Test mode, synthetic data)

| Process | File | Why Sandbox |
|---------|------|-------------|
| Seed day 1 event | `scripts/seed_day1_event.py` | Writes to Supabase, test data |
| Seed premium foundation | `scripts/seed_premium_foundation.py` | Bulk seed, test data |
| Seed static data | `scripts/supabase/seed_static_data_to_supabase.py` | Static data push |
| Alpha Search | `netlify/functions/alpha-search.mjs` | SearXNG proxy, test query |
| Alpha URL Review | `netlify/functions/alpha-url-review.mjs` | Firecrawl proxy, test URL |
| Alpha Provider | `netlify/functions/alpha-provider.mjs` | LLM proxy, test prompt |
| Hermes Chat (Edge) | `supabase/functions/hermes-chat/index.ts` | LLM proxy, test message |
| Hermes Search (Edge) | `supabase/functions/hermes-search/index.ts` | Search proxy, test query |
| Oanda demo trading | `scripts/trading/` | Demo account, no real money |
| Trading research pipeline | `src/hermes/alpha/alphaTradingResearchPipeline.ts` | Research only |
| Full activation script | `scripts/activation/run_nexus_full_activation.py` | --run-all flag |
| Continuous loop | `scripts/activation/run_nexus_continuous_loop.py` | --safe-internal flag |

### APPROVED_LIVE (Production ready)

| Process | File | Why Live |
|---------|------|----------|
| Got Funding landing page | Netlify deployment | Deployed, form works, tested |
| Vite dev server | `npm run dev` | Local development |
| Vite build | `npm run build` | Production build |
| Test suite | `npm run test` | Validation |

---

## Processes That Cannot Run Safely Now

| Process | Blocker | Recommendation |
|---------|---------|----------------|
| TikTok posting | No code exists | Build in Prompt 2 |
| Credit report upload | No upload mechanism | Build in Prompt 2 |
| Grant application draft | No generation code | Build in Prompt 2 |
| Referral tracking | No tracking code | Build in Prompt 2 |
| Live trading | `LIVE_TRADING=false` by design | Keep disabled |
