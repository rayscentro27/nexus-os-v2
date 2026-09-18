# Admin Nova to Hermes 0.20.6 Restoration

Date: 2026-09-18 (America/Phoenix)

## Outcome

ADMIN_NOVA_HERMES_RESTORATION_STATUS=PARTIAL

The Admin execution path now defaults to the existing Oracle Hermes Agent
0.20.6 runtime and nova_nexus profile. The direct Admin graph is no longer
the primary execution path; it remains available only behind the explicit
rollback environment flag NEXUS_ADMIN_NOVA_RUNTIME=direct.

The real local Admin HTTP contract returned Hermes metadata:

- executor: hermes_agent_0.20.6
- host: ORACLE
- profile: nova_nexus
- toolset: nexus_mcp_remote
- provider: openrouter
- model: openai/gpt-4o-mini

No Resource Governor route was activated. The benchmark conclusions remain
unchanged.

## Runtime audit

HERMES_VERSION=0.20.6 (2026.8.27) was verified inside the running
nexus-hermes-0206 container on Oracle host nexus-llm-worker.

NOVA_PROFILE_EXISTS=YES

NOVA_PROFILE_PATH=/opt/data/profiles/nova_nexus

NOVA_PROFILE_HEALTH=PASS_REAL: profile directory, config, SOUL, state DB,
and auth files present; Hermes profile model probe returned HTTP 200.

NOVA_PROFILE_MODEL=openai/gpt-4o-mini

NOVA_PROFILE_PROVIDER=openrouter

NOVA_PROFILE_TOOL_CONFIG=nexus_mcp_remote enabled; http://127.0.0.1:18765/mcp

The profile audit found no generic /opt/data/profiles/nexus or /opt/data/profiles/alpha
directory. It did find specialized test profiles such as
nexus_orchestrator_test, nexus_research_test, and nexus_review_test.
Therefore:

- NEXUS_PROFILE_EXISTS=NO exact generic profile; specialized test profiles exist
- ALPHA_PROFILE_EXISTS=NO exact generic profile; specialized test profiles exist
- NEXUS/ALPHA_ARCHITECTURE_CHANGE=NO

The current Admin restoration uses the existing Nova profile only and does not
create a second profile.

## Hermes capability evidence

- Hermes native chat probe: PASS_REAL; exact HERMES_NOVA_CHAT_PASS.
- Hermes model call: PASS_REAL; OpenRouter openai/gpt-4o-mini.
- Hermes session continuity before restart: PASS_REAL in the same Hermes
  session for Project Falcon.
- Nexus MCP: PASS_REAL after restoring the existing SSH tunnel; remote health
  reported LISTENER_401, and a Hermes turn returned a current read-only Nexus
  health result.
- Google MCP: UNAVAILABLE; not configured in nova_nexus.
- Gmail, Calendar, Drive: UNAVAILABLE; no active Google tool in this profile.
- Department knowledge: PASS_REAL through the Admin-to-Hermes path; canonical
  departments and responsibilities were returned.
- Stedman blocker knowledge: PASS_REAL.
- Research/Alpha distinction: PASS_REAL.

The underlying Nexus MCP data read reported degraded Supabase configuration
for one operational read, and a Research work-order delegation returned a
work_order_id error. Those are truthful Hermes/tool-surface limitations, not
converted into fake success.

## Transport repair

The existing com.nexus.oracle-hermes-tunnel launchd service was restored.
Current local checks:

- Hermes loopback health: HTTP 200.
- Nexus MCP local listener: HTTP 401 without its bearer token, expected for an
  unauthenticated probe.
- Hermes profile request through the existing authorized transport: PASS_REAL.
- Public Nova host: Cloudflare Access challenge remains expected; no Access
  bypass was attempted.

## Canonical ownership

| Layer | Owner |
|---|---|
| Admin UI, conversation list, composer, voice, styling | GoClear Admin |
| Conversation persistence | Supabase Admin conversation store |
| HTTP validation and transport | nova_admin_server.py |
| Nova execution, session, toolset, profile | Hermes Agent 0.20.6 / nova_nexus |
| Model inference | Provider selected beneath Hermes |
| Future model selection | Resource Governor insertion point, not activated |

nova_admin_server.py now acts as a thin bridge. It validates the existing
Admin contract, builds bounded read-only Nexus pre-context, maps the Admin
conversation ID deterministically to the Hermes session ID, invokes the
existing Hermes CLI/profile, and returns the Hermes response.

## Conversation mapping

