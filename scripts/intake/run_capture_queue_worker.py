#!/usr/bin/env python3
"""Nexus OS v2 — Source Intake capture queue worker (bounded, manual, SAFE).

Processes SAFE queued capture requests from `task_requests` and (only if a linked approval is
already approved) approved review-required ones. For each, it runs the existing, audited YouTube
capture wrapper ONCE per item and updates the request status + writes proof events. It never
captures arbitrary URLs — only what is already queued. Default mode is DRY-RUN.

It NEVER: publishes/sends/trades/deploys, flips publish_enabled, runs social publish jobs, starts a
scheduler/daemon, touches v1 workers, writes the v1 `research` table, uses summarize.py / external AI,
runs broad scraping, or auto-approves anything.

Usage:
  # dry-run (no capture, no writes):
  python3 scripts/intake/run_capture_queue_worker.py --once --limit 1 --dry-run --no-external-ai
  # process ONE real queued safe item:
  python3 scripts/intake/run_capture_queue_worker.py --once --limit 1 --no-dry-run --no-external-ai
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "social"))
import _supabase as sb  # noqa: E402

WRAPPER = ROOT / "scripts" / "intake" / "run_existing_youtube_monitor.py"
MAX_LIMIT = 3
SAFE_POLICY = "safe_admin_submitted_capture_v1"
RUNTIME = ROOT / "reports" / "runtime" / "nexus_capture_queue_worker_latest.md"
MANUAL = ROOT / "reports" / "manual_publish" / "nexus_capture_queue_worker_latest.md"
YT_RE = re.compile(r"^(https?://)?(www\.)?(youtube\.com/watch\?v=[\w-]{6,}|youtu\.be/[\w-]{6,})", re.I)
BAD_URL_BITS = ("list=", "/playlist", "/channel/", "/@", "results?search", "/c/", "/user/")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_public_video(url: str) -> bool:
    u = (url or "").strip()
    if not YT_RE.match(u):
        return False
    return not any(b in u for b in BAD_URL_BITS)   # reject playlist/channel/search/broad


def forbidden_flag(p: dict) -> str | None:
    for k in ("publish", "send", "trade", "deploy"):
        if p.get(k):
            return k
    if p.get("scheduler"):
        return "scheduler"
    if p.get("v1_jobs_touched"):
        return "raw_v1_worker"
    if p.get("external_ai"):
        return "external_ai"
    return None


def linked_approval_approved(task_request_id: str) -> bool:
    st, rows = sb.get("approvals", f"select=status&payload->>task_request_id=eq.{sb.q(task_request_id)}&limit=1")
    return bool(isinstance(rows, list) and rows and rows[0].get("status") == "approved")


def eligible(row: dict, args) -> tuple[bool, str]:
    p = row.get("payload") or {}
    if args.request_id and row["id"] != args.request_id:
        return False, "not requested id"
    if row.get("task_type") != "youtube_capture_request":
        return False, "not a youtube_capture_request"
    url = (p.get("source_url") or "").strip()
    if not is_public_video(url):
        return False, "not a public youtube video url"
    if args.source_url and url != args.source_url:
        return False, "url does not match --source-url filter"
    f = forbidden_flag(p)
    if f:
        return False, f"forbidden flag: {f}"
    if bool(p.get("approval_required")):
        if args.safe_queue_only:
            return False, "approval_required (safe-queue-only)"
        if not linked_approval_approved(row["id"]):
            return False, "approval_required and linked approval not approved"
        return True, "approved review-required"
    if args.approved_only:
        return False, "not approval-required (approved-only)"
    if p.get("source_capture_policy") != SAFE_POLICY:
        return False, "missing safe_admin_submitted_capture_v1 policy"
    if p.get("capture_status") not in (None, "queued", "requested"):
        return False, f"capture_status={p.get('capture_status')}"
    return True, "safe queued"


def fetch_candidates() -> list[dict]:
    st, rows = sb.get("task_requests",
                      "select=id,task_type,status,payload&task_type=eq.youtube_capture_request"
                      "&status=in.(requested,queued,running)&order=created_at.asc&limit=50")
    return rows if isinstance(rows, list) else []


def update_task(tid: str, status: str, patch_payload: dict, result_summary: str) -> None:
    st, rows = sb.get("task_requests", f"select=payload&id=eq.{sb.q(tid)}&limit=1")
    base = (rows[0].get("payload") if isinstance(rows, list) and rows else {}) or {}
    base.update(patch_payload)
    sb.update("task_requests", f"id=eq.{sb.q(tid)}",
              {"status": status, "payload": base, "result_summary": result_summary[:300], "updated_at": now()})


def run_wrapper(url: str) -> tuple[int, dict, str]:
    cmd = ["python3", str(WRAPPER), "--source-url", url, "--once", "--limit", "1",
           "--no-external-ai", "--write-events", "--no-dry-run"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    out = proc.stdout.strip()
    data: dict = {}
    if "{" in out:
        try:
            data = json.loads(out[out.find("{"):])
        except Exception:
            data = {}
    return proc.returncode, data, (proc.stderr or "")[-300:]


def process_one(row: dict, dry: bool) -> dict:
    p = row.get("payload") or {}
    url = (p.get("source_url") or "").strip()
    preview = p.get("capture_command_preview") or (
        f'python3 scripts/intake/run_existing_youtube_monitor.py --source-url "{url}" '
        f"--once --limit 1 --no-external-ai --write-events --no-dry-run")
    if dry:
        return {"request_id": row["id"], "dry_run": True, "would_process": True, "source_url": url, "command_preview": preview}

    update_task(row["id"], "running", {"capture_status": "running", "worker_started_at": now()}, "capture worker running")
    sb.event("research", "capture_worker_started", "pending", (p.get("title") or url)[:80],
             f"task_request {row['id']}", payload={"task_request_id": row["id"], "source_url": url})

    rc, data, err = run_wrapper(url)
    written = (data.get("written") or [{}])
    w = written[0] if isinstance(written, list) and written else {}
    ok = bool(data.get("ok")) and bool(w)
    if ok:
        refs = w.get("refs") or {}
        summary = f"captured: {str(w.get('title', ''))[:50]} | {w.get('category')} -> {w.get('destination')} | score {w.get('score')} | transcript {w.get('transcript_status')}"
        update_task(row["id"], "done",
                    {"capture_status": "captured", "completed_at": now(),
                     "research_source_id": refs.get("research_source_id"),
                     "nexus_event_id": w.get("nexus_event_id"), "transcript_status": w.get("transcript_status")},
                    summary)
        sb.event("research", "capture_worker_completed", "success", (str(w.get("title")) or url)[:80], summary,
                 payload={"task_request_id": row["id"], "research_source_id": refs.get("research_source_id")})
        return {"request_id": row["id"], "ok": True, "status": "done", "result_summary": summary,
                "research_source_id": refs.get("research_source_id")}
    emsg = f"capture failed (rc={rc}): {err or json.dumps(data)[:200]}"
    update_task(row["id"], "failed", {"capture_status": "failed", "completed_at": now()}, emsg)
    sb.event("research", "capture_worker_failed", "failed", url[:80], emsg[:200], payload={"task_request_id": row["id"]})
    return {"request_id": row["id"], "ok": False, "status": "failed", "result_summary": emsg[:300]}


def write_report(report: dict) -> None:
    lines = ["# Nexus Capture Queue Worker", "",
             f"- generated_at: {now()}",
             f"- mode: {'DRY-RUN (no capture, no writes)' if report['dry_run'] else 'LIVE'}",
             f"- candidates: {report['candidates']} · eligible: {report['eligible']} · processed: {report['processed']}",
             "- external_ai: false · summarize.py: not used · v1 research table: not written", "", "## Results"]
    for r in report["results"]:
        lines.append(f"- {json.dumps(r)}")
    if report["skipped"]:
        lines += ["", "## Skipped"] + [f"- {s['id']}: {s['reason']}" for s in report["skipped"]]
    for path in (RUNTIME, MANUAL):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--limit", type=int, default=1, help=f"max items (hard cap {MAX_LIMIT})")
    ap.add_argument("--dry-run", dest="dry_run", action="store_true")
    ap.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    ap.set_defaults(dry_run=True)
    ap.add_argument("--no-external-ai", action="store_true", default=True)
    ap.add_argument("--request-id", default="")
    ap.add_argument("--source-url", default="")
    ap.add_argument("--approved-only", action="store_true", help="only approved review-required items")
    ap.add_argument("--safe-queue-only", action="store_true", help="only safe approval_required=false items")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--report-path", default="")
    args = ap.parse_args()

    if not sb.configured():
        print(json.dumps({"ok": False, "error": "supabase_not_configured"})); return 2

    limit = max(1, min(args.limit, MAX_LIMIT))
    candidates = fetch_candidates()
    eligible_rows: list[dict] = []
    skipped: list[dict] = []
    for r in candidates:
        ok, reason = eligible(r, args)
        if ok:
            eligible_rows.append(r)
        else:
            skipped.append({"id": r["id"][:8], "reason": reason})
        if len(eligible_rows) >= limit:
            break

    results = [process_one(r, args.dry_run) for r in eligible_rows[:limit]]
    report = {"ok": True, "dry_run": args.dry_run, "no_external_ai": True, "candidates": len(candidates),
              "eligible": len(eligible_rows), "processed": len(results), "results": results, "skipped": skipped[:10]}
    write_report(report)
    if args.report_path:
        Path(args.report_path).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
