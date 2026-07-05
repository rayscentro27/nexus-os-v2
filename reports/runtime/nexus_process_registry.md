# Nexus Process Registry

**Generated**: 2026-07-05

---

## Active Processes Discovered

### Python Scripts (scripts/)

| Process ID | File | Department | Can Run Now |
|-----------|------|-----------|-------------|
| seed_day1 | `scripts/seed_day1_event.py` | System | Yes (needs SUPABASE keys) |
| seed_premium | `scripts/seed_premium_foundation.py` | System | Yes (needs SUPABASE keys) |
| seed_static | `scripts/supabase/seed_static_data_to_supabase.py` | System | Yes (needs SUPABASE keys) |
| nexus_runner | `scripts/nexus_runner.py` | System | Yes (needs SUPABASE keys) |
| social_publish | `scripts/run_social_publish_job.py` | Marketing | Yes (needs META tokens) |
| nexus_ops | `scripts/run_nexus_continuous_operations.py` | System | Yes (manual mode) |
| nexus_overnight | `scripts/run_nexus_overnight_safe_ops.py` | System | Yes |
| nexus_activate | `scripts/activation/run_nexus_full_activation.py` | System | Yes (--run-all) |
| nexus_loop | `scripts/activation/run_nexus_continuous_loop.py` | System | Yes (--safe-internal) |
| model_router | `scripts/model_router.py` | Alpha | Yes (test mode) |

### Package.json Scripts

| Command | Purpose | Can Run Now |
|---------|---------|-------------|
| `npm run dev` | Vite dev server | Yes |
| `npm run build` | TypeScript + Vite build | Yes |
| `npm run test` | Vitest test suite | Yes |
| `npm run preview` | Preview production build | Yes |
| `npm run typecheck` | TypeScript check | Yes |
| `npm run test:hermes-live` | Hermes live question test | Yes (needs Ollama) |
| `npm run seed:day1` | Seed day 1 event | Yes (needs Python + SUPABASE) |
| `npm run nexus:watch` | Manual operations | Yes |
| `npm run nexus:overnight` | Overnight safe ops | Yes |
| `npm run nexus:activate` | Full activation | Yes |
| `npm run nexus:loop` | Continuous loop | Yes |

### LaunchD Schedulers

| Process ID | Plist | Status |
|-----------|-------|--------|
| continuous_loop | `com.nexus.continuous-loop.plist` | Active |
| daily_operating | `com.nexus.daily-operating.plist` | Active |
| evening_closeout | `com.nexus.evening-closeout.plist` | Active |
| operational_research | `com.nexus.operational-research-cycle.plist.disabled` | DISABLED |

### Netlify Functions

| Process ID | Function | Route |
|-----------|----------|-------|
| alpha_search | `netlify/functions/alpha-search.mjs` | `/api/alpha/search` |
| alpha_url_review | `netlify/functions/alpha-url-review.mjs` | `/api/alpha/url-review` |
| alpha_provider | `netlify/functions/alpha-provider.mjs` | `/api/alpha/*` |

### Supabase Edge Functions

| Process ID | Function | Purpose |
|-----------|----------|---------|
| hermes_chat | `supabase/functions/hermes-chat/index.ts` | LLM chat proxy |
| hermes_search | `supabase/functions/hermes-search/index.ts` | Web search proxy |
