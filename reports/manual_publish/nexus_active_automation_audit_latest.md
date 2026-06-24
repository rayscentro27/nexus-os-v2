# Nexus Active + Automated System Status Audit

- generated_at: 2026-06-24 (audit run)
- repo: ~/nexus-os-v2
- branch: main · HEAD: 0f0a137 (feat: add Nexus overnight safe operations mode)
- mode: read-only audit. No rebuilds, no deploys, no publishes, no sends, no trades, no scheduler started, no secrets printed.

> Note on location: the live "latest" copy is written to the gitignored
> `reports/runtime/nexus_active_automation_audit_latest.md`. Per repo policy runtime reports stay
> uncommitted, so this committed copy lives in the tracked `reports/manual_publish/` directory.

---

## 1. Executive summary

Nexus OS v2 is a **bounded, manual-first operating shell that runs correctly and produces safe proof
outputs, but is not yet money-producing and is not permanently automated.** Last night a **bounded
overnight runner completed 3/3 cycles** (via tmux, now finished) and generated a clean morning
report. Build passes, the watch loop passes, Hermes explains reports, Oracle is reachable, Oanda is
demo-only, and a Resend proof newsletter was sent once (to Ray, dedup-guarded).

The system is **gated, not broken.** The two things standing between Nexus and its first live money
path are both **manual unlocks, not engineering**: (1) the GoClear/Apex landing page is built and
deploy-ready but Netlify is not connected; (2) Facebook publishing is blocked behind a pending
approval + `publish_enabled=false`. There is **no permanent scheduler** — automation today is a
bounded temporary runner only, which is the intended safe posture.

**Highest-value next move:** deploy the already-built GoClear/Apex landing page to Netlify (it ships
with an email-CTA intake, so it is money-capable on day one). See §9.

---

## 2. What actually ran (evidence)

- **Overnight safe-ops runner — RAN, COMPLETED.** `nexus_overnight_safe_ops_background.log`:
  `{"ok": true, "cycles_completed": 3, "cycles_requested": 3, "errors": []}`. Started
  2026-06-24T04:46:33Z, ended 05:27:40Z (local evening Jun 23). Runner = tmux session
  `nexus_overnight_safe_ops` (pid 94874 at the time). **That session is no longer running** (bounded
  3-cycle run finished; `scheduler_started: false`).
- **Morning report — GENERATED.** `nexus_morning_report_latest.md`: build passed, watch loop passed,
  hermes explained, oracle reachable, oanda demo ok, resend already_sent, facebook
  publish_enabled_false, netlify deploy_ready_manual, **0 errors**.
- **Watch loop — PASSES (re-run this audit).** `npm run nexus:watch` today: newsletter
  `already_sent` (no resend), trading `demo_connection_ok` (no trade), oracle reachable, hermes
  `hermes_explained_report`, `nexus_events_written: true`.
- **Build — PASSES.** `npm run build` → `tsc --noEmit && vite build` clean (`dist/` emitted).
- **Proof writes — YES.** `nexus_events_written: true`; `creative_assets_db` written (0 new rows on
  re-run = idempotent); 8 creative drafts scored (top: instagram_caption 92/100).

---

## 3. What is automated (and how)

| Automation | State |
|---|---|
| Overnight safe-ops runner (`npm run nexus:overnight`) | **Bounded temporary runner only** — runs N cycles in a tmux session, then exits. Not scheduled. Last night: 3 cycles, done. |
| Watch/activation pass (`npm run nexus:watch`) | **Manual only** — one bounded status+proof pass with a file lock (`reports/runtime/nexus_watch.lock`) to prevent overlap. |
| Permanent scheduler (cron/launchd/systemd) for v2 | **None.** `scheduler.installed=false, started=false`. Only `docs/operations/SCHEDULER_POLICY.md` exists (policy doc, not an installed job). |
| Legacy v1 launchd jobs (`com.nexus.*`, `~/nexus-ai`) | **Separate system** — ~26 launchd jobs are loaded, but they belong to the old v1 Nexus (`~/nexus-ai`), NOT v2. Left untouched. |

**Takeaway:** v2 automation = bounded, on-demand. Nothing in v2 runs unattended/permanently yet.

---

## 4. What is only manual / scaffolded

