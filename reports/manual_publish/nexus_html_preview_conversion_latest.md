# Nexus — HTML Preview Conversion (report)

- generated_at: 2026-06-25 · build PASS · watch PASS
- ZIP inspected: `~/Downloads/sfadafd.zip` (extracted read-only to `/tmp/nexus_html_previews`, not into repo)
- extracted: `preview.html`, `preview (1).html`

## Mapping
- **`preview.html`** → **Command Center** ("Nexus OS v2 — Command Center").
- **`preview (1).html`** → **Source Intake & Review** ("Nexus OS v2 — Source Intake & Review").
- Not duplicates. Source Intake mockup is the more detailed/stronger design and is the data-wired one.

## Components created
- `src/components/nexusUI.css` — `nx-`-prefixed visual classes (glass/soft/orb/glow/pill/memory-node/
  line/source-card/mini-progress/input/badges) — no Tailwind, no CDN, scoped, no collisions.
- `src/components/command-center/MissionControl.tsx` — `CommandCenterMissionControl` + Jarvis/Oracle/
  MemoryGalaxy/RecentOutputs cards; **wraps the existing Hermes `CommandCenter`**.
- `src/components/source-intake/` — `SourceIntakeReviewPage`, `AddSourcePanel`, `SourceEntryForm`,
  `RecentSourcesTable`, `ReviewDetailPanel`.
- `src/components/Shell.tsx` — Command Center tab → MissionControl; Intake tab → SourceIntakeReviewPage
  (both passed `onNavigate=setActive`). `src/main.tsx` imports the CSS. Routing/auth unchanged.

## Connected to REAL v2 Supabase
- Recent Sources table → `research_sources` (shows the captured **"Hermes SEO Agent OS…"** source:
  transcript captured, ai_tooling → Ops & Improvements, 22/100, model v1).
- Review Detail → that row's `metadata` (score, priority, tags, compliance).
- Oracle card → recent `research_sources`; Recent Outputs → `nexus_events`; Memory count → `nexus_lessons`.

## Remaining static/sample
Memory Galaxy node positions + labels, Jarvis button set, header status pills, Connection Status copy.

## Actions — live vs disabled
- **Live/safe:** Ask Hermes (navigate), routing buttons + Submit → file approval-gated `task_requests`
  (sign-off only).
- **Disabled/inert:** Jarvis Open Browser/TradingView/VS Code/Run Safe Command → "Mac bridge not
  connected"; no Mac exec; **no publish/send/trade/deploy; no browser capture; no scheduler.**

## Preserved
Routing, auth/session, RLS, Approvals/System Health/Agent Jobs/Events Feed, Hermes
chat+Report Reader+Task Request, tab status model + badges + Connection Status + Systems overview.

## Verification
build PASS · `nexus:watch` PASS · no scheduler · no v1 jobs touched · no real capture · no
publish/send/trade/deploy · approval `13eafcab` pending · FB `publish_enabled` false · no secrets ·
`.env` not committed.

## Next build
Add a "Run approved capture" action (task_request → worker runs the CLI wrapper) and source-row
disposition writes; then polish the Command Center grid responsiveness.
