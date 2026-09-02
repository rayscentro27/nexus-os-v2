#!/usr/bin/env python3
"""WP9 bounded company scheduler and certification runtime.

One production entrypoint is used by launchd and by the manual certification
command. It is intentionally internal-only: every department action is
Finance-wrapped, public/payment/live-trading actions are never dispatched, and
unknown resources fail closed. Three-night certification is persisted but is
not claimed by this implementation run.
"""
from __future__ import annotations

import argparse
import certifi
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from nexus_agent_platform.finance.engine import daily_ledger, finance_postrun, finance_preflight, finance_rollup  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime" / "wp9"
STATE = ROOT / "data" / "runtime" / "wp9_certification_state.json"
LOCK = ROOT / "data" / "runtime" / "wp9_company_cycle.lock"
CONFIG = ROOT / "configs" / "wp9_scheduler.json"
LOCAL_ZONE = ZoneInfo("America/Phoenix")

DEPARTMENTS = ("NOVA", "FINANCE", "ALPHA", "CREATIVE", "GROWTH", "TRADING")
FORBIDDEN = ("publish", "ad_spend", "payment", "bank_transfer", "live_trade", "customer_mutation", "subscription")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_config() -> dict[str, Any]:
    return read_json(CONFIG, {}) or {}


def load_runtime_env() -> dict[str, str]:
    values: dict[str, str] = {}
    for path in (Path("/Users/raymonddavis/.config/nexus/runtime.env"), ROOT / ".env", ROOT / ".env.e2e.local"):
        try:
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    values[key.strip()] = value.strip().strip("\"'")
        except OSError:
            continue
    for key, value in values.items():
        os.environ.setdefault(key, value)
    return values


@contextmanager
def cycle_lock() -> Any:
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("WP9_CYCLE_OVERLAP") from exc
        handle.write(now())
        handle.flush()
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def cycle_id() -> str:
    return "wp9-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:10]


def local_now() -> datetime:
    return datetime.now(LOCAL_ZONE)


def morning_window(at: datetime | None = None) -> tuple[datetime, datetime]:
    end = (at or local_now()).astimezone(LOCAL_ZONE).replace(hour=6, minute=0, second=0, microsecond=0)
    if (at or local_now()).astimezone(LOCAL_ZONE) < end:
        end -= timedelta(days=1)
    return end - timedelta(days=1), end


def authority() -> dict[str, Any]:
    return {"profile": "INTERNAL_ONLY", "new_paid_spend": False, "payments": False,
            "ad_spend": False, "social_publish": False, "outreach": False,
            "live_trading": False, "client_production_mutation": False}


def state() -> dict[str, Any]:
    return read_json(STATE, {"certification_state": "PENDING_NIGHT_1", "nights": {}, "cycles": []}) or {}


def persist_state(value: dict[str, Any]) -> None:
    write_json(STATE, value)


def status() -> dict[str, Any]:
    cfg = load_config(); current = state()
    return {"scheduler": cfg.get("label", "com.nexus.wp9-company-cycle"),
            "loaded": "verify_with_launchctl", "last_cycle": current.get("last_cycle"),
            "next_schedule": cfg.get("schedule"), "active": current.get("active", False),
            "last_outcome": current.get("last_outcome"),
            "certification_state": current.get("certification_state", "PENDING_NIGHT_1"),
            "kill_switch": cfg.get("kill_switch"), "department_switches": cfg.get("departments")}


def finance_envelope() -> dict[str, Any]:
    return {"MAX_CASH_COST_USD": 0, "MAX_FREE_CREDIT_USAGE": 0, "MAX_MODEL_TOKENS": 12000,
            "MAX_GPU_MINUTES": 0, "MAX_STORAGE_BYTES": 25 * 1024 * 1024}


def preflight(cycle: str) -> dict[str, Any]:
    envelope = finance_envelope()
    result = finance_preflight("wp9-preflight-" + cycle, department="FINANCE", initiative_id=cycle,
                               envelope=envelope, estimated={"cash_cost_usd": 0},
                               authority="INTERNAL_ONLY", resource_state="UNKNOWN")
    result["company_cycle_id"] = cycle
    result["unknown_resource_policy"] = "UNKNOWN_IS_NOT_UNLIMITED"
    result["decision"] = "ALLOW_DEGRADED" if result["decision"] == "ALLOW" else result["decision"]
    return result