- **Social publishing** (Facebook/Instagram/TikTok): manual-package only; nothing auto-published.
- **Netlify deploy**: manual (CLI or token) — landing page built but not deployed.
- **$97 intake/checkout backend**: scaffolded — landing page uses a **manual email CTA** fallback
  (`form_backend: missing_public_form_backend_manual_email_cta_used`); no real checkout/intake form
  backend yet.
- **Hermes search** (`hermes-search`): scaffolded in repo, **not deployed** (by design).

---

## 5. What is blocked (and by what)

| Blocked thing | Blocker | Type |
|---|---|---|
| Landing page public URL | Netlify not connected (`NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID` missing) | Missing config / manual step |
| Facebook auto-publish | `publish_enabled=false` + pending approval `13eafcab-6940-4612-8239-54786e8c9e60` | Safety gate + approval |
| Instagram / TikTok publish | Manual-package only; TikTok also has no tokens | Manual-only / missing config |
| $97 conversion at scale | No public intake/checkout backend (email CTA only) | Scaffolded |
| Permanent automation | No scheduler installed (intentional) | Policy gate |

---

## 6. Job execution model (important)

Nexus v2's overnight/watch runners are **report-and-proof activation passes, NOT a job-queue
consumer.** They do not poll `agent_jobs` or `task_requests`; instead each pass directly checks
channel readiness and writes proof rows to Supabase (`nexus_events`, `creative_assets`, `approvals`,
`social_posts`). So:

- **Did jobs run last night?** Yes — 3 activation cycles ran and wrote proofs. Not queue "jobs."
- **Zero queued jobs?** There is no queue being drained by these runners; work is the activation
  pass itself. The separate `task_requests` table (Hermes) and `agent_jobs`/`nexus_runner.py`
  registry exist but are **not wired into** the overnight/watch loop.
- **Blocked by gates?** Social publish was gate-blocked (publish_enabled=false); everything else
  completed or was safely no-op (resend already_sent, trading demo-only).
- **Where are jobs represented?** As proof events in Supabase + the runtime report files; not a
  local job file or queue runner.

---

## 7. External systems status (read-only checks)

| System | Status | Evidence |
|---|---|---|
| Oracle worker | **Reachable (read-only)** | `nexus-llm-worker` up 41 days, ollama seen, nexus process seen; action=read_only_status_check |
| Oanda | **Demo/paper connection OK** | `demo_connection_ok`, `demo_paper_only=true`, no trade placed, live_signal=false |
| Resend (email) | **Connected; proof sent once** | keys present; newsletter `already_sent`, message_id `0e034d02…`; dedup prevents resend |
| Facebook/Meta | **Token present; publish gated off** | META_* present; `publish_enabled=false`; pending approval `13eafcab` |
| Instagram | **Manual only** | account id present; manual-package path |
| TikTok | **Not connected** | no tokens (`TIKTOK_*` missing) |
| Netlify | **Not connected** | missing `NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID`; `deploy_ready_manual` |
| Supabase | **Connected** | URL + service role + VITE_* present |
| OpenRouter/Hermes | **Connected, chat live** | OPENROUTER_API_KEY + VITE_HERMES_CHAT_ENABLED present |

(Env presence reported by NAME only — no secret values printed or read.)

---

## 8. Active vs pretending

| System / component | Current state | Evidence | Actually active? | Automated? | Money-producing? | Blocker | Smallest next step |
|---|---|---|---|---|---|---|---|
| Overnight safe-ops runner | Bounded run, completed | bg log 3/3, no tmux session now | Ran, now idle | Temporary only | No | Not scheduled (by design) | Decide cadence later; keep bounded |
| Watch/activation pass | Works on demand | nexus:watch passes | Yes (manual) | Manual | Indirectly | Manual trigger | Run each business morning |
| Build/CI | Green | `tsc+vite` pass | Yes | Manual | No | — | none |
| Hermes chat | Live (OpenRouter/DeepSeek) | watch: hermes_explained_report | Yes | On request | Indirect (advisor) | primary 429→fallback | none |
| Hermes report-reader | Live, safe summaries | watch report explained | Yes | On request | No | — | none |
| Landing page (GoClear/Apex) | Built, not deployed | dist file + deploy package | Built only | No | **Gateway to money** | Netlify not connected | **Deploy to Netlify** |
| $97 intake/funnel | Email-CTA fallback only | form_backend missing | Partial | No | Yes (if live) | No checkout backend | Deploy page (email CTA) now; real form later |
| Resend follow-up | Proof sent once | already_sent + message_id | Yes | Dedup-guarded | Supports money path | — | Use as $97 follow-up |
| Facebook publish | Gated off | publish_enabled=false + approval | Scaffolded | No | Yes (if enabled) | Approval + DB gate | Approve `13eafcab`, then one test post |
| Instagram/TikTok | Manual packages | manual_publish_required | Scaffolded | No | Potential | Manual / no TikTok token | Manual post from 92-score draft |
| Oanda demo | Connected demo | demo_connection_ok | Yes (demo) | No | No (paper only) | live disabled (correct) | none for money path |
| Oracle worker | Reachable | uptime/ollama seen | Yes (read-only) | v1 launchd | No | — | leave as-is |
| Permanent scheduler (v2) | Not installed | scheduler.installed=false | No | No | No | policy: none yet | install one later if approved |
| Legacy v1 launchd jobs | Loaded (separate) | launchctl list com.nexus.* | Yes (v1) | Yes (v1) | Unknown | out of v2 scope | do not touch |

