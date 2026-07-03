# Nexus Legacy Folder Audit

**Generated**: 2026-07-03

---

## Folders Found

### 1. `~/nexus-ai` (Active)
- **Git**: Yes, branch `master`
- **Size**: Large (50+ subdirectories)
- **Running**: Yes — control_center_server on port 4000
- **launchd jobs**: 15+ jobs reference this path
- **Contents**: Full autonomous business system (Python + Node.js)
- **Status**: OPERATIONAL — do not modify without explicit approval

### 2. `~/nexuslive`
- **Git**: Yes, branch `master`
- **Running**: No
- **Contents**: Legacy web application
- **Status**: DORMANT

### 3. `~/nexus`
- **Git**: Yes, branch `master`
- **Running**: No
- **Contents**: Legacy codebase
- **Status**: DORMANT

### 4. `~/nexus-ai-council-sandbox`
- **Git**: Unknown
- **Running**: No
- **Contents**: Sandbox environment
- **Status**: DORMANT

### 5. `~/nexus-ai/trading-engine`
- **Git**: Part of nexus-ai
- **Running**: No (launchd job exists but not active)
- **Contents**: Full trading engine with backtester, broker API, tournament
- **Config**: `trading_config.json` — Oanda demo, live_trading=false, auto_trading=false
- **Status**: CONFIGURED FOR DEMO ONLY

### 6. `~/nexus-os-v2` (Current)
- **Git**: Yes, branch `master`
- **Running**: opencode session
- **Contents**: Hermes Alpha + $97 delivery kit
- **Status**: ACTIVE DEVELOPMENT

---

## Cross-References

- `nexus-ai` references `nexus-os-v2` via Hermes gateway (`http://127.0.0.1:8642`)
- `nexus-os-v2` references `nexus-ai` via cloudflare tunnel config
- Both share Supabase instance (`ygqglfbhxiumqdisauar.supabase.co`)
- Both share Oanda demo account (`101-001-27557105-003`)
- Both share Groq API key for LLM inference

---

## Recommendations

1. **Do not delete** any legacy folders — they contain operational systems
2. **Do not modify** `~/nexus-ai` without explicit approval — 15+ launchd jobs depend on it
3. **Hermes Alpha** should treat `~/nexus-ai` as a reference architecture, not a dependency
4. **Shared resources** (Supabase, Oanda, Groq) should be accessed via environment variables, not hardcoded paths
