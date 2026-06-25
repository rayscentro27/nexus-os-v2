# Nexus YouTube Monitoring — Schedule Plan (NOT enabled)

Ray wants scheduled YouTube monitoring. **No scheduler is started by this task.** This is the plan
+ a `.plist.example` to enable later, only after a successful dry-run and Ray's explicit approval.

## Recommended policy
- **Frequency:** daily (once/day) to start. Never more than hourly.
- **Max videos per run:** small and bounded — start with `--limit 3` (legacy `COLLECTOR_MAX_VIDEOS`
  default is also 3). No backfills.
- **Sources:** approved channels/playlists only (allowlist). No private/unlisted videos, no
  login/captcha/paywall bypass, no broad/topic scraping.
- **Dry-run first:** every change is validated with `--dry-run --no-external-ai` before any live run.
- **External AI:** off by default (`--no-external-ai`). Transcripts are public, but keep scoring
  deterministic unless Ray approves AI summarization.

## Enable (later, with approval)
1. Confirm a dry-run passes:
   ```
   python3 scripts/intake/run_existing_youtube_monitor.py --once --limit 1 --dry-run --no-external-ai \
       --source-url https://www.youtube.com/watch?v=EXAMPLE
   ```
2. Do ONE manual live run and review the Supabase rows + report:
   ```
   python3 scripts/intake/run_existing_youtube_monitor.py --once --limit 3 --no-dry-run --write-events \
       --source-url <approved-url>
   ```
3. Only then, install ONE launchd job on ONE host from the example below.

## Enable launchd (one host only)
- Copy `docs/operations/com.nexus.v2.youtube-monitor.plist.example` →
  `~/Library/LaunchAgents/com.nexus.v2.youtube-monitor.plist`, edit the absolute paths, then:
  `launchctl load ~/Library/LaunchAgents/com.nexus.v2.youtube-monitor.plist`

## Disable
- `launchctl unload ~/Library/LaunchAgents/com.nexus.v2.youtube-monitor.plist` and remove the file.

## Logs / proofs
- Report: `reports/runtime/nexus_youtube_monitor_latest.md` (+ committed copy in
  `reports/manual_publish/`).
- Proof events: `nexus_events` (`youtube_source_reviewed`) — only with `--write-events` on a live run.
- launchd stdout/stderr: `reports/runtime/nexus_youtube_monitor.out` / `.err`.

## How Ray approves
Ray approves enabling the schedule explicitly (chat or an `approvals` row). Until then the `.plist`
stays as `.plist.example` and is never loaded.

## Legacy v1 schedulers (separate system — do NOT touch)
The old `~/nexus-ai` system already runs these launchd jobs (in `~/Library/LaunchAgents/`):
`com.nexus.monetization-research.plist`, `com.nexus.research-worker.plist`,
`com.nexus.youtube-channel-poller.plist`, `com.nexus.research-signal-bridge.plist`. These belong to
v1 and write to the v1 Supabase `research` table. **v2 does not modify, start, or stop them.** The v2
monitor is independent and writes to v2 tables only.
