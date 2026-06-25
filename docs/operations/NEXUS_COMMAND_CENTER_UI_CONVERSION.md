# Nexus — Command Center UI Conversion

From `preview.html`. The Command Center tab now renders `command-center/MissionControl.tsx`
(`CommandCenterMissionControl`), which **wraps** the existing Hermes `CommandCenter` so all Hermes
modes (Conversation / Report Reader / Task Request) keep working unchanged.

## Layout
- **Top:** `SystemStatusOverview` (Live/Partial/Legacy/Seed tabs + detected v1 fleet + failing jobs).
- **Main column:** the existing Hermes workspace (`<CommandCenter/>`) + `RecentOutputsPanel`.
- **Side column:** `HermesJarvisCard`, `HermesOracleCard`, `MemoryGalaxyCard`.

## Cards
- **Hermes Jarvis** — computer-control buttons are **inert/safe**: they show
  "Mac bridge: not yet connected end-to-end" or open a tab. **No Mac command execution.**
- **Hermes Oracle** — real: latest `research_sources` with score + category → destination.
- **Memory Galaxy** — visual node map (static positions) + real `nexus_lessons` count.
- **Recent Outputs** — real: latest `nexus_events` (proof log).

## Preserved
Hermes chat/firewall, tab status badges, Connection Status panel (rendered by Shell above the
content), routing, auth. No new risky actions; nothing publishes/sends/trades/deploys.
