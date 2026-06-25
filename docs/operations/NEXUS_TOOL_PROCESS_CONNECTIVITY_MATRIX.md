# Nexus Tool / Process / Integration Connectivity Matrix

Date: 2026-06-24

| Name | Category | Path/table/integration | How to run/use | Current state | Mac/local | Supabase | UI | Hermes | Reports | Proof | Approval | Safe now | Money | Auto | Research | Hermes | Priority | Smallest next step |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---|---|
| Vite app | Frontend | `src`, `vite.config.ts` | `npm run dev/build` | live | yes | yes | yes | partial | no | no | no | yes | 7 | 4 | 4 | 7 | now | keep deploy clean |
| Netlify deploy | Deploy | `netlify.toml`, GitHub | push `main` | live | no | no | public app | no | no | no | no | yes | 8 | 5 | 2 | 4 | now | add deploy status in UI |
| Supabase DB/Auth | Platform | migrations/functions | UI/scripts | live | partial | yes | yes | yes | no | yes | yes for writes | yes | 9 | 8 | 8 | 9 | now | keep RLS diagnostics visible |
| Hermes chat | Communication | `hermes-chat`, `hermesProviders.ts` | Command Center | live | no | partial | yes | yes | no | partial | task approval only | yes | 8 | 6 | 7 | 10 | now | show tool-readiness context |
| Hermes search | Search | `hermes-search` | disabled unless configured | disconnected/blocked | no | no | no | no | no | no | yes | no | 5 | 4 | 7 | 6 | later | deploy only after approval |
| Watch loop | Ops | `scripts/run_nexus_continuous_operations.py` | `npm run nexus:watch` | working manually | yes | yes | report-only | yes | yes | yes | no | yes | 9 | 8 | 6 | 9 | now | add UI run/status bridge |
| Overnight loop | Ops | `scripts/run_nexus_overnight_safe_ops.py` | `npm run nexus:overnight` | working manually | yes | yes | report-only | yes | yes | yes | no | with constraints | 7 | 8 | 5 | 8 | next | keep disabled by default |
| Nexus runner | Automation | `scripts/nexus_runner.py` | `--once --dry-run` | working manually | yes | yes | Agent Jobs | partial | no | yes | job dependent | dry-run yes | 8 | 9 | 6 | 8 | now | expose safe run button/bridge |
| Runner allowlist | Automation | `scripts/runner_handlers` | registry | live | yes | yes | no | partial | no | yes | yes for risky | yes | 7 | 9 | 6 | 8 | now | mirror registry to UI |
| Approvals | Gate | `approvals`, UI | Approvals tab | live | partial | yes | yes | yes read-only | no | yes | yes | yes | 9 | 7 | 5 | 9 | now | add completeness badges |
| Task requests | Gate | `task_requests` | Hermes approved task | scaffolded/live table empty | no | yes | no | yes | no | partial | yes | yes | 7 | 7 | 5 | 9 | next | add UI status list |
| Agent jobs | Queue | `agent_jobs` | UI queues/runner consumes | working manually | yes | yes | yes | partial | no | yes | risky jobs | dry-run yes | 8 | 9 | 6 | 8 | now | operator cards |
| Nexus events | Proof | `nexus_events` | scripts/UI writes | live | yes | yes | yes | yes | no | yes | no | yes | 7 | 8 | 6 | 9 | now | group/filter UI |
| Source intake capture | Research | `capture_intake_event.py`, `intake_events` | CLI | working manually | yes | yes | read-only table | partial | no | yes | no | yes | 7 | 6 | 9 | 7 | now | add UI form |
| Transcript review | Research | `review_transcript.py` | CLI/job | working manually | yes | yes | yes | partial | no | yes | no | yes | 8 | 7 | 10 | 8 | now | wire source intake workflow |
| Service opportunity extraction | Research/revenue | `extract_service_opportunity.py` | CLI | working manually | yes | yes | Opportunity Lab | partial | no | yes | no | yes | 8 | 6 | 8 | 7 | next | source-to-opportunity action |
| YouTube transcript fetch | Research | none | none | missing | no | no | no | no | no | no | no | no | 8 | 8 | 10 | 8 | now | add approved fetch/manual transcript path |
| Article/website fetch | Research | none | none | missing | no | no | no | no | no | no | no | no | 7 | 7 | 9 | 7 | next | add safe URL ingestion |
| Creative engine | Monetization | `scripts/creative` | CLI/jobs | working manually | yes | yes | yes | partial | manual exports | yes | publish approvals | yes | 9 | 7 | 5 | 8 | now | visual workflow |
| Manual publish packages | Social/revenue | `publish_readiness_packages`, reports | CLI/UI | working manually | yes | yes | yes | yes read-only | yes | yes | yes | yes | 8 | 5 | 4 | 8 | now | link package preview to approvals |
| Facebook token status | Integration | `facebook_token_status.py` | CLI | tested | yes | yes | Integrations via events | report | no | yes | no | yes | 8 | 5 | 2 | 6 | now | connection card |
| Facebook publisher | Integration | `facebook_publisher.py` | runner/job | unsafe until approved | yes | yes | via approvals/jobs | no | no | yes | yes | dry-run only | 9 | 6 | 2 | 5 | next | keep real publish hidden |
| Resend | Comms | watch loop | idempotent test only | partially working | yes | proof only | report-only | report | yes | yes | yes | with constraints | 8 | 5 | 2 | 5 | next | connect newsletter UI |
| Oanda demo | Trading | watch loop/env | connection check | working demo status | yes | events/report | Trading Lab report-only | report | yes | yes | yes for orders | status only | 5 | 5 | 4 | 5 | later | show demo proof, no live |
| Trading research tables | Trading | `trading_*` | UI tables | scaffolded | partial | yes | sparse | no | no | partial | yes | research only | 4 | 4 | 5 | 4 | later | seed strategies/backtests |
| Model router | AI policy | `model_router.py`, tables | CLI/UI | working dry-run | yes | yes | yes | Hermes route jobs | no | yes | yes | yes | 6 | 7 | 7 | 9 | now | agent console |
| OpenRouter | AI | Edge Function env | Hermes chat | connected | no | Edge Function | yes | yes | no | no | no | yes for safe data | 8 | 6 | 7 | 10 | now | monitor failures |
| Ollama/local models | AI | registry/Oracle/local process | not from UI | registered/partial | yes elsewhere | partial | registry only | route only | no | no | yes | unknown | 6 | 8 | 7 | 8 | next | safe local route test |
| Oracle worker | Infra | SSH/read-only checks | watch loop | reachable | no/local remote | report | report-only | report | yes | yes | no | read-only | 6 | 8 | 5 | 7 | next | expose status card |
| SEO engine | Marketing | `seo_*` tables | UI | scaffolded/empty | no | yes | empty | no | no | no | no | yes | 7 | 6 | 8 | 6 | hide | seed first workflow |
| Integration registry | Ops | `integration_registry` | UI | registered only | partial | yes | yes | report | no | no | no | yes | 6 | 5 | 5 | 6 | now | add live status checks |
| Ops incidents | Self-healing | `ops_incidents`, handlers | UI/jobs | scaffolded/empty | partial | yes | empty | partial | no | partial | yes for fixes | diagnostic only | 6 | 8 | 5 | 8 | now | System Doctor workflow |
| Legacy nexus-ai workers | External local | `/Users/raymonddavis/nexus-ai` | launchd/processes | running outside repo | yes | unknown | no | unknown | unknown | unknown | unknown | do not touch | 7 | 8 | 8 | 6 | audit later | bridge or isolate |
| Mac mini worker | External local | `/Users/raymonddavis/mac-mini-worker` | running process | running outside repo | yes | unknown | no | unknown | unknown | unknown | unknown | do not touch | 7 | 9 | 6 | 6 | audit later | define contract |

## Hide Until Connected

- SEO / Marketing primary tab.
- GraphRAG, SuperMemory, MarkItDown integration claims.
- TikTok and Instagram publishing.
- Live trading/funded execution.
- Public search if not explicitly deployed/configured.
- Any Oracle control/restart buttons.