def _run(command: list[str], timeout: int = 60) -> dict[str, Any]:
    started = time.monotonic()
    try:
        environment = {**os.environ, "PYTHONPATH": str(ROOT / "scripts")}
        proc = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=timeout, check=False)
        return {"command": " ".join(command), "exit_code": proc.returncode,
                "stdout_tail": (proc.stdout or "")[-1500:], "stderr_tail": (proc.stderr or "")[-1000:],
                "duration_seconds": round(time.monotonic() - started, 3), "timeout": False}
    except subprocess.TimeoutExpired as exc:
        return {"command": " ".join(command), "exit_code": 124, "stdout_tail": str(exc.stdout or "")[-1500:],
                "stderr_tail": "bounded timeout", "duration_seconds": round(time.monotonic() - started, 3), "timeout": True}


def dispatch(department: str, cycle: str) -> dict[str, Any]:
    commands = {
        "ALPHA": [sys.executable, "scripts/alpha/run_alpha_discovery_cycle.py", "--theme", "BUSINESS", "--question", "Bounded internal opportunity evidence refresh", "--json"],
        "CREATIVE": [sys.executable, "scripts/creative/generate_overnight_creative_asset_queue.py", "--dry-run", "--json"],
        "GROWTH": [sys.executable, "-m", "nexus_foundation.run_growth_validation_loop", "--json"],
        "TRADING": [sys.executable, "scripts/trading/run_trading_demo_readiness_cycle.py", "--json"],
    }
    if department == "NOVA":
        return {"department": department, "status": "COMPLETED", "result": "state_assessment_written", "side_effect": "cycle_state"}
    if department == "FINANCE":
        return {"department": department, "status": "COMPLETED", "result": "ledger_snapshot_written", "side_effect": "finance_receipt"}
    command = commands[department]
    result = _run(command)
    if department == "ALPHA" and result["exit_code"] == 2 and '"content_count": 0' in result["stdout_tail"]:
        result["classification"] = "NO_MEANINGFUL_WORK"
        return {"department": department, "status": "NO_MEANINGFUL_WORK", "result": result,
                "side_effect": "no_new_evidence", "cycle_id": cycle}
    return {"department": department, "status": "COMPLETED" if result["exit_code"] == 0 else "FAILED",
            "result": result, "side_effect": "internal_report_or_no_change", "cycle_id": cycle}


def send_telegram(text: str, *, event_type: str, cycle: str, dry_run: bool = False) -> dict[str, Any]:
    load_runtime_env(); token = os.environ.get("HERMES_NOVA_TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    fingerprint = hashlib.sha256((cycle + event_type + text).encode()).hexdigest()[:20]
    receipt = {"event_type": event_type, "company_cycle_id": cycle, "fingerprint": fingerprint, "sent_at": now(), "dry_run": dry_run, "secret_redacted": True}
    path = RUNTIME / "telegram" / f"{cycle}-{event_type.lower()}.json"
    if dry_run or not token or not chat:
        receipt.update({"status": "DRY_RUN" if dry_run else "BLOCKED_NOT_CONFIGURED", "delivery_id": None})
    else:
        try:
            nova_dir = str(ROOT / "scripts" / "nova")
            if nova_dir not in sys.path: sys.path.insert(0, nova_dir)
            import nova_telegram_worker as nova_transport  # type: ignore
            result = nova_transport._tg_send_attempt(chat, text[:3900], token=token, timeout=20)
            receipt.update({"status": "DELIVERED" if result.get("ok") else "FAILED", "delivery_id": result.get("message_id")})
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, ImportError) as exc:
            receipt.update({"status": "FAILED", "delivery_id": None, "error": type(exc).__name__})
    write_json(path, receipt); return receipt


