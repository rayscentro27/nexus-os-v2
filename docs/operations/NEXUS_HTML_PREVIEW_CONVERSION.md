# Nexus — HTML Preview → React Conversion

Converted the two static HTML mockups from `~/Downloads/sfadafd.zip` into real React/Vite components
inside the existing app. No browser exec, no Tailwind CDN, no external fonts/images/scripts.

## Files
| Mockup | Title | Maps to | New components |
|---|---|---|---|
| `preview.html` | "Nexus OS v2 — Command Center" | **Command Center** tab | `command-center/MissionControl.tsx` |
| `preview (1).html` | "Nexus OS v2 — Source Intake & Review" | **Source Intake** tab (intake) | `source-intake/*` |

Not duplicates — distinct designs. The Source Intake mockup is the stronger/more detailed one and is
the data-wired conversion.

## What was stripped (per safety rules)
`<!DOCTYPE>/html/head/body`, **Tailwind CDN `<script>`**, Google Fonts links, the Unsplash avatar
image, and all inline `<script>` blocks (animation). `class`→`className`, `onclick`→`onClick`.

## Styling approach
The app uses its own CSS design system (no Tailwind). I did **not** add Tailwind (neither CDN nor a
local install). Instead I recreated the key visual classes in **`src/components/nexusUI.css`**,
**prefixed `nx-`** (`nx-glass`, `nx-soft`, `nx-orb`, `nx-pill`, `nx-glow`, `nx-memory-node`,
`nx-line`, `nx-source-card`, `nx-mini-progress`, `nx-input`, badges/tags) so they never collide with
the existing `.card`/`.pill` classes. Imported once in `main.tsx`. Scoped under `.nx-scope`.

## What's REAL data vs static
- **Real (v2 Supabase):** Source Intake "Recent Sources" table (`research_sources`), Review Detail
  rating (from each row's `metadata`), Oracle card (recent `research_sources`), Recent Outputs
  (`nexus_events`), Memory Galaxy lesson count (`nexus_lessons`), Systems Status (tab config).
- **Static/sample:** Memory Galaxy node positions + category labels, the Jarvis button set, status
  pills in headers (illustrative), the Connection Status copy (truth-based but hand-written).

## Safe vs disabled actions
- **Safe/live:** select a source, Ask Hermes (navigates), routing buttons → file approval-gated
  `task_requests` (sign-off only), Submit Source → files a `task_request` (no browser capture).
- **Disabled/inert:** Jarvis "Open Browser/TradingView/VS Code/Run Safe Command" → show "Mac bridge:
  not yet connected end-to-end" (no Mac exec). No publish/send/trade/deploy anywhere.

## Preserved
Routing, auth/session persistence, Supabase RLS, Approvals, System Health, Agent Jobs, Events Feed,
**existing Hermes chat (Conversation / Report Reader / Task Request)**, the tab status model
(`nexusTabs.ts`, sidebar badges, Connection Status panels, Systems Status overview). The Command
Center mission control **wraps** the existing `CommandCenter` (Hermes) rather than replacing it.

See `NEXUS_COMMAND_CENTER_UI_CONVERSION.md` and `NEXUS_SOURCE_INTAKE_UI_PLAN.md`.
