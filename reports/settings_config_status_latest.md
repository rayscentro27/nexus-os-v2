# Settings Config Status Latest

**Generated:** 2026-07-01T19:45:00Z
**Data Sources:** operations status, hermes status, model infrastructure

---

## Policy

**Show presence by name only. Never print values.**

---

## Config Status

| Config | Present | Proof Level | Blockers |
|--------|---------|-------------|----------|
| supabase | Yes | verified | None |
| hermes_chat | No | verified | LLM provider not configured |
| hermes_model | No | verified | HERMES_MODEL_PROVIDER missing |
| hermes_search | No | verified | VITE_HERMES_SEARCH_ENABLED not set |
| netlify | Yes | installed_only | None |
| oanda | No | not_proven_live | No proof of configuration |
| youtube | Yes | verified | No proof of recent fetch |
| openrouter | Yes | verified | None |

---

## Details

### supabase
- **Status:** Present
- **Proof:** SUPABASE_URL=true, SUPABASE_SERVICE_ROLE_KEY=true
- **Next:** Verify connection health

### hermes_chat
- **Status:** Missing
- **Proof:** HERMES_LLM_PROVIDER=false
- **Next:** Configure LLM provider in Edge Function secrets

### hermes_model
- **Status:** Missing
- **Proof:** HERMES_MODEL_PROVIDER=false, OPENROUTER_API_KEY=true
- **Next:** Set HERMES_MODEL_PROVIDER env var

### hermes_search
- **Status:** Missing
- **Proof:** VITE_HERMES_SEARCH_ENABLED=false
- **Next:** Set VITE_HERMES_SEARCH_ENABLED=true

### netlify
- **Status:** Installed
- **Proof:** CLI available at node path
- **Next:** Verify authentication status

### oanda
- **Status:** Not proven
- **Proof:** None
- **Next:** Verify Oanda demo account credentials if needed

### youtube
- **Status:** Present
- **Proof:** Scheduler installed
- **Next:** Verify YouTube API key and scheduler execution

### openrouter
- **Status:** Present
- **Proof:** OPENROUTER_API_KEY=true
- **Next:** Configure model endpoint to use OpenRouter

---

## Summary

| Metric | Count |
|--------|-------|
| Total Configs | 8 |
| Present | 4 |
| Missing | 4 |

---

**Critical:** Config values are never printed. Only presence by name is shown.