---

## 9. Highest-value next move (exactly one)

**Deploy the already-built GoClear/Apex landing page to Netlify.**

Why this one: the page is **already built and scored (91/100)**, ships with an **email-CTA intake**
so it is money-capable immediately (no checkout backend required to start), and a public URL is the
single prerequisite that unblocks every downstream money action (social posts can link to it, the
Resend follow-up has somewhere to point). It is **bounded, reversible, and not a rebuild** — it only
needs Netlify auth. The Resend follow-up path is already working, so the first lead→follow-up loop is
ready the moment the page is live.

Not chosen: Facebook test post (needs approval + DB gate first, and has nowhere to link until the
page is live); trading (does not serve the GoClear/Apex money path).

### Exact commands Ray should run next
```bash
cd ~/nexus-os-v2
npm run build
netlify login
netlify init        # choose this GitHub repo · build: npm run build · publish dir: dist
netlify deploy --prod --dir=dist
# then open: <site>/goclear-apex-readiness.html
```
Alternative (token-based, no interactive login): set `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID` in
local runtime env, then `netlify deploy --prod --dir=dist`.

After it's live: (1) confirm the Resend proof email as the $97 follow-up; (2) approve Facebook
`13eafcab` for one gated test post linking to the new page.

---

## 10. Top risks
1. **Live page without a real intake/checkout** — email-CTA works to start, but a real form/checkout
   is needed before paid traffic (don't scale ads first).
2. **Netlify domain CORS** — the deployed Netlify origin will call the Supabase Edge Function
   (`hermes-chat`, CORS `*`) fine, but confirm the Supabase anon/URL env are set on Netlify
   (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_HERMES_CHAT_ENABLED=true`).
3. **Two parallel systems** — v1 launchd jobs (`~/nexus-ai`) still run independently; keep them out
   of v2 changes to avoid cross-talk.
4. **No permanent v2 scheduler** — automation only runs when Ray triggers it; acceptable now, but
   "runs without Ray at the computer" needs a single approved scheduler later.
5. **Facebook publish gate** — keep the one-post limit when first enabling; don't bulk-publish.

---

## Appendix — files inspected / commands run / git
- **Files inspected:** `package.json`; `reports/runtime/nexus_overnight_safe_ops_status.md`,
  `…_background.log`, `nexus_morning_report_latest.md`, `nexus_watch_report_latest.md`;
  `reports/manual_publish/goclear_apex_netlify_deploy_package.md`;
  `docs/operations/NEXUS_LIVE_OPERATIONS.md`, `docs/operations/SCHEDULER_POLICY.md`;
  `scripts/run_nexus_overnight_safe_ops.py`, `scripts/run_nexus_continuous_operations.py`.
- **Commands run:** `git status/log`, `tmux ls`, `pgrep`, `launchctl list | grep nexus`,
  `git check-ignore`, `npm run build` (pass), `npm run nexus:watch` (pass).
- **Git:** branch `main`, HEAD `0f0a137`, clean working tree, 0 ahead / 0 behind origin before this
  audit. Runtime reports are gitignored (stay uncommitted by policy).
- **Safety:** no secrets printed/committed, no `.env` read, no publish/send/trade, no scheduler
  started, no deploy, Oracle checked read-only, Hermes firewall untouched, `hermes-search` not
  deployed.
