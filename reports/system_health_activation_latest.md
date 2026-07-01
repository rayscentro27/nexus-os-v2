# System Health Activation Latest

**Generated:** 2026-07-01T19:45:00Z
**Data Sources:** operations status, process inventory, scheduler inventory, hermes status, model infrastructure

---

## Last Audit

- **Audit ID:** ops-20260701T193927Z
- **Checked At:** 2026-07-01T19:39:27Z
- **Version:** 1.0

---

## Build Status

| Item | Status |
|------|--------|
| Last Build Report | 2026-06-29T15:52:19Z |
| Build Command | `tsc --noEmit && vite build` |
| Typecheck | `tsc --noEmit` |
| Status | last_known_passing |
| Proof Level | no_proof |

---

## Test Status

| Test | Status | PID | Uptime |
|------|--------|-----|--------|
| hermes-live | Active | 87534 | 03:25:09 |

---

## Supabase Status

| Item | Value |
|------|-------|
| Last Known Write | 2026-07-01 |
| Last 24h Writes | 27 |
| Last 7d Writes | 149 |
| Total Rows | 732 |
| RLS Enabled | Yes |
| Service Role Present | Yes |
| URL Present | Yes |

### Tables Written

- task_requests
- business_opportunities
- monetization_opportunities
- client_profiles
- research_sources
- nexus_events

---

## Model Status

### Ollama

| Item | Value |
|------|-------|
| Installed | Yes |
| Running | Yes |
| Endpoint | http://127.0.0.1:11434 |
| Models | qwen2.5:0.5b, gemma4:31b-cloud, gemma3:1b |
| Endpoint Responding | Yes |

### Oracle

| Item | Value |
|------|-------|
| CLI Installed | No |
| Config Exists | Yes |
| VM Reachable | Yes |
| Hostname | nexus-llm-worker |

### OpenRouter

| Item | Value |
|------|-------|
| API Key Present | Yes |
| Model Endpoint Configured | No |

### Hermes

| Item | Status |
|------|--------|
| Live Model | not_configured |
| Web Search | not_configured |

---

## Scheduler Summary

| Metric | Count |
|--------|-------|
| Total Schedulers | 31 |
| Installed & Loaded | 28 |
| Installed & Not Loaded | 3 |
| Active Now (PID Proof) | 0 |

---

## Process Summary

| Metric | Count |
|--------|-------|
| Total Processes | 16 |
| Active (PID Proof) | 14 |
| Recent Output Only | 1 |
| Not Found | 0 |
| Unknown | 1 |

---

## CLI Summary

| Metric | Value |
|--------|-------|
| Total Tools | 11 |
| Installed | 11 |
| Authenticated | not_proven |

---

## Environment Variables

| Variable | Present |
|----------|---------|
| SUPABASE_URL | Yes |
| SUPABASE_SERVICE_ROLE_KEY | Yes |
| VITE_SUPABASE_URL | Yes |
| VITE_SUPABASE_ANON_KEY | Yes |
| OPENROUTER_API_KEY | Yes |
| ANTHROPIC_API_KEY | No |
| OPENAI_API_KEY | No |
| HERMES_LLM_PROVIDER | No |
| VITE_HERMES_SEARCH_ENABLED | No |
| OLLAMA_HOST | No |

---

## Blockers

1. YouTube research not proven live
2. Hermes live model not configured
3. Hermes web search not configured
4. Background processes write local JSON only
5. Trading Lab, System Health, Automation, Reports, Settings, CLI still use static data
6. System Health not wired to Supabase

## Next Actions

1. Verify YouTube research scheduler loads and runs
2. Configure Hermes live model (LLM provider)
3. Enable Hermes web search (VITE_HERMES_SEARCH_ENABLED)
4. Seed System Health and Reports tables
5. Wire remaining static sections to Supabase
