# Hermes 0.20.6 Feature Inventory — 2026-08-29

All meaningful campaign-scope features have a deterministic disposition; none
is left `UNKNOWN`.

| Feature | Hermes native | Current status | Nexus equivalent | Disposition |
|---|---|---|---|---|
| Conversations | Yes | certified | Nexus advisory conversation route | USE_AS_IS |
| Persistent sessions | Yes | certified | TruthKernel receipts remain separate | USE_AS_IS |
| Built-in memory | Yes | certified with synthetic marker | Nexus decision memory | WRAP_WITH_NEXUS |
| Profiles | Yes | default + secondary profile proven | Nexus role/policy context | USE_AS_IS |
| Skills / AgentSkills | Yes | bundled sync and API inventory proven | Nexus allowlist/receipts | WRAP_WITH_NEXUS |
| Gateway API | Yes | authenticated loopback API certified | Nexus bridge | WRAP_WITH_NEXUS |
| Provider routing | Yes | single approved Ollama route | Nexus provider policy | WRAP_WITH_NEXUS |
| Retries/fallbacks | Yes | native support available; no paid fallback activated | Nexus fail-closed retry policy | WRAP_WITH_NEXUS |
| Ollama | Yes | `gemma3:4b` reasoning certified | existing Oracle service | USE_AS_IS |
| Browser/web | Yes | disabled in API toolsets | Nexus research wrapper | WRAP_WITH_NEXUS |
| Search | Yes | no Hermes web tool enabled | existing SearXNG/Nexus research | KEEP_NEXUS_VERSION |
| Image tooling | Yes | no provider/credential activated | Nexus media policy | BLOCKED_EXTERNAL_DEPENDENCY |
| TTS | Yes | disabled; no voice activation | Nexus voice policy | BLOCKED_EXTERNAL_DEPENDENCY |
| Microphone/voice | Yes | disabled | Nexus voice policy | KEEP_NEXUS_VERSION |
| Telegram/Discord/Slack/WhatsApp/Teams gateways | Yes | not configured | Nexus Telegram authority route | BLOCKED_EXTERNAL_DEPENDENCY |
| MCP | Yes | disabled; no servers configured | Nexus approved-tool boundary | WRAP_WITH_NEXUS |
| Subagents/delegation | Yes | disabled | Nexus worker/work-order governance | KEEP_NEXUS_VERSION |
| Kanban/workers | Yes | startup component present; no autonomous authority | Nexus work orders | KEEP_NEXUS_VERSION |
| Terminal backends | Yes | disabled in API platform | deterministic Nexus Python | WRAP_WITH_NEXUS |
| `execute_code` | Yes | disabled | Nexus deterministic execution | KEEP_NEXUS_VERSION |
| Cron/routines | Yes | disabled | Nexus scheduler/gates | KEEP_NEXUS_VERSION |
| Hooks | Yes | no external hooks activated | Nexus receipts | WRAP_WITH_NEXUS |
| Research tools | Yes | not enabled in minimum profile | Nexus/SearXNG research | KEEP_NEXUS_VERSION |
| Trajectory export | Yes | available, not enabled | Nexus evidence artifacts | WRAP_WITH_NEXUS |
| Dashboard | Yes | disabled; no dashboard listener | Nexus control UI | KEEP_NEXUS_VERSION |
| SSH-backed execution | Yes | disabled | Nexus private transport only | KEEP_NEXUS_VERSION |
| Local API sessions/runs | Yes | session endpoints certified | Nexus request correlation | WRAP_WITH_NEXUS |
