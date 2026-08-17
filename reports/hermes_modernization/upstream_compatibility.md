# Hermes Upstream Compatibility Lab

- Generated: 2026-08-17T21:45:48.507771+00:00
- Upstream repo: /Users/raymonddavis/.hermes/hermes-agent
- Sandbox home: /Users/raymonddavis/nexus-os-v2/data/runtime/nexus-hermes-lab-f6rtw8m6/hermes_home
- Overall status: PARTIAL

## First Proof: Nexus Status

Nexus is up. The registry shows 19 processes, with 17 enabled and 2 disabled. Runtime telemetry is available right now; the current runtime summary is unknown with last terminal status unknown. I have 58763 recent runtime events in the requested window.

## Probe Results

- **install_start**: PASS (ADOPT)
  - version: rc=0
  - status: rc=0
  - gateway_status: rc=0

- **model_provider**: PASS (ADAPT)
  - primary_returncode: 0
  - primary_note: No Codex credentials stored. Run `hermes auth` to authenticate.
  - local_returncode: 0
  - stdout: {"provider": "local-ollama", "model": "gemma4:31b-cloud", "content": "OK"}

- **session_continuity**: PASS (ADAPT)
  - persisted: True

- **memory**: PASS (ADAPT)

- **skill_loading**: PASS (ADOPT)
  - stdout: Installed Skills                     
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━┳━━━━━━━━━┓
┃ Name            ┃ Category ┃ Source ┃ Trust ┃ Status  ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━╇━━━━━━━━━┩
│ nexus-lab-skill │         

- **delegation**: PASS (PILOT)
  - stdout: _subagent_auto_deny

- **cron**: PARTIAL (KEEP_NEXUS)
  - stdout: ✗ Gateway is not running — cron jobs will NOT fire

  To enable automatic execution:
    hermes gateway install    # Install as a user service
    sudo hermes gateway install --system  # Linux servers: boot-time system service
    hermes ga

- **plugin_tool_integration**: PASS (ADAPT)
  - stdout: {"plugin_count": 31, "tool_names": ["nexus_current_status", "spotify_albums", "spotify_devices", "spotify_library", "spotify_playback", "spotify_playlists", "spotify_queue", "spotify_search"]}

- **nexus_tool_dispatch**: PASS (ADAPT)
  - answer: Nexus is up. The registry shows 19 processes, with 17 enabled and 2 disabled. Runtime telemetry is available right now; the current runtime summary is unknown with last terminal status unknown. I have 58759 recent runtime events in the requ

- **nexus_capability_lookup**: PASS (KEEP_NEXUS)
  - capability: get_system_health

- **deterministic_capability_invocation**: PASS (KEEP_NEXUS)
  - answer: Nexus is up. The registry shows 19 processes, with 17 enabled and 2 disabled. Runtime telemetry is available right now; the current runtime summary is unknown with last terminal status unknown. I have 58761 recent runtime events in the requested window.

- **governance_boundary**: PASS (KEEP_NEXUS)

- **supabase_writes**: PASS (KEEP_NEXUS)

- **pii_isolation**: PASS (KEEP_NEXUS)

- **production_telegram**: PASS (KEEP_NEXUS)

- **production_cutover**: PASS (KEEP_NEXUS)

## Classification

| Capability | Classification |
| --- | --- |
| install_start | ADOPT |
| model_provider | ADAPT |
| session_continuity | ADAPT |
| memory | ADAPT |
| skill_loading | ADOPT |
| delegation | PILOT |
| cron | KEEP_NEXUS |
| plugin_tool_integration | ADAPT |
| nexus_tool_dispatch | ADAPT |
| nexus_capability_lookup | KEEP_NEXUS |
| deterministic_capability_invocation | KEEP_NEXUS |
| governance_boundary | KEEP_NEXUS |
| supabase_writes | KEEP_NEXUS |
| pii_isolation | KEEP_NEXUS |
| production_telegram | KEEP_NEXUS |
| production_cutover | KEEP_NEXUS |

## Security / Isolation

- The isolated lab uses a temp HERMES_HOME and a temp plugin bridge.
- The Nexus status answer is synthesized from deterministic capabilities; no LLM is required for the system read.
