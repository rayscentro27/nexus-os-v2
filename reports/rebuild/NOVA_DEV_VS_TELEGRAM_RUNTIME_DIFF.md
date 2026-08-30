# Nova Development vs Telegram Runtime Diff

Baseline: `eb09dc3`. Audit only; no runtime changes.

## Comparison

| Dimension | Development inspection | Telegram runtime | Result |
|---|---|---|---|
| Entrypoint | Direct Python imports / graph inspection | launchd wrapper → `nova_telegram_worker.py --once` | Different invocation, same source checkout |
| Repository | `/Users/raymonddavis/nexus-os-v2` | Same path, proven by plist and wrapper | Match |
| Graph | `get_nova_graph()` introspected as five nodes | Worker imports `get_nova_graph()` and invokes it when enabled | Source-path match; historical in-memory invocation not recoverable |
| Environment | Bare shell initially reported flags false | Wrapper sources `~/.config/nexus/runtime.env`; Nova flags enabled | Environment mismatch in diagnostics; launchd path is authoritative |
| Python | Current shell interpreter | `.venv-agent-platform/bin/python3` selected by wrapper | Configured interpreter differs unless shell is run in that venv |
| Model | Current source default/launch configuration | Receipt records `openai/gpt-4o-mini` | Model route recorded for Telegram |
| Capability broker | Imported and inspected | Worker’s graph has broker/catalog code available | Invocation not recorded in receipts |
| Web provider | Source adapter exists | No Telegram receipt proves provider selection or execution | Not proven live through Telegram |
| Capability truth | Handler exists in shared capabilities | No Telegram receipt proves `get_live_capability_status` ran | Not proven live |
| Alpha | Adapter exists | No Telegram lifecycle metadata or artifact return in receipts | Not proven live |
| Session | Direct state build inspected | Telegram persists chat memory in `scripts/data/runtime/nova_memory` | Same persistence mechanism; stale turns are live input |

## Conclusion

The development PASS and Telegram path are not identical experiments: development exercised direct source/runtime inspection, while Telegram exercised an ephemeral launchd worker with a persisted conversation. The source checkout and graph definitions match, but development did not prove that model capability envelopes were emitted, intercepted, executed, and returned on Telegram. The absence of those fields in receipts prevents a stronger claim.
