# Nexus Phase 2 Activation Baseline

**Generated:** 2026-07-01T19:45:00Z
**Data Sources:** nexus_operations_status, nexus_process_inventory, nexus_scheduler_inventory, hermes_operations_status

---

## Summary

| Metric | Count |
|--------|-------|
| Total sections | 14 |
| Live (verified) | 5 |
| Incomplete | 10 |
| Proof: verified | 5 |
| Proof: no_proof | 6 |
| Proof: unproven | 2 |
| Proof: not_proven_live | 2 |

---

## Incomplete Sections

### 1. Trading Lab (`trading_lab`)

- **Source Mode:** static
- **Proof Level:** no_proof
- **Processes:** pid-588 (nexus_trading_engine.py) — live running, PID 588 uptime 20:17:39
- **Schedulers:** demo-trading-loop loaded but no active PID proof
- **Tables:** None
- **Blockers:** No Supabase table, UI uses inline static data
- **Safe Plan:** Wire trading_lab section to Supabase; verify demo-trading-loop execution via log proof
- **Risky Blocked:** Enable live trading, connect funded broker

### 2. System Health (`system_health`)

- **Source Mode:** static
- **Proof Level:** no_proof
- **Processes:** None
- **Tables:** None
- **Blockers:** Uses systemHealthData.js, no live process monitoring
- **Safe Plan:** Seed System Health table from operations status reports
- **Risky Blocked:** Auto-restart processes from UI

### 3. Automation Scheduler (`automation`)

- **Source Mode:** static
- **Proof Level:** unproven
- **Schedulers:** 30+ launchd schedulers inventoried
- **Tables:** None
- **Blockers:** Schedulers loaded but no active PID proof for most
- **Safe Plan:** Wire scheduler status to Supabase; add process proof collection
- **Risky Blocked:** Auto-load/unload schedulers from UI

### 4. Reports (`reports`)

- **Source Mode:** static
- **Proof Level:** no_proof
- **Tables:** None
- **Blockers:** Reads local files only, uses reportRegistryData.js
- **Safe Plan:** Seed report registry to Supabase; wire UI to live reads
- **Risky Blocked:** Auto-delete old reports

### 5. Settings (`settings`)

- **Source Mode:** static
- **Proof Level:** no_proof
- **Tables:** None
- **Blockers:** No Supabase table, no data file
- **Safe Plan:** Create config status table; show presence by name only, never values
- **Risky Blocked:** Write secret values from UI

### 6. CLI / Tool Registry (`cli_registry`)

- **Source Mode:** static
- **Proof Level:** unproven
- **Tables:** None
- **Blockers:** CLI inventory exists locally but not wired to UI
- **Safe Plan:** Seed CLI inventory to Supabase; never expose auth tokens
- **Risky Blocked:** Execute CLI commands from UI

### 7. Credit & Funding (`credit_funding`)

- **Source Mode:** static
- **Proof Level:** no_proof
- **Tables:** None
- **Blockers:** Uses creditFundingData.js, no live broker connection
- **Safe Plan:** Create credit_funding_readiness table; seed workflow checklist
- **Risky Blocked:** Submit credit applications, connect live broker

### 8. Marketing Drafts (`marketing_drafts`)

- **Source Mode:** static
- **Proof Level:** no_proof
- **Tables:** None
- **Blockers:** No Supabase table, no draft workflow data
- **Safe Plan:** Create marketing_drafts table; wire approval-gated workflow
- **Risky Blocked:** Auto-publish drafts, send marketing emails

### 9. YouTube Research (`youtube_research`)

- **Source Mode:** static
- **Proof Level:** not_proven_live
- **Tables:** research_sources (52 rows)
- **Schedulers:** com.nexus.youtube-channel-poller (loaded)
- **Blockers:** No proof of recent YouTube metadata fetch, no transcript extraction proof
- **Safe Plan:** Add execution logging; verify fetch proof via log timestamps
- **Risky Blocked:** Auto-download transcripts, auto-post content

### 10. Hermes Live Model (`hermes_live_model`)

- **Source Mode:** static
- **Proof Level:** not_proven_live
- **Processes:** pid-618 (hermes_cli gateway) — live running, PID 618 uptime 20:17:39
- **Blockers:** LLM provider not configured, VITE_HERMES_SEARCH_ENABLED not set
- **Safe Plan:** Configure LLM provider in Edge Function; enable web search env var
- **Risky Blocked:** Send unfiltered prompts to external API

---

## Critical Note

Do not claim a section is live unless verified by Supabase read, process evidence, or log proof. Use "not_proven_live" when proof is missing.
