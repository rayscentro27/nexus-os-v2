# Nexus Existing System Process CLI Audit

**Generated**: 2026-07-03  
**Repo**: `~/nexus-os-v2` (git, branch `master`, clean, commit `5999e1d`)  
**Tested**: 794/794 passing, build clean

---

## Summary

This audit catalogs every running process, installed CLI, launchd job, and integration found on the Mac Mini host. It serves as the foundation for determining what Hermes Alpha can reuse, what must be adapted, and what must be built from scratch.

---

## 1. Running Processes

| Process | PID | CPU | Notes |
|---------|-----|-----|-------|
| `opencode` | 26324 | 100% | Current session tool |
| `cloudflared` | 12035 | 0.0% | Hermes gateway tunnel |
| `nexus-ai control_center_server` | 23097 | 0.0% | Port 4000, Python Flask |

**Key finding**: Only 3 processes running. The legacy Nexus AI stack is mostly dormant — launchd jobs exist but are not actively running (no `KeepAlive` success in most cases).

---

## 2. launchd Jobs (25+ found)

### Active / Running
| Job | Status | Path |
|-----|--------|------|
| `ai.hermes.gateway` | Running | `~/.hermes/start_gateway.sh` |
| `cf.hermes.gateway` | Running | `cloudflared tunnel` |
| `com.raymonddavis.nexus.control-center` | Running | `control_center_server.py` (port 4000) |

### Installed but Not Running
| Job | Purpose |
|-----|---------|
| `com.nexus.trading-engine` | Oanda trading engine (Python) |
| `com.nexus.research-worker` | Research job worker (Node.js) |
| `com.nexus.research-signal-bridge` | Research→Signal bridge (Python) |
| `com.nexus.signal-router` | TradingView signal router (Python) |
| `com.nexus.orchestrator` | Event orchestrator (Node.js) |
| `com.nexus.auto-executor` | Auto trade executor (Python) |
| `com.nexus.tournament` | Strategy tournament (Python) |
| `com.nexus.ollama` | Local LLM server |
| `com.nexus.mac-mini-worker` | Mac Mini job worker (Node.js) |
| `com.nexus.signal-review` | Signal review (Bash) |
| `com.raymonddavis.nexus.scheduler` | Operations scheduler (Python) |
| `com.raymonddavis.nexus.dashboard` | Dashboard server (Python) |
| `com.raymonddavis.nexus.autonomy-worker` | Autonomy worker (Python) |
| `com.raymonddavis.nexus.email-pipeline` | Email pipeline (Python) |
| `com.raymonddavis.nexus.monitoring-worker` | Monitoring worker (Python) |
| `com.nexus.continuous-ops-daily` | Daily ops cron |
| `com.nexus.evening-closeout` | Evening closeout cron |
| `com.raymonddavis.ollama` | Ollama (duplicate) |

**Key finding**: 25+ launchd jobs registered. Most are for the legacy Nexus AI Python stack in `~/nexus-ai`. Only 3 are actually running.

---

## 3. Installed CLIs

| CLI | Version | Path |
|-----|---------|------|
| Node.js | v22.22.3 | `/Users/raymonddavis/.nvm/versions/node/v22.22.3/bin/node` |
| npm | 10.9.3 | nvm-managed |
| Python3 | (system) | `/usr/local/bin/python3` |
| Git | 2.43.0 | `/usr/local/bin/git` |
| GitHub CLI | 2.76.2 | nvm-managed |
| Ollama | 0.14.0 | `/usr/local/bin/ollama` |
| ripgrep | 14.1.1 | nix-profile |
| Cloudflared | 2026.2.1 | `/usr/local/bin/cloudflared` |

**Key finding**: Node 22, Python 3, Git, GitHub CLI, Ollama, ripgrep, cloudflared all available. No Claude Code CLI (opencode used instead).

---

## 4. Existing Integrations

| Integration | Status | Location |
|-------------|--------|----------|
| **Supabase** | Configured | `ygqglfbhxiumqdisauar.supabase.co` |
| **Stripe** | Test mode | Config in env vars |
| **Resend** | Blocked (403) | Cannot send emails |
| **Cloudflare Tunnel** | Active | `hermes-gateway` tunnel |
| **Ollama** | Installed, launchd job exists | Port 11434 |
| **YouTube API** | Cached data exists | `data/cache/youtube/` |
| **Netlify** | Config exists | Deploy scripts |
| **Oanda** | Demo account configured | `101-001-27557105-003` |
| **Groq** | API key in env vars | llama-3.3-70b-versatile |

---

## 5. Nexus AI Legacy Stack (`~/nexus-ai`)

Full Python-based autonomous business system:
- `control_center/` — Flask server (port 4000)
- `trading-engine/` — Oanda trading with tournament
- `research_intelligence/` — Research signal bridge
- `signal-router/` — TradingView signal routing
- `services/` — Node.js workers (research, orchestrator)
- `operations_center/` — Scheduler
- `dashboard.py` — Dashboard server
- `autonomy/` — Autonomy worker
- `funding_engine/`, `funnel_engine/`, `ad_engine/` — Business units

**Key finding**: This is a complete, operational autonomous business system. Hermes Alpha should leverage its patterns rather than rebuild.

---

## 6. Hermes Alpha Existing Assets

| Asset | Location | Status |
|-------|----------|--------|
| 50+ Reports | `reports/hermes_alpha/` | Created |
| Research Inbox | `hermes_alpha/research_inbox/` | 8 subdirectories (README placeholders) |
| Eval Framework | `hermes_alpha/evaluations/` | Phase 1 fixtures complete |
| Ollama Plan | `reports/hermes_alpha/hermes_alpha_ollama_provider_plan.md` | Complete |
| Affiliate Lab | `reports/hermes_alpha/affiliate_offer_lab_plan.md` | Complete |
| Marketing Dept | `reports/hermes_alpha/hermes_alpha_marketing_dept_design.md` | Complete |

---

## 7. Recommendations for Hermes Alpha

1. **Reuse**: Supabase client, Cloudflare tunnel pattern, Ollama integration, Groq API
2. **Adapt**: Trading engine patterns → funding engine patterns, research worker → content worker
3. **Build**: Vibe-trading adapter (empty), marketing dept (design exists), business opportunity desk (design exists)
4. **Do not rebuild**: Control center, signal routing, tournament — these work in legacy stack
