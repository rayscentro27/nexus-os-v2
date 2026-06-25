# Nexus OS v2 — Tab Behavior Rules (canonical)

Enforced by `src/config/nexusTabs.ts` + `TabStatus.tsx` (badges + Connection Status panel) and by
component logic.

1. **No fake functionality.** A tab never implies a capability it doesn't have.
2. **Every tab shows one status:** connected (Live) · partial · manual · legacy · coming soon ·
   hidden. (Rendered as a badge + Connection Status panel.)
3. **Every action button does exactly one of:** read real data · create a `task_request` · create an
   `approval` · run a dry-run allowlisted job · open a report/proof · show "not connected yet".
4. **No button may publish / send / trade / deploy without an explicit approval** (an `approvals`
   row decided in the UI, plus the server-side gate, e.g. `social_accounts.publish_enabled`).
5. **No v1 worker command is exposed directly in the browser.** v1 workers are observed, never
   controlled, from v2.
6. **Client-facing features use only approved Supabase knowledge/policies/assets** (approved_knowledge,
   admin-gated tables) — never raw private data.
7. **Hermes private advisor** may read broader safe context and recommend actions, but must not
   execute risky actions without approval (firewall: public + internal_summary only).
8. **v1 processes appear as observed/legacy status**, not controlled by v2 until safely wrapped.
9. **Uncontrolled running v1 worker label:** "Detected legacy worker — not controlled by Nexus OS v2
   yet."
10. **Scaffold-only tabs** are hidden or clearly marked "Seed/Coming Soon" (not shown as working).
11. **Connected tab actions write proof to `nexus_events`** where appropriate.

## Action-capability ladder (lowest → highest risk)
read → open report → create task_request → create approval → run dry-run job → (approval-gated)
real action. The UI may offer up to "run dry-run job" freely; anything past that requires an
approval record.

## Never-expose list (raw control forbidden in UI)
Live trading execution, `auto_executor`, social real-publish toggles, email send, scheduler
load/unload, launchd control, `mac-mini-worker` exec. These may be **displayed as status only**.
