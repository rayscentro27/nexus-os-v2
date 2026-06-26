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
from nexus_enrichment import build_project_enrichment  # noqa: E402

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


def fetch_source(source_id: str | None, url: str) -> dict:
    if source_id:
        st, rows = sb.get("research_sources", f"select=*&id=eq.{sb.q(source_id)}&limit=1")
        if isinstance(rows, list) and rows:
            return rows[0]
    st, rows = sb.get("research_sources", f"select=*&url=eq.{sb.q(url)}&limit=1")
    return rows[0] if isinstance(rows, list) and rows else {}


def fetch_transcript_review(source: dict, url: str) -> dict:
    source_id = source.get("id")
    if source_id:
        st, rows = sb.get("transcript_reviews",
                          f"select=*&metadata->>research_source_id=eq.{sb.q(source_id)}&order=created_at.desc&limit=1")
        if isinstance(rows, list) and rows:
            return rows[0]
    if url:
        st, rows = sb.get("transcript_reviews",
                          f"select=*&metadata->>source_url=eq.{sb.q(url)}&order=created_at.desc&limit=1")
        if isinstance(rows, list) and rows:
            return rows[0]
    title = source.get("title")
    if title:
        st, rows = sb.get("transcript_reviews", f"select=*&title=eq.{sb.q(title)}&order=created_at.desc&limit=1")
        if isinstance(rows, list) and rows:
            return rows[0]
    return {}


def write_project_enrichment(task_id: str, source_id: str | None, url: str, task_payload: dict,
                             wrapper_item: dict | None = None, existing_event_id: str | None = None) -> dict:
    source = fetch_source(source_id, url)
    review = fetch_transcript_review(source, url)
    enrichment_source = "transcript_capture" if (wrapper_item or {}).get("transcript_status") == "captured" or review else "deterministic"
    enrichment = build_project_enrichment(
        source=source or {"title": task_payload.get("title"), "url": url, "snippet": task_payload.get("snippet"),
                          "metadata": {"transcript_status": task_payload.get("transcript_status") or "pending_transcript"}},
        transcript_review=review,
        task_payload=task_payload,
        proof_event_id=existing_event_id,
        enrichment_source=enrichment_source,
    )
    st, ev = sb.insert("nexus_events", {
        "lane": "research", "action": "source_enriched_for_project_card",
        "status": "success" if enrichment["enrichment_status"] != "failed" else "failed",
        "source": "capture_queue_worker",
        "title": (source.get("title") or task_payload.get("title") or url)[:80],
        "summary": f"{enrichment['enrichment_status']} · {enrichment['category']} -> {enrichment['destination']} · score {enrichment['score']}",
        "payload": {"task_request_id": task_id, "research_source_id": source.get("id"),
                    "transcript_review_id": review.get("id"), "source_url": url,
                    "project_enrichment": enrichment},
    })
    proof_id = ev[0]["id"] if isinstance(ev, list) and ev else existing_event_id
    enrichment["proof_event_id"] = proof_id
    if source.get("id"):
        meta = (source.get("metadata") or {}) | {
            "project_enrichment": enrichment,
            "enrichment_status": enrichment["enrichment_status"],
            "proof_event_id": proof_id,
        }
        sb.update("research_sources", f"id=eq.{sb.q(source['id'])}", {"metadata": meta})
    if review.get("id"):
        meta = (review.get("metadata") or {}) | {
            "project_enrichment": enrichment,
            "research_source_id": source.get("id"),
            "source_url": url,
            "proof_event_id": proof_id,
        }
        sb.update("transcript_reviews", f"id=eq.{sb.q(review['id'])}", {"metadata": meta})
    return enrichment


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
        enrichment = write_project_enrichment(row["id"], refs.get("research_source_id"), url, p, w, w.get("nexus_event_id"))
        summary = f"captured+enriched: {str(w.get('title', ''))[:50]} | {enrichment.get('category')} -> {enrichment.get('destination')} | score {enrichment.get('score')} | {enrichment.get('enrichment_status')}"
        update_task(row["id"], "done",
                    {"capture_status": "captured", "completed_at": now(),
                     "research_source_id": refs.get("research_source_id"),
                     "nexus_event_id": w.get("nexus_event_id"), "transcript_status": w.get("transcript_status"),
                     "project_enrichment": enrichment, "enrichment_status": enrichment.get("enrichment_status")},
                    summary)
        sb.event("research", "capture_worker_completed", "success", (str(w.get("title")) or url)[:80], summary,
                 payload={"task_request_id": row["id"], "research_source_id": refs.get("research_source_id")})
        return {"request_id": row["id"], "ok": True, "status": "done", "result_summary": summary,
                "research_source_id": refs.get("research_source_id")}
    source = fetch_source(None, url)
    if source:
        enrichment = write_project_enrichment(row["id"], source.get("id"), url, p, None, None)
        update_task(row["id"], "requested",
                    {"capture_status": "queued", "enrichment_status": enrichment.get("enrichment_status"),
                     "project_enrichment": enrichment, "research_source_id": source.get("id")},
                    "source metadata saved; transcript enrichment pending")
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
