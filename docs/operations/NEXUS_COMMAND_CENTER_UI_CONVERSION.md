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

## Polish update (2026-06-25)
- **Full desktop width:** Command Center + Source Intake opt into `.main.wide` (removes the global
  1180px cap; other tabs keep the readable width).
- **3-column mission-control grid restored** (`nx-mc-grid`, from the mockup):
  `minmax(520px,1.35fr) minmax(300px,.62fr) minmax(360px,.8fr)`; 2-col ≤1480px; 1-col ≤1024px.
  - Col 1: Hermes Mission Workspace (existing `CommandCenter`) + Source Intake/Notebook preview +
    Recent Outputs.
  - Col 2: Hermes Jarvis + **compact System Awareness** (collapsible Systems Status).
  - Col 3: Hermes Oracle + Memory Galaxy.
- **Systems Status compacted:** now a small "System Awareness" card (Live/Partial/Legacy/Seed counts
  + failing v1 jobs `continuous-ops-daily` exit 1 / `cf.hermes.gateway` exit 11 + action-capable
  count), with a `<details>` for full tab/fleet detail. No safety info removed.
- Fixes blank right-side space, early stacking, excessive scrolling, misaligned workspace,
  oversized status block. Hermes Conversation/Report Reader/Task Request preserved; Jarvis buttons
  still inert/safe ("Mac bridge not connected").
