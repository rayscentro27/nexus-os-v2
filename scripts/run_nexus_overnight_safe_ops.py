#!/usr/bin/env python3
"""Bounded overnight safe operations runner for Nexus OS.

No scheduler install, no daemon, no unbounded loop. Runs a fixed number of
cycles, calls the existing safe watch loop, writes runtime reports, and stops.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "reports" / "runtime"
OVERNIGHT_LOG = REPORT_DIR / "nexus_overnight_safe_ops.md"
MORNING_REPORT = REPORT_DIR / "nexus_morning_report_latest.md"
STATUS_REPORT = REPORT_DIR / "nexus_overnight_safe_ops_status.md"
LOCK_FILE = REPORT_DIR / "nexus_overnight_safe_ops.lock"
WATCH_JSON = REPORT_DIR / "nexus_watch_report_latest.json"
WATCH_MD = REPORT_DIR / "nexus_watch_report_latest.md"

sys.path.insert(0, str(ROOT / "scripts" / "social"))
try:
    import _supabase as sb  # type: ignore
except Exception:  # pragma: no cover - runtime fallback
    sb = None


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_cmd(cmd: list[str], timeout: int) -> dict:
    started = now()
    try:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        return {
            "cmd": " ".join(cmd),
            "started_at": started,
            "ended_at": now(),
            "returncode": proc.returncode,
            "stdout_tail": "\n".join((proc.stdout or "").splitlines()[-40:]),
            "stderr_tail": "\n".join((proc.stderr or "").splitlines()[-20:]),
        }
    except subprocess.TimeoutExpired:
        return {
            "cmd": " ".join(cmd),
            "started_at": started,
            "ended_at": now(),
            "returncode": 124,
            "stdout_tail": "",
            "stderr_tail": "timeout",
        }


def load_watch() -> dict:
    if not WATCH_JSON.exists():
        return {}
    try:
        return json.loads(WATCH_JSON.read_text(errors="ignore"))
    except Exception:
        return {}


def event(action: str, status: str, title: str, summary: str, payload: dict | None = None) -> None:
    if not sb or not sb.configured():
        return
    sb.event("automation", action, status, title, summary, payload=payload or {})


@contextlib.contextmanager
def lock():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    handle = LOCK_FILE.open("w")
    try:
        import fcntl  # type: ignore
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("overnight_safe_ops_already_running")
        handle.write(now())
        handle.flush()
        yield
    finally:
        with contextlib.suppress(Exception):
            import fcntl  # type: ignore
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def append_cycle(cycle: int, total: int, result: dict, watch: dict) -> None:
    lines = [
        f"## Cycle {cycle}/{total} - {now()}",
        "",
        f"- watch_returncode: {result['returncode']}",
        f"- watch_report: {watch.get('latest_report_path', 'reports/runtime/nexus_watch_report_latest.md')}",
        f"- hermes_status: {(watch.get('hermes') or {}).get('status', 'unknown')}",
        f"- oracle_status: {(watch.get('oracle') or {}).get('status', 'unknown')}",
        f"- oanda_status: {(watch.get('trading') or {}).get('status', 'unknown')}",
        f"- resend_status: {(watch.get('newsletter') or {}).get('status', 'unknown')}",
        f"- facebook_status: {json.dumps((watch.get('social') or {}).get('blocked', []))}",
        f"- netlify_status: {(watch.get('landing') or {}).get('status', 'unknown')}",
        "",
    ]
    if result["returncode"] != 0:
        lines += ["### Error Tail", "```text", result.get("stderr_tail", ""), "```", ""]
    with OVERNIGHT_LOG.open("a") as f:
        f.write("\n".join(lines) + "\n")


def money_actions(watch: dict) -> list[str]:
    social = watch.get("social") or {}
    approval = social.get("approval_required") or {}
    return [
        "Deploy the GoClear/Apex landing page: run `netlify login`, `netlify init`, then `netlify deploy --prod --dir=dist`, or add Netlify token/site env names.",
        f"Approve Facebook one-post enablement in Nexus approvals{f' ({approval.get('approval_id')})' if approval.get('approval_id') else ''}, then set `social_accounts.publish_enabled=true` for the Clear Credentials row.",
        "Use the Resend proof email as the first follow-up test and connect landing-page intake to the $97 readiness review path.",
    ]


def write_morning_report(started: str, ended: str, cycles: list[dict], build: dict | None, errors: list[str]) -> None:
    watch = load_watch()
    lines = [
        "# Nexus Morning Report",
        "",
        f"- overnight_mode_started: True",
        f"- start_time: {started}",
        f"- end_time: {ended}",
        f"- cycles_completed: {len([c for c in cycles if c['returncode'] == 0])}/{len(cycles)}",
        f"- build_status: {'passed' if build and build.get('returncode') == 0 else 'not_run_or_failed'}",
        f"- watch_loop_status: {'passed' if cycles and cycles[-1]['returncode'] == 0 else 'failed'}",
        f"- hermes_explanation_status: {(watch.get('hermes') or {}).get('status', 'unknown')}",
        f"- oracle_status: {(watch.get('oracle') or {}).get('status', 'unknown')}",
        f"- oanda_demo_status: {(watch.get('trading') or {}).get('status', 'unknown')}",
        f"- resend_status: {(watch.get('newsletter') or {}).get('status', 'unknown')}",
        f"- facebook_status: {json.dumps((watch.get('social') or {}).get('blocked', []))}",
        f"- netlify_status: {(watch.get('landing') or {}).get('status', 'unknown')}",
        f"- scheduler_started: False",
        f"- packages_updated: reports/manual_publish/",
        f"- proof_events: {'written' if (watch.get('proofs') or {}).get('nexus_events_written') else 'unknown'}",
        f"- final_git_status: see operator final check",
        "",
        "## Errors",
        *(f"- {err}" for err in errors),
        *([] if errors else ["- none"]),
        "",
        "## Blockers",
        "- Netlify public URL is still blocked until Netlify is linked or token/site env names are added.",
        "- Facebook auto-publish is blocked until the one-post enablement approval is approved and `publish_enabled=true` is set for the Facebook row.",
        "- TikTok and Instagram remain manual packages only.",
        "",
        "## Top 3 Money Actions",
        *(f"{i}. {action}" for i, action in enumerate(money_actions(watch), start=1)),
        "",
        "## Exact Next Commands / Buttons",
        "- Netlify CLI: `netlify login`, `netlify init`, `netlify deploy --prod --dir=dist`.",
        "- Nexus Approvals: approve `Enable one Facebook GoClear/Apex test post` before enabling the DB publish gate.",
        "- Manual command: `npm run nexus:watch` for one safe status pass.",
    ]
    MORNING_REPORT.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run bounded Nexus overnight safe operations.")
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--sleep-minutes", type=float, default=20.0)
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()

    if args.cycles < 1 or args.cycles > 12:
        print(json.dumps({"ok": False, "status": "invalid_cycles", "cycles": args.cycles}))
        return 2

    started = now()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    OVERNIGHT_LOG.write_text(f"# Nexus Overnight Safe Ops\n\n- started_at: {started}\n- cycles_requested: {args.cycles}\n- bounded: true\n- scheduler_started: false\n\n")
    errors: list[str] = []
    cycles: list[dict] = []
    build: dict | None = None

    try:
        with lock():
            event("overnight_safe_ops_started", "pending", "Overnight safe ops started", f"{args.cycles} bounded cycle(s)", {"cycles": args.cycles})
            if not args.skip_build:
                build = run_cmd(["npm", "run", "build"], timeout=180)
                if build["returncode"] != 0:
                    errors.append("build_failed")
                    write_morning_report(started, now(), cycles, build, errors)
                    event("overnight_safe_ops_blocked", "failed", "Overnight safe ops blocked", "build_failed", {"build": build})
                    print(json.dumps({"ok": False, "status": "build_failed", "morning_report": str(MORNING_REPORT.relative_to(ROOT))}, indent=2))
                    return 1

            for cycle in range(1, args.cycles + 1):
                result = run_cmd(["npm", "run", "nexus:watch"], timeout=240)
                cycles.append(result)
                watch = load_watch()
                append_cycle(cycle, args.cycles, result, watch)
                if result["returncode"] != 0:
                    errors.append(f"cycle_{cycle}_watch_failed")
                    break
                event("overnight_safe_ops_cycle", "success", "Overnight safe ops cycle completed", f"cycle {cycle}/{args.cycles}", {"cycle": cycle, "cycles": args.cycles})
                if cycle < args.cycles:
                    time.sleep(max(0, args.sleep_minutes) * 60)

            ended = now()
            write_morning_report(started, ended, cycles, build, errors)
            event("overnight_safe_ops_finished", "success" if not errors else "failed", "Overnight safe ops finished", f"cycles={len(cycles)} errors={len(errors)}", {"cycles": len(cycles), "errors": errors})
    except RuntimeError as exc:
        if str(exc) == "overnight_safe_ops_already_running":
            print(json.dumps({"ok": False, "status": "blocked_overlap", "reason": str(exc)}, indent=2))
            return 2
        raise

    print(json.dumps({
        "ok": not errors,
        "cycles_completed": len([c for c in cycles if c["returncode"] == 0]),
        "cycles_requested": args.cycles,
        "morning_report": str(MORNING_REPORT.relative_to(ROOT)),
        "overnight_log": str(OVERNIGHT_LOG.relative_to(ROOT)),
        "errors": errors,
    }, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