admin_ai_conversations.id → Hermes session_id is a deterministic identity
mapping using the existing validated conversation ID. No new conversation store
or mapping table was created.

The browser’s persisted Admin history is also replayed as bounded pre-context.
This is important because native Hermes session state did not independently
survive a service restart in the tested CLI path. After restarting the Admin
bridge, replaying the persisted Admin history restored Project Falcon
successfully:

SESSION_CONTINUITY_BEFORE_RESTART=PASS_REAL

SESSION_CONTINUITY_AFTER_RESTART=PASS_REAL_VIA_PERSISTED_ADMIN_HISTORY

HERMES_NATIVE_SESSION_PERSISTENCE_AFTER_RESTART=NOT_PROVEN

No message duplication or Supabase schema change was introduced.

## Knowledge integration

| Component | Action | Reason |
|---|---|---|
| nova_knowledge_retrieval.py | USE_AS_PRE_CONTEXT | Preserve bounded entity/repository/history ranking without creating an agent |
| nova_company_context.py | USE_AS_PRE_CONTEXT | Supply current bounded operational context |
| research_operational_state.py | USE_AS_PRE_CONTEXT | Preserve current Research truth and date semantics |
| nova_capability_truth.py | KEEP_FOR_LEGACY_DIRECT_RUNTIME | Its direct-runtime claims must not be reused as Hermes truth |
| Hermes nexus_mcp_remote | EXPOSE_AS_HERMES_TOOL | Hermes owns current tool execution and read-only runtime checks |

The source precedence remains: current governed/live state, exact entity record,
canonical repository architecture, bounded development history, then stale
summaries. Conversation history supports continuity but cannot override
verified current state.

The architecture retrieval text was updated so historical questions now explain
that the former direct graph is legacy and Hermes is the canonical Admin runtime.

## Model boundary

HERMES_EXECUTOR=Hermes Agent 0.20.6 / nova_nexus

CURRENT_MODEL_PROVIDER=OpenRouter

CURRENT_MODEL=openai/gpt-4o-mini

EXECUTOR_MODEL_COUPLED=NO

The future model-selection boundary is the Hermes request/model selection layer
inside run_oracle_hermes and the profile/provider model contract. The Resource
Governor can later select a model before Hermes inference without moving
execution ownership back into the Admin server.

MODEL_SELECTION_INTERFACE=Hermes model/provider request boundary

RESOURCE_GOVERNOR_INSERTION_POINT=before Hermes provider inference, beneath the Admin transport

RESOURCE_GOVERNOR_ACTIVATED=NO

No free model, Gemini Flash, or Gemini Pro route was activated.

## Regression tests

Real Admin HTTP tests passed for:

- Hermes executor metadata and exact response.
- natural Nova conversation.
- Project Falcon continuity across three turns.
- Project Falcon recovery after Admin service restart using persisted Admin history.
- Nexus MCP truth.
- Google MCP truth.
- Gmail unavailable truth.
- canonical department knowledge.
- Stedman blocker knowledge.
- Research versus Alpha knowledge.

Department probes:

- Systems Engineering health read: returned a current degraded health response.
- Alpha review request: returned a truthful no-current-finding result, but did
  not produce a separately verifiable Alpha delegation receipt.
- Research objective request: encountered a current MCP work_order_id error;
  no fabricated delegation was claimed.

Therefore delegation is partial, while the Hermes transport and capability truth
path are real.

## Rollback and deployment

ROLLBACK_AVAILABLE=YES

Set NEXUS_ADMIN_NOVA_RUNTIME=direct only for emergency rollback. The direct
graph was not deleted, but it is no longer initialized or selected by default.

Frontend files were unchanged, so no Netlify bundle change was required.
The backend service was restarted through launchd after the bridge change.

FILES_CHANGED=scripts/nova/nova_admin_server.py; scripts/nexus_agent_platform/bridge/oracle_hermes_cli.py; scripts/nexus_agent_platform/nova_knowledge_retrieval.py; this report

TESTS_RUN=Hermes 0.20.6/profile checks; Oracle health/models probes; Hermes direct chat; MCP read-only probe; real Admin HTTP probes; restart continuity; 19 focused Python tests; Python compilation; npm build

RAY_ACTION_REQUIRED=YES for authenticated production UI confirmation

RAY_DECISION_REQUIRED=NO for this cutover

NEXT_MACHINE_ACTION=repair/prove the existing Research work-order delegation receipt path and native Hermes session persistence before activating Resource Governor routing
