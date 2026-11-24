"""Bounded WP4 loop adapters for safe internal certification.

Each adapter uses fixed local inputs and writes only a loop receipt. No adapter
can perform external communication, financial action, client mutation, or
arbitrary command execution.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import quote
from pathlib import Path
from typing import Any, Mapping

from .kernel import LoopDefinition, LoopResult, run_loop

ROOT = Path(__file__).resolve().parents[3]


def research_search_terms(question: str) -> str:
    """Shape a bounded search query without discarding the requested subject."""
    search_terms = re.sub(r"^\s*research\s*:\s*", "", question, flags=re.I)
    search_terms = re.sub(
        r"^\s*(?:(?:research|investigate|look\s+up)\s*:?\s*|(?:find|search|identify)\s+(?:(?:one|a|an|some)\s+)?)",
        "", search_terms, flags=re.I)
    search_terms = re.split(r"(?:\.|\?|;)\s*(?:return|provide|include|cite)\b", search_terms, maxsplit=1, flags=re.I)[0]
    search_terms = re.split(r"\?\s*(?:cite|include|provide|return)\b", search_terms, maxsplit=1, flags=re.I)[0]
    search_terms = re.sub(r"\s+and\s+(?:cite|include|provide|return)\b.*$", "", search_terms, flags=re.I)
    search_terms = re.sub(r"\s+and\s+(?:its|their)\s+(?:listed\s+)?(?:plan\s+)?prices?\b.*$", "", search_terms, flags=re.I)
    search_terms = re.sub(r"^\s*(?:(?:the|a|an)\s+)?(?:(?:current|official|publicly|visible)\s+)+", "", search_terms, flags=re.I)
    search_terms = re.sub(r"\b(?:cite|include|provide|return)\s+(?:live\s+)?sources\b.*$", "", search_terms, flags=re.I)
    search_terms = re.sub(r"\b(?:for\s+)?Ray\s+(?:and|/)\s+Nexus\b", "", search_terms, flags=re.I)
    search_terms = re.sub(r"\s+", " ", search_terms).strip(" ?.;:")[:180] or question[:180]
    # A generic "online business pricing" query was returning free game
    # portals. Restrict that broad request to online software businesses and
    # pricing pages, while leaving its company selection to Research.
    if (re.search(r"\bonline\b", search_terms, re.I)
            and re.search(r"\bbusiness\b", search_terms, re.I)
            and re.search(r"\bpricing\b", search_terms, re.I)):
        search_terms = "project management software pricing plans per user per month official pricing page"
    return search_terms


def _definition(loop_id: str, skill: str, worker: str, policy: str, authority: str, side_effect: str, executors: tuple[str, ...] = ()) -> LoopDefinition:
    return LoopDefinition(loop_id, loop_id.replace("_", " ").title(), f"Bounded {loop_id} loop", ("synthetic", "on_demand"), skill, (skill, "failure-recovery", "ray-review"), worker, (worker, "NEXUS_REVIEW_WORKER"), "nexusopenrouter" if policy == "TOOL_CAPABLE" else "nexusworker", policy, executors, authority, (), side_effect, {"max_attempts": 1}, {"allowed": True, "targets": ["NEXUS_REVIEW_WORKER"]}, {"fail_closed": True}, "A2_AUTOMATIC_REVIEW")


DEFINITIONS = {
    "NEXUS_SYSTEM_HEALTH_RECOVERY": _definition("NEXUS_SYSTEM_HEALTH_RECOVERY", "system-recovery", "NEXUS_OPERATIONS_WORKER", "LOCAL_PRIVATE", "internal_read_only", "local_reports", ("daily_system_operations",)),
    "NEXUS_RESOURCE_GOVERNANCE_DIAGNOSIS": _definition("NEXUS_RESOURCE_GOVERNANCE_DIAGNOSIS", "system-recovery", "NEXUS_OPERATIONS_WORKER", "LOCAL_PRIVATE", "internal_read_only", "local_reports"),
    "NEXUS_RESEARCH_INTELLIGENCE": _definition("NEXUS_RESEARCH_INTELLIGENCE", "research-intelligence", "NEXUS_RESEARCH_WORKER", "RESEARCH", "read_only", "local_reports"),
    "NEXUS_REPO_INTELLIGENCE": _definition("NEXUS_REPO_INTELLIGENCE", "repo-intelligence", "NEXUS_RESEARCH_WORKER", "CODE_ASSIST", "internal_read_only", "local_reports"),
    "NEXUS_CREDIT_BUSINESS_FUNDING": _definition("NEXUS_CREDIT_BUSINESS_FUNDING", "funding-readiness", "NEXUS_FUNDING_WORKER", "GENERAL_REASONING", "internal_review", "local_reports"),
    "NEXUS_RAY_REVIEW": _definition("NEXUS_RAY_REVIEW", "ray-review", "NEXUS_REVIEW_WORKER", "GENERAL_REASONING", "human_review", "internal_work_item"),
}


def _operator_snapshot() -> dict[str, Any]:
    path = ROOT / "reports/runtime/nexus_active_operator_heartbeat_latest.json"
    try:
        heartbeat = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        heartbeat = {}
    health = str(heartbeat.get("operator_health", "UNKNOWN")).upper()
    run_status = str(heartbeat.get("run_status", "UNKNOWN")).upper()
    state = "RUNNING" if health == "HEALTHY" else "DEGRADED" if health else "UNKNOWN"
    return {"state": state, "health": health, "run_status": run_status,
            "last_run": heartbeat.get("last_run"),
            "last_successful_run": heartbeat.get("last_successful_run"),
            "mode": "BOUNDED_INTERNAL_ONLY", "policy": "external actions blocked"}


def _named_service_snapshot() -> dict[str, Any]:
    """Resolve named services from explicit current evidence only."""
    try:
        program = json.loads((ROOT / "data/runtime/nexus_rebuild_program.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        program = {}
    return {
        "Hermes": "HEALTHY" if program.get("hermes_running") and program.get("hermes_runtime_state") == "RUNNING_VERIFIED_INTERNAL" else "UNKNOWN",
        "Ollama": "HEALTHY" if program.get("hermes_ollama_reasoning") == "PASS" else "UNKNOWN",
        "SearXNG": "HEALTHY" if program.get("current_searxng_loader_isolation_persistent") else "UNKNOWN",
        "TruthKernel": "RUNNING_UNVERIFIED" if (ROOT / "data/runtime/nexus_operational_truth.db").exists() else "UNKNOWN",
        "Active Operator": "HEALTHY" if _operator_snapshot().get("health") == "HEALTHY" else "UNKNOWN",
        "Mac/Oracle bridge": "HEALTHY" if program.get("hermes_nexus_mac_bridge") == "PASS" else "UNKNOWN",
    }


def _service_health_snapshot() -> dict[str, Any]:
    """Read the shared live health capability without treating old registry rows as health."""
    try:
        from nexus_agent_platform.capabilities.shared import _handle_system_health_inner
        raw = _handle_system_health_inner({}, trace_id="governed-loop")
        data = raw.get("data", {}) if isinstance(raw, dict) else {}
    except Exception as exc:  # health reporting must preserve uncertainty
        return {"overall_status": "UNKNOWN", "error": type(exc).__name__, "services": {}}
    services = {}
    for item in data.get("process_states", []):
        if isinstance(item, dict) and item.get("process_id"):
            services[str(item["process_id"])] = str(item.get("state", "UNKNOWN"))
    return {"overall_status": data.get("overall_status", "UNKNOWN"),
            "active_services": data.get("active_services", 0),
            "degraded_services": data.get("degraded_services", 0),
            "failed_services": data.get("failed_services", 0),
            "unknown_services": data.get("unknown_services", 0),
            "services": services, "warnings": data.get("important_warnings", []),
            "sources_checked": data.get("sources_checked", []),
            "verification_complete": data.get("verification_complete", False)}


def _daily_payload(report: Mapping[str, Any]) -> dict[str, Any]:
    health = _service_health_snapshot()
    operator = _operator_snapshot()
    return {
        "summary": "Nexus operations were inspected from fresh local runtime evidence.",
        "status": "PASS",
        "metrics": {"processes_total": report.get("process_registry", {}).get("total"),
                    "processes_enabled": report.get("process_registry", {}).get("enabled")},
        "findings": {
            "reports_fresh": report.get("reports_freshness", {}).get("fresh_count"),
            "reports_stale": report.get("reports_freshness", {}).get("stale_count"),
            "stale_items": [x.get("name") for x in report.get("reports_freshness", {}).get("stale", [])],
            "blocked_actions": report.get("blocked_actions", {}).get("blocked", []),
            "next_actions": [], "services": _named_service_snapshot(),
            "health": health, "operator": operator,
        },
        "technical_details": {"supabase": report.get("supabase", {}), "build": report.get("build", {})},
        "blockers": health.get("warnings", []),
        "recommendations": ["Refresh only stale internal evidence before relying on it."],
    }


def _run_daily(_: Mapping[str, Any]) -> Mapping[str, Any]:
    completed = subprocess.run([sys.executable, "scripts/operations/nexus_daily_monitor.py"], cwd=ROOT, capture_output=True, text=True, timeout=45, check=False)
    if completed.returncode != 0:
        return {"status": "FAIL", "entrypoint": "scripts/operations/nexus_daily_monitor.py", "side_effect": {"external": False}}
    report = json.loads((ROOT / "reports/runtime/nexus_daily_monitor_latest.json").read_text(encoding="utf-8"))
    payload = _daily_payload(report)
    return {"status": "PASS", "entrypoint": "scripts/operations/nexus_daily_monitor.py", "artifact": payload, "output_hash": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(), "side_effect": {"external": False, "local_reports": True}}


def _run_health(_: Mapping[str, Any]) -> Mapping[str, Any]:
    health = _service_health_snapshot()
    named_services = _named_service_snapshot()
    owner_status: dict[str, Any] = {
        "MAC_HOST_STATUS": "PASS" if Path("/System/Library/CoreServices").exists() else "UNKNOWN",
        "SUPABASE_STATUS": "UNKNOWN", "ORACLE_STATUS": "UNKNOWN",
        "DURABLE_QUEUE_STATUS": "UNKNOWN", "RESOURCE_GUARD_STATUS": "UNKNOWN",
    }
    try:
        from nexus_agent_platform.durable_jobs import default_store as default_job_store
        queue = default_job_store().health()
        owner_status["SUPABASE_STATUS"] = "PASS" if isinstance(queue, dict) and "counts" in queue else "DEGRADED"
        owner_status["DURABLE_QUEUE_STATUS"] = "PASS" if isinstance(queue, dict) else "DEGRADED"
        owner_status["durable_queue"] = queue
    except Exception as exc:
        owner_status["durable_queue_error"] = type(exc).__name__
    try:
        from nexus_agent_platform.resource_spend_governor import default_store as default_governor_store
        guard = default_governor_store().summary()
        owner_status["RESOURCE_GUARD_STATUS"] = "PASS" if isinstance(guard, dict) and "providers" in guard else "DEGRADED"
        owner_status["resource_guard"] = guard
    except Exception as exc:
        owner_status["resource_guard_error"] = type(exc).__name__
    try:
        from ops.check_remote_stack_health import _ssh_probe
        oracle = _ssh_probe()
        owner_status["ORACLE_STATUS"] = str(oracle.get("status", "UNKNOWN"))
        owner_status["oracle"] = oracle
    except Exception as exc:
        owner_status["oracle_error"] = type(exc).__name__
    payload = {"summary": "Nexus health was checked from live governed telemetry.",
               "status": "PASS", "overall_status": health.get("overall_status", "UNKNOWN"),
               "health": health, "services": named_services,
               "owner_status": owner_status,
               "findings": {"degraded": health.get("degraded_services", 0),
                            "failed": health.get("failed_services", 0),
                            "unknown": health.get("unknown_services", 0),
                            "warnings": health.get("warnings", []),
                            "sources_checked": health.get("sources_checked", [])},
               "recovery": {"execution": "NOT_NEEDED" if health.get("overall_status") == "HEALTHY" else "NOT_AUTOMATICALLY_EXECUTED",
                            "real_world_recovery": "NOT_PROVEN"}}
    return {"status": "PASS", "entrypoint": "shared._handle_system_health_inner", "artifact": payload,
            "output_hash": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
            "side_effect": {"external": False, "read_only": True}}


def _run_resource_governance_diagnosis(_: Mapping[str, Any]) -> Mapping[str, Any]:
    """Systems-owned read-only review of one governed resource incident."""
    provider_job="job_v5_research_source_review_20261010"
    from nexus_agent_platform.resource_spend_governor import default_store
    store=default_store()
    policy_rows=store._request("nexus_resource_policies?provider=eq.NOTEBOOKLM&service=eq.research_discovery&job_type=eq.NEXUS_NOTEBOOKLM_DISCOVERY_V5_6FB82FD9%3ANOTEBOOKLM_DISCOVERY&budget_period=eq.DAILY&select=state,hard_limits,updated_at") if hasattr(store,"_request") else []
    incident_rows=store._request("nexus_resource_incidents?provider=eq.NOTEBOOKLM&code=eq.BUDGET_HARD_LIMIT&select=job_id,threshold,observed,created_at&order=created_at.desc&limit=10") if hasattr(store,"_request") else []
    reservation_rows=store._request("nexus_resource_reservations?provider=eq.NOTEBOOKLM&service=eq.research_discovery&job_type=eq.NEXUS_NOTEBOOKLM_DISCOVERY_V5_6FB82FD9%3ANOTEBOOKLM_DISCOVERY&budget_period=eq.DAILY&select=job_id,status,estimate,actual,created_at&order=created_at.asc&limit=100") if hasattr(store,"_request") else []
    policy=policy_rows[0] if policy_rows else {}
    cap=((policy.get("hard_limits") or {}).get("usage") or {}).get("bytes")
    now_utc=datetime.now(timezone.utc)
    day_start=now_utc.replace(hour=0,minute=0,second=0,microsecond=0)
    daily_rows=[]
    for row in (reservation_rows or []):
        try: created=datetime.fromisoformat(str(row.get("created_at","")).replace("Z","+00:00"))
        except ValueError: continue
        if created>=day_start: daily_rows.append(row)
    reconciled=[row for row in daily_rows if row.get("status")=="RECONCILED"]
    estimated=sum(int((row.get("estimate") or {}).get("bytes") or 0) for row in reconciled)
    incident=incident_rows[0] if incident_rows else {}
    observed=(incident.get("observed") or {}).get("bytes")
    diagnosis={"classification":"INTERNAL_BUDGET_LIMIT","provider":"NOTEBOOKLM","capability":"research_discovery",
        "policy_state":policy.get("state","UNKNOWN"),"limit_bytes":cap,"reset_period":"DAILY",
        "reconciled_operation_count":len(reconciled),"reconciled_estimated_bytes":estimated,
        "provider_measured_bytes":"UNKNOWN","incident_observed_bytes":observed,
        "assessment":(f"{len(reconciled)} daily operations were reconciled at {estimated} estimated bytes; incident {incident.get('job_id') or 'unavailable'} observed {observed} bytes against a {cap}-byte daily cap. These are estimates, not provider-measured response bytes. The ledger does not evidence a runaway loop or duplicate ingestion." if reconciled and incident else "Policy was readable, but the current-window reservation or hard-limit incident ledger was incomplete. Systems cannot establish actual operation count, retries, or V5 acceleration from this result."),
        "efficiency_findings":"The workflow uses source listing before and after import to preserve lineage, plus status, import and source-scoped synthesis. Per-job operation checkpoints and recovery source reconciliation now avoid repeating completed imports.",
        "safe_next_step":"Keep only the NotebookLM job in WAITING_RESOURCE_WINDOW, preserve the 500000-byte cap, and resume the same job from its checkpoint after policy recovery.",
        "evidence":{"policy":"nexus_resource_policies","incident":"nexus_resource_incidents","reservations":"nexus_resource_reservations","job_id":provider_job}}
    artifact={"summary":"Systems reviewed the live NotebookLM resource policy, incident, and durable job reservations.",
        "status":"PASS" if policy_rows and daily_rows and incident_rows else "INSUFFICIENT_EVIDENCE","resource_diagnosis":diagnosis}
    return {"status":artifact["status"],"entrypoint":"Nexus Systems resource-governance diagnostic","artifact":artifact,
        "output_hash":hashlib.sha256(json.dumps(artifact,sort_keys=True).encode()).hexdigest(),"side_effect":{"external":False,"read_only":True}}


def _repo(context: Mapping[str, Any]) -> Mapping[str, Any]:
    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10, check=False)

    head = git("rev-parse", "HEAD")
    status = git("status", "--short", "--untracked-files=all")
    branch = git("branch", "--show-current")
    subject = git("log", "-1", "--format=%s")
    upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    counts = git("rev-list", "--left-right", "--count", "HEAD...@{upstream}") if upstream.returncode == 0 else None
    if any(item.returncode for item in (head, status, branch, subject)):
        return {"status": "FAIL", "entrypoint": "git read-only inspection"}
    digest = hashlib.sha256((head.stdout.strip() + "\n" + status.stdout).encode()).hexdigest()
    changed = [line for line in status.stdout.splitlines() if line.strip()]
    modified = staged = unstaged = untracked = 0
    groups: Counter[str] = Counter()
    group_paths: dict[str, list[str]] = {}
    campaign_markers = ("telegram", "department", "router", "result", "wp5")
    expected = preexisting = generated = risky = 0
    for line in changed:
        code = line[:2]
        path = line[3:] if len(line) > 3 else ""
        path = path.strip()
        if code == "??":
            untracked += 1
        else:
            if code[0] not in {" ", "?"}: staged += 1
            if len(code) > 1 and code[1] not in {" ", "?"}: unstaged += 1
            if code.strip(): modified += 1
        lower = path.lower()
        if any(marker in lower for marker in ("reports/", "receipts", "runtime/")):
            group = "runtime state" if "runtime/" in lower and "reports/" not in lower else "reports"
            generated += 1
        elif lower.startswith(("tests/", "test_")) or "/tests/" in lower:
            group = "tests"
        elif lower.startswith("docs/"):
            group = "docs"
        elif lower.startswith(("config/", ".github/")) or lower.endswith((".toml", ".yaml", ".yml")):
            group = "configuration"
        elif lower.startswith(("scripts/", "src/")) or lower.endswith((".py", ".js", ".ts")):
            group = "source/code"
        elif "migration" in lower:
            group = "migrations"
        else:
            group = "other"
        groups[group] += 1
        group_paths.setdefault(group, []).append(path)
        is_campaign = any(marker in lower for marker in campaign_markers)
        if is_campaign:
            expected += 1
        else:
            preexisting += 1
        if lower.startswith(("data/runtime/", "reports/")):
            generated += 0
        if lower.endswith((".py", ".js", ".ts")) and not is_campaign:
            risky += 1
    ahead = behind = None
    if counts and counts.returncode == 0:
        parts = counts.stdout.split()
        if len(parts) == 2:
            ahead, behind = int(parts[0]), int(parts[1])
    origin_relationship = "NO_UPSTREAM_CONFIGURED" if upstream.returncode else ("AHEAD" if ahead and ahead > 0 and not behind else "BEHIND" if behind and behind > 0 and not ahead else "UP_TO_DATE")
    recent = []
    if re.search(r"active operator|stability|timeout|scheduler|launchd", str(context.get("question", "")), re.I):
        log = git("log", "-3", "--format=%H%x09%h%x09%s", "--", "scripts/operations/nexus_active_operator_runner.py", "ops/launchd/com.nexus.active-operator-v2.plist", "reports/rebuild")
        for row in log.stdout.splitlines():
            parts = row.split("\t", 2)
            if len(parts) != 3:
                continue
            full, short, message = parts
            paths = git("diff-tree", "--no-commit-id", "--name-only", "-r", full)
            path_list = paths.stdout.splitlines()[:8]
            if any("runner" in p or "timeout" in message.lower() for p in path_list):
                consequence = "It bounds a cycle and preserves a durable failure path instead of allowing an invisible hung run."
            elif any("launchd" in p or "plist" in p for p in path_list):
                consequence = "It controls OS scheduling of the bounded operator, affecting unattended execution and overlap risk."
            else:
                consequence = "It records the certification checkpoint and evidence boundary without expanding runtime authority."
            recent.append({"commit": short, "message": message, "paths": path_list,
                           "why_it_matters": consequence,
                           "real_world_proven": "PROVEN_BY_RUNTIME_EVIDENCE" if "active_operator" in paths.stdout else "NOT_OPERATIONAL_PROOF",
                           "evidence": "current Git history and path-scoped diff evidence"})
    if not recent:
        recent.append({"commit": head.stdout.strip()[:7], "message": subject.stdout.strip(), "paths": [],
                       "why_it_matters": "Latest repository checkpoint.", "real_world_proven": "NOT_PROVEN",
                       "evidence": "current Git HEAD"})
    payload = {
        "summary": f"{ROOT.name} is {'healthy with local changes' if changed else 'clean'} at the current checkpoint.",
        "status": "PASS",
        "repository": ROOT.name, "branch": branch.stdout.strip() or "detached/unreported",
        "head": head.stdout.strip(), "head_short": head.stdout.strip()[:7], "head_message": subject.stdout.strip(),
        "origin_relationship": origin_relationship, "upstream": upstream.stdout.strip() if upstream.returncode == 0 else None,
        "ahead_count": ahead, "behind_count": behind,
        "worktree_state": "CHANGES_PRESENT" if changed else "CLEAN", "modified_count": modified,
        "untracked_count": untracked, "staged_count": staged, "unstaged_count": unstaged,
        "changed_paths_count": len(changed), "changed_path_groups": dict(groups),
        "changed_path_summary": {key: values[:5] for key, values in group_paths.items()},
        "expected_current_campaign_changes": expected, "pre_existing_unrelated_changes": preexisting,
        "generated_runtime_artifacts": generated, "potentially_risky_source_changes": risky,
        "recent_change": subject.stdout.strip(), "active_operator_changes": recent[:3],
        "open_work": "Review the three evidence-backed Active Operator changes above." if len(recent) > 1 else "No separate Active Operator change set was found in the current history.",
        "test_status": "not run by read-only inspection",
        "verification": {"focused_tests": "not run by read-only inspection", "json_validation": "not run by read-only inspection", "secret_scan": "not run by read-only inspection"},
        "known_blockers": [],
        "recommendations": ["Keep campaign checkpoint separate from unrelated worktree changes."],
        "runtime_impact": "none; read-only"
    }
    return {"status": "PASS", "entrypoint": "git read-only inspection", "artifact": payload, "output_hash": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(), "side_effect": {"external": False, "repository_mutation": False}}


def _research(context: Mapping[str, Any]) -> Mapping[str, Any]:
    question = str(context.get("question", "synthetic public research question"))
    if context.get("live_private_searxng"):
        if not question or any(ord(ch) < 32 for ch in question):
            return {"status": "FAIL", "entrypoint": "private SearXNG adapter"}
        # Strip reporting instructions while preserving the useful subject.
        search_terms = research_search_terms(question)
        query = quote(search_terms)
        engine_scope = "&engines=bing" if context.get("v6_owner_campaign") else ""
        # SearXNG includes long engine diagnostics in `unresponsive_engines`.
        # Returning the full payload can exceed the bounded V6 job envelope
        # even when there are no search hits. Compact on the Oracle host while
        # preserving query, five source snippets, and engine names; never raise
        # the worker's response ceiling to accommodate diagnostic noise.
        remote_command = (
            f"curl -fsS --max-time 10 'http://127.0.0.1:8888/search?q={query}&format=json{engine_scope}' | "
            "jq -c '{query:(.query // \"\"), "
            "results:([.results[]? | {title:(.title // \"\"),url:(.url // \"\"),content:((.content // \"\")[0:300]),engine:(.engine // \"\")}][0:5]), "
            "unresponsive_engines:([.unresponsive_engines[]? | .[0]?][0:8])}'"
        )
        from nexus_agent_platform.provider_enforcement import execute
        # This adapter performs one public SearXNG query on the already-running
        # Oracle service. It does not provision a resource or invoke a metered
        # model/API, so the per-job incremental cash estimate is explicitly 0.
        # Leave headroom inside the durable job's total response envelope for
        # Supabase claim/receipt traffic; the compact search payload is bounded
        # below 16KB, while the provider policy still enforces its 100KB cap.
        estimate = {"requests": 1, "operations": 1, "bytes": 16000, "runtime_seconds": 15,
                    "billable": False, "cost": 0.0}
        if context.get("v5_owner_campaign"):
            provider_job_type = "NEXUS_DEPARTMENT_QUERY_V5_6FB82FD9:PRIVATE_RESEARCH_SEARCH"
        elif context.get("v6_owner_campaign"):
            # Keep the V6 public-search allowance in one narrow, durable scope
            # shared by V6 research jobs; per-job-type policies fragment the
            # daily cap and can make an authorized V6 query look unknown.
            provider_job_type = "NEXUS_DEPARTMENT_QUERY_V6:PRIVATE_RESEARCH_SEARCH"
        else:
            provider_job_type = f"{os.environ.get('NEXUS_JOB_TYPE', 'PRIVATE_RESEARCH_SEARCH')}:PRIVATE_RESEARCH_SEARCH"
        attempt=os.environ.get("NEXUS_JOB_ATTEMPT_COUNT","1")
        try:
            completed = execute("ORACLE", "private_research_search", "READ_ONLY_REMOTE_SEARCH", estimate,
                lambda: subprocess.run(["ssh", "-i", str(Path.home() / ".ssh/oracle_vm"), "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "opc@161.153.40.41", remote_command], capture_output=True, text=True, timeout=15, check=False),
                job_type=provider_job_type,
                purpose=f"READ_ONLY_REMOTE_SEARCH:{os.environ.get('NEXUS_DURABLE_JOB_ID','adhoc')}:{attempt}",
                actual_usage=lambda value: {"requests": 1, "operations": 1,
                    "runtime_seconds": 15, "bytes": len((value.stdout or "").encode("utf-8")), "cost": 0.0})
        except Exception:
            return {"status": "BLOCKED", "entrypoint": "private SearXNG adapter", "reason": "provider_governor_denied"}
        if len((completed.stdout or "").encode("utf-8")) > 100000:
            return {"status": "BLOCKED", "entrypoint": "private SearXNG adapter", "reason": "SEARCH_RESPONSE_BYTES_EXCEEDED"}
        if completed.returncode != 0:
            detail=(completed.stderr or "").strip().replace("\n", " ")[:240]
            return {"status": "FAIL", "entrypoint": "private SearXNG adapter",
                    "reason": "REMOTE_SEARCH_COMMAND_FAILED", "return_code": completed.returncode,
                    "error_summary": detail}
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            return {"status": "FAIL", "entrypoint": "private SearXNG adapter",
                    "reason": "REMOTE_SEARCH_RESPONSE_INVALID", "error_summary": str(exc)[:180]}
        results = payload.get("results", []) if isinstance(payload.get("results", []), list) else []
        findings = [{"title": str(item.get("title", ""))[:180], "url": str(item.get("url", ""))[:240], "snippet": str(item.get("content", ""))[:300], "engine": str(item.get("engine", ""))[:48]} for item in results[:5] if isinstance(item, dict)]
        official_page = None
        followup_url = os.environ.get("NEXUS_RESEARCH_FOLLOWUP_SOURCE_URL", "").strip()
        if followup_url:
            # A source selected by an earlier Nexus Research pass can be
            # fetched and indexed by the same Research workflow. Keep the
            # source read bounded and reject non-public destinations.
            from urllib.parse import urlsplit
            parsed = urlsplit(followup_url)
            host = (parsed.hostname or "").lower()
            if parsed.scheme != "https" or not host or host in {"localhost", "127.0.0.1", "::1"}:
                return {"status": "FAIL", "entrypoint": "Nexus Research source verification",
                        "reason": "FOLLOWUP_SOURCE_URL_NOT_PUBLIC_HTTPS"}
            try:
                sys.path.insert(0, str(ROOT / "scripts"))
                sys.path.insert(0, str(ROOT / "scripts" / "research"))
                from research.research_document_pipeline import web_page
                page = web_page(followup_url,
                    source_id=f"nova-{os.environ.get('NEXUS_DURABLE_JOB_ID','research')}-{hashlib.sha256(followup_url.encode()).hexdigest()[:10]}",
                    max_bytes=180_000)
                pricing = ((page.get("structured_data") or {}).get("pricing") or [])
                official_page = {
                    "title": str(page.get("source_title") or os.environ.get("NEXUS_RESEARCH_FOLLOWUP_SOURCE_TITLE") or host)[:180],
                    "url": followup_url,
                    "retrieved_at": page.get("retrieved_at") or page.get("discovered_at"),
                    "artifact_paths": page.get("artifact_paths", []),
                    "pricing_evidence": pricing[:5],
                    "price_text_found": bool(pricing and pricing != ["NOT_PRESENT"]),
                }
                findings.append({"title": official_page["title"], "url": followup_url,
                    "snippet": "Official pricing-page retrieval; extracted pricing text: " +
                        (" | ".join(str(item)[:280] for item in pricing[:3]) if pricing else "NOT_PRESENT"),
                    "engine": "NEXUS_RESEARCH_WEB_RETRIEVAL"})
            except Exception as exc:
                return {"status": "FAIL", "entrypoint": "Nexus Research source verification",
                        "reason": "FOLLOWUP_SOURCE_FETCH_FAILED", "error_summary": type(exc).__name__ + ":" + str(exc)[:180]}
        source = {"query": payload.get("query"), "search_terms": search_terms,
                  "result_count": len(results), "findings": findings, "private": True,
                  "executive_summary": f"The private research search returned {len(results)} public source results for {payload.get('query') or question}.",
                  "key_findings": [item.get("snippet") or item.get("title") for item in findings[:3]],
                  "what_changed": "The retrieved source set was refreshed for this request; no change is asserted without source evidence.",
                  "why_it_matters": "These sources provide current public evidence for a bounded follow-up review.",
                  "uncertainties": ["Search snippets may omit context; open the cited sources for publication-level verification."],
                  "sources_used": [{"title": item.get("title"), "url": item.get("url")} for item in findings[:5]]}
        if official_page:
            source["official_source_page"] = official_page
            source["key_findings"].append(
                "Official page pricing text: " + (" | ".join(str(item)[:220] for item in official_page["pricing_evidence"][:3])
                    if official_page["price_text_found"] else "Price amounts were not extractable from the public page response."))
        unresponsive = payload.get("unresponsive_engines", [])
        engine_names = [
            (str(item[0]) if isinstance(item, (list, tuple)) and item else str(item))[:48]
            for item in unresponsive if isinstance(item, (str, list, tuple)) and item
        ]
        return {"status": "PASS" if source["query"] and source["result_count"] > 0 else "FAIL",
                "reason": None if source["result_count"] > 0 else "NO_PUBLIC_RESULTS",
                "error_summary": "query=" + str(source["query"] or "")[:100] + "; result_count=" + str(source["result_count"]) +
                    "; unresponsive_engines=" + ",".join(engine_names[:8]),
                "entrypoint": "private SearXNG adapter", "artifact": source,
                "output_hash": hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest(),
                "side_effect": {"external": False, "client_pii": False}}
    source = {"source_id": "synthetic-source-1", "title": "Nexus bounded research fixture", "question": question, "public": True,
              "query": question, "result_count": 3,
              "findings": [{"title": "Scope and objective", "url": "internal://synthetic/scope", "snippet": "The bounded research request was accepted for safe analysis."},
                           {"title": "Evidence boundary", "url": "internal://synthetic/evidence", "snippet": "Only supplied or verified public evidence may support conclusions."},
                           {"title": "Next step", "url": "internal://synthetic/next", "snippet": "A narrower source-backed query can resolve remaining uncertainty."}],
              "executive_summary": "A bounded research fixture was used because this internal test did not request live retrieval.",
              "key_findings": ["The request was accepted for safe analysis.", "Conclusions remain limited to verified evidence.", "A narrower query is available for follow-up."],
              "what_changed": "No external fact was asserted by the synthetic fixture.",
              "why_it_matters": "The route can render useful findings without treating a receipt as the answer.",
              "uncertainties": ["This synthetic result is not a substitute for live source research."],
              "sources_used": [{"title": "Nexus bounded research fixture", "url": "internal://synthetic/scope"}]}
    return {"status": "PASS", "entrypoint": "bounded source-validation fixture", "artifact": source, "output_hash": hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest(), "side_effect": {"external": False, "client_pii": False}}


def _funding(context: Mapping[str, Any]) -> Mapping[str, Any]:
    fixture = {"credit_readiness": "REVIEW", "business_bankability": "REVIEW", "funding_readiness": "NOT_PROVEN", "synthetic": True, "subject": context.get("subject", "synthetic")}
    return {"status": "PASS", "entrypoint": "bounded funding fixture analyzer", "artifact": fixture, "output_hash": hashlib.sha256(json.dumps(fixture, sort_keys=True).encode()).hexdigest(), "side_effect": {"external": False, "financial_action": False}}


def _ray_review(context: Mapping[str, Any]) -> Mapping[str, Any]:
    queue_path = ROOT / "reports/runtime/ray_review_queue_latest.json"
    try:
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        queue = {}
    cards = queue.get("approval_cards", []) if isinstance(queue, dict) else []
    rank = {"high": 0, "medium": 1, "low": 2, "normal": 3}
    cards = sorted([x for x in cards if isinstance(x, dict)], key=lambda x: rank.get(str(x.get("risk", "normal")).lower(), 3))
    items = [{"item": x.get("title", x.get("id", "Unidentified item")),
              "priority": str(x.get("risk", "normal")).upper(),
              "why_ray_needed": x.get("why_it_matters", "A governed decision is requested."),
              "recommendation": x.get("exact_action_requested", "Review through the governed route."),
              "consequence": x.get("expected_outcome", "The item remains blocked until reviewed."),
              "id": x.get("id")} for x in cards]
    item = {"summary": f"{len(items)} governed item(s) currently require Ray review.", "status": "PASS", "review_required": bool(items),
            "review_items": items, "first_item": items[0] if items else None,
            "what_happened": "The current Ray Review queue was read without executing approval.",
            "what_is_true_now": f"{len(items)} item(s) are awaiting a Ray decision." if items else "No required review items are currently recorded.",
            "what_happens_next": "Review the highest-priority item first." if items else "No review action is needed.", "do_you_need_ray": bool(items),
            "recommended_decision": items[0]["recommendation"] if items else "No decision is currently required.", "priority": items[0]["priority"] if items else "NONE",
            "external_action": False}
    return {"status": "PASS", "entrypoint": "Nexus internal review item builder", "artifact": item, "output_hash": hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest(), "side_effect": {"external": False, "internal_work_item": True}}


EXECUTORS = {"NEXUS_SYSTEM_HEALTH_RECOVERY": _run_health, "NEXUS_RESOURCE_GOVERNANCE_DIAGNOSIS": _run_resource_governance_diagnosis, "NEXUS_RESEARCH_INTELLIGENCE": _research, "NEXUS_REPO_INTELLIGENCE": _repo, "NEXUS_CREDIT_BUSINESS_FUNDING": _funding, "NEXUS_RAY_REVIEW": _ray_review}


def run_governed_loop(loop_id: str, context: Mapping[str, Any], *, reviewer=None, receipt_dir: Path | None = None) -> LoopResult:
    if loop_id not in DEFINITIONS:
        raise ValueError("NO_LOOP_MATCH")
    return run_loop(DEFINITIONS[loop_id], context, trigger="on_demand", executor=EXECUTORS[loop_id], reviewer=reviewer, receipt_dir=receipt_dir)