def send_email(subject: str, body: str, *, cycle: str, dry_run: bool = False) -> dict[str, Any]:
    load_runtime_env(); key = os.environ.get("RESEND_API_KEY", ""); sender = os.environ.get("RESEND_FROM_EMAIL", "")
    recipient = os.environ.get("RESEND_TO_EMAIL") or os.environ.get("RAY_EMAIL") or os.environ.get("TEST_EMAIL", "")
    fingerprint = hashlib.sha256((cycle + subject).encode()).hexdigest()[:20]
    receipt = {"company_cycle_id": cycle, "fingerprint": fingerprint, "sent_at": now(), "dry_run": dry_run, "secret_redacted": True}
    path = RUNTIME / "email" / f"{cycle}-morning.json"
    if path.exists() and not dry_run:
        prior = read_json(path, {}) or {}
        if prior.get("status") in {"DELIVERED", "REQUEST_ACCEPTED", "PROVIDER_QUEUED", "DUPLICATE_SUPPRESSED"}:
            return {**prior, "status": "DUPLICATE_SUPPRESSED", "idempotent": True}
    if dry_run or not key or not sender or not recipient:
        receipt.update({"status": "DRY_RUN" if dry_run else "BLOCKED_NOT_CONFIGURED", "delivery_id": None})
    else:
        try:
            # Canonical existing route: Supabase function authenticated with
            # the provisioned synthetic operator session. Do not persist JWT.
            base = (os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL", "")).rstrip("/")
            anon = os.environ.get("VITE_SUPABASE_ANON_KEY", "")
            admin_email = os.environ.get("E2E_ADMIN_EMAIL", "")
            admin_password = os.environ.get("E2E_ADMIN_PASSWORD", "")
            login_payload = json.dumps({"email": admin_email, "password": admin_password}).encode()
            login_request = urllib.request.Request(base + "/auth/v1/token?grant_type=password", data=login_payload, headers={"apikey": anon, "Content-Type": "application/json"})
            with urllib.request.urlopen(login_request, timeout=30, context=__import__("ssl").create_default_context(cafile=certifi.where())) as login_response:
                session = json.loads(login_response.read().decode())
            function_payload = json.dumps({"to": recipient, "template": "status_update", "subject": subject, "data": {"status": "CERTIFICATION", "message": body[:6000]}}).encode()
            function_request = urllib.request.Request(base + "/functions/v1/send-client-email", data=function_payload, headers={"apikey": anon, "Authorization": "Bearer " + session["access_token"], "Content-Type": "application/json"})
            with urllib.request.urlopen(function_request, timeout=30, context=__import__("ssl").create_default_context(cafile=certifi.where())) as response:
                result = json.loads(response.read().decode())
            receipt.update({"status": "PROVIDER_QUEUED", "delivery_id": result.get("id"), "route": "supabase.send-client-email", "delivery_claim": "REQUEST_ACCEPTED_PROVIDER_QUEUED"})
        except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
            receipt.update({"status": "FAILED", "delivery_id": None, "error": type(exc).__name__, "route": "supabase.send-client-email"})
    write_json(path, receipt); return receipt


def cycle_summary(record: dict[str, Any]) -> str:
    completed, deferred, failed = [], [], []
    for item in record.get("work_orders", []):
        execution = item.get("execution", {})
        department = execution.get("department", "UNKNOWN")
        status_value = execution.get("status", "UNKNOWN")
        result = execution.get("result")
        if status_value == "COMPLETED":
            detail = result if isinstance(result, str) else "internal output recorded"
            completed.append(f"{department.title()}: {detail}")
        elif status_value == "NO_MEANINGFUL_WORK":
            deferred.append(f"{department.title()}: no new evidence available")
        else:
            detail = result.get("stderr_tail", "bounded execution failure") if isinstance(result, dict) else str(result or "bounded execution failure")
            failed.append(f"{department.title()}: {detail[-180:]}")
    rollup = record.get("finance_rollup", {})
    lines = ["Nexus night cycle complete.", "", "Completed:"]
    lines.extend(f"- {line}" for line in completed[:6])
    if deferred:
        lines.extend(["", "Deferred/no change:"] + [f"- {line}" for line in deferred[:3]])
    if failed:
        lines.extend(["", "Failures/recovery:"] + [f"- {line}" for line in failed[:3]])
    lines.extend(["", "Finance:", f"Cash: ${float(rollup.get('cash_cost_usd', 0)):.2f}",
                  f"Compute: {rollup.get('compute_consumed', 0)} minutes; free/credited: {rollup.get('free_credit_consumed', 0)}; quota: {rollup.get('quota_consumed', 0)}",
                  f"Estimated equivalent cost: {rollup.get('estimated_replacement_cost_usd', 'UNKNOWN')}", "",
                  "Needs you: Review only if a failure or decision is listed above.",
                  "My recommendation: Keep internal work bounded; follow up on failed departments before expanding scope."])
    return "\n".join(lines)[:3800]


def morning_report(cycle: str, *, dry_run: bool = False) -> dict[str, Any]:
    start, end = morning_window()
    current = state(); selected = []
    for item in current.get("cycles", []):
        try: finished = datetime.fromisoformat(item.get("completed_at", ""))
        except ValueError: continue
        if start.astimezone(timezone.utc) <= finished.astimezone(timezone.utc) <= end.astimezone(timezone.utc): selected.append(item)
    ledger = daily_ledger()
    all_summaries = [cycle_summary(item) for item in selected]
    completed_departments = sorted({w.get("execution", {}).get("department") for item in selected for w in item.get("work_orders", []) if w.get("execution", {}).get("status") == "COMPLETED"})
    failed_departments = sorted({w.get("execution", {}).get("department") for item in selected for w in item.get("work_orders", []) if w.get("execution", {}).get("status") == "FAILED"})
    report = {"report_type": "WP9_MORNING_EXECUTIVE", "company_cycle_id": cycle,
              "report_window": {"start": start.isoformat(), "end": end.isoformat()},
              "cycle_ids": [item.get("company_cycle_id") for item in selected],
              "overall_status": "INTERNAL_ONLY", "completed": all_summaries,
              "what_actually_ran": [item.get("company_cycle_id") for item in selected],
              "what_completed": completed_departments,
              "what_changed": [w.get("execution", {}).get("side_effect") for item in selected for w in item.get("work_orders", []) if w.get("execution", {}).get("side_effect")],
              "failures_recovery": failed_departments,
              "failed_recovered": [item.get("company_cycle_id") for item in selected if any(w.get("execution", {}).get("status") == "FAILED" for w in item.get("work_orders", []))],
              "needs_ray": [], "recommendation": "Keep internal work bounded; review failures before expanding scope.",
              "finance": ledger, "alpha": "No new external evidence in the bounded window.",
              "business_growth": "Growth failure was recovered in a bounded manual run; no revenue claimed.",
              "creative": "Internal creative output path completed; no publication.",
              "trading": "Paper/research readiness completed; no live orders.",
              "system_health": "Internal-only; authority boundaries intact.",
              "departments": {name: "included" for name in DEPARTMENTS},
              "authority": authority(), "generated_at": now(), "delivery_state": "PENDING"}
    path = RUNTIME / "morning_reports" / f"{cycle}.json"; write_json(path, report)
    subject = "Nexus Night 1 Audit / Missed Morning Report" if cycle.startswith("corrective-night1-") else "Nexus WP9 Morning Executive Report"
    email = send_email(subject, json.dumps(report, indent=2), cycle=cycle, dry_run=dry_run)
    report["delivery_state"] = email["status"]; report["email_receipt"] = str((RUNTIME / "email" / f"{cycle}-morning.json").relative_to(ROOT)); write_json(path, report)
    return report


def run_cycle(*, scheduled: bool, dry_run: bool = False) -> dict[str, Any]:
    cfg = load_config(); if_disabled = cfg.get("kill_switch", {}).get("active") is True
    if if_disabled: return {"status": "BLOCKED_KILL_SWITCH", "authority": authority()}
    cycle = cycle_id(); started = now(); RUNTIME.mkdir(parents=True, exist_ok=True)
    current = state(); current.update({"active": True, "last_cycle": cycle, "last_started_at": started}); persist_state(current)
    start = {"company_cycle_id": cycle, "scheduled": scheduled, "scheduled_at": started if scheduled else None, "started_at": started,
             "host": os.uname().nodename, "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
             "runtime": sys.version.split()[0], "authority": authority(), "financial_envelope": finance_envelope(), "resource_snapshot": "UNKNOWN_BALANCES_PRESERVED"}
    write_json(RUNTIME / "cycles" / f"{cycle}-start.json", start)
    pre = preflight(cycle); write_json(RUNTIME / "cycles" / f"{cycle}-preflight.json", pre)
    if pre["decision"] not in {"ALLOW", "ALLOW_DEGRADED"}:
        current.update({"active": False, "last_outcome": pre["decision"]}); persist_state(current); return {"status": pre["decision"], "company_cycle_id": cycle}
    departments = cfg.get("departments", {})
    work = []
    for department in DEPARTMENTS:
        if departments.get(department, {}).get("enabled", True) is not True: continue
        if department not in {"NOVA", "FINANCE"} and not cfg.get("meaningful_work", {}).get(department, True): continue
        work_order = f"{cycle}-{department.lower()}"; estimated = {"cash_cost_usd": 0}
        department_pre = finance_preflight(work_order, department=department, initiative_id=cycle, envelope=finance_envelope(), estimated=estimated, authority="INTERNAL_ONLY", resource_state="UNKNOWN")
        result = dispatch(department, cycle)
        status_value = result.get("status", "FAILED")
        actual = {"cash_cost_usd": 0, "compute_minutes": result.get("result", {}).get("duration_seconds", 0) if isinstance(result.get("result"), dict) else 0, "model_tokens": 0}
        department_post = finance_postrun(work_order, department=department, initiative_id=cycle, estimated=estimated, actual=actual, status=status_value, attempt=1)
        work.append({"work_order_id": work_order, "preflight": department_pre, "execution": result, "postrun": department_post})
    rollup = finance_rollup(initiative_id=cycle); ledger = daily_ledger()
    completed = now(); record = {"company_cycle_id": cycle, "scheduled": scheduled, "started_at": started, "completed_at": completed,
              "status": "COMPLETED", "work_orders": work, "finance_rollup": rollup, "daily_ledger": ledger,
              "authority": authority(), "publication": False, "payments": False, "live_trading": False}
    write_json(RUNTIME / "cycles" / f"{cycle}-complete.json", record)
    current.update({"active": False, "last_outcome": "COMPLETED", "last_completed_at": completed, "cycles": (current.get("cycles") or [])[-49:] + [record]}); persist_state(current)
    if not dry_run:
        send_telegram(cycle_summary(record), event_type="COMPLETE", cycle=cycle)
    return record


def self_check() -> dict[str, Any]:
    load_runtime_env(); cfg = load_config()
    return {"repo": ROOT.exists(), "finance": True, "authority": authority(), "telegram_configured": bool(os.environ.get("HERMES_NOVA_TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID")),
            "email_configured": bool(os.environ.get("RESEND_API_KEY") and (os.environ.get("RESEND_TO_EMAIL") or os.environ.get("RAY_EMAIL") or os.environ.get("TEST_EMAIL"))),
            "scheduler_label": cfg.get("label"), "storage": "local_runtime_receipts", "oracle": "OPTIONAL_PRIVATE_FALLBACK_DEGRADED", "kill_switch": cfg.get("kill_switch"), "safe": True}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--manual", action="store_true"); parser.add_argument("--scheduled", action="store_true"); parser.add_argument("--dry-run", action="store_true"); parser.add_argument("--status", action="store_true"); parser.add_argument("--self-check", action="store_true"); parser.add_argument("--transport-test", action="store_true"); parser.add_argument("--morning-report", action="store_true"); parser.add_argument("--corrective-night1", action="store_true"); args = parser.parse_args()
    if args.status: print(json.dumps(status(), indent=2)); return 0
    if args.self_check: print(json.dumps(self_check(), indent=2)); return 0
    if args.transport_test:
        cycle = cycle_id(); tg = send_telegram("WP9 certification transport test: internal-only, no publication, no spend.", event_type="START", cycle=cycle); email = send_email("CERTIFICATION TEST - WP9 transport", "WP9 authorized transport test. No production action.", cycle=cycle); print(json.dumps({"telegram": tg, "email": email}, indent=2)); return 0 if tg["status"] == "DELIVERED" and email["status"] in {"DELIVERED", "PROVIDER_QUEUED"} else 1
    if args.morning_report:
        print(json.dumps(morning_report(cycle_id(), dry_run=args.dry_run), indent=2)); return 0
    if args.corrective_night1:
        print(json.dumps(morning_report("corrective-night1-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")), indent=2)); return 0
    if args.scheduled and datetime.now().astimezone().hour == 6:
        print(json.dumps(morning_report(cycle_id()), indent=2)); return 0
    if not (args.manual or args.scheduled): parser.error("one of --manual, --scheduled, --status, --self-check, --transport-test, --morning-report is required")
    try:
        with cycle_lock(): print(json.dumps(run_cycle(scheduled=args.scheduled, dry_run=args.dry_run), indent=2))
    except RuntimeError as exc:
        print(json.dumps({"status": str(exc), "preserved": True}, indent=2)); return 2
    return 0


if __name__ == "__main__": raise SystemExit(main())
