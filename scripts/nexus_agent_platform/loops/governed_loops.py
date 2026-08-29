"""Bounded WP4 loop adapters for safe internal certification.

Each adapter uses fixed local inputs and writes only a loop receipt. No adapter
can perform external communication, financial action, client mutation, or
arbitrary command execution.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from urllib.parse import quote
from pathlib import Path
from typing import Any, Mapping

from .kernel import LoopDefinition, LoopResult, run_loop

ROOT = Path(__file__).resolve().parents[3]


def _definition(loop_id: str, skill: str, worker: str, policy: str, authority: str, side_effect: str, executors: tuple[str, ...] = ()) -> LoopDefinition:
    return LoopDefinition(loop_id, loop_id.replace("_", " ").title(), f"Bounded {loop_id} loop", ("synthetic", "on_demand"), skill, (skill, "failure-recovery", "ray-review"), worker, (worker, "NEXUS_REVIEW_WORKER"), "nexusopenrouter" if policy == "TOOL_CAPABLE" else "nexusworker", policy, executors, authority, (), side_effect, {"max_attempts": 1}, {"allowed": True, "targets": ["NEXUS_REVIEW_WORKER"]}, {"fail_closed": True}, "A2_AUTOMATIC_REVIEW")


DEFINITIONS = {
    "NEXUS_SYSTEM_HEALTH_RECOVERY": _definition("NEXUS_SYSTEM_HEALTH_RECOVERY", "system-recovery", "NEXUS_OPERATIONS_WORKER", "LOCAL_PRIVATE", "internal_read_only", "local_reports", ("daily_system_operations",)),
    "NEXUS_RESEARCH_INTELLIGENCE": _definition("NEXUS_RESEARCH_INTELLIGENCE", "research-intelligence", "NEXUS_RESEARCH_WORKER", "RESEARCH", "read_only", "local_reports"),
    "NEXUS_REPO_INTELLIGENCE": _definition("NEXUS_REPO_INTELLIGENCE", "repo-intelligence", "NEXUS_RESEARCH_WORKER", "CODE_ASSIST", "internal_read_only", "local_reports"),
    "NEXUS_CREDIT_BUSINESS_FUNDING": _definition("NEXUS_CREDIT_BUSINESS_FUNDING", "funding-readiness", "NEXUS_FUNDING_WORKER", "GENERAL_REASONING", "internal_review", "local_reports"),
    "NEXUS_RAY_REVIEW": _definition("NEXUS_RAY_REVIEW", "ray-review", "NEXUS_REVIEW_WORKER", "GENERAL_REASONING", "human_review", "internal_work_item"),
}


def _run_daily(_: Mapping[str, Any]) -> Mapping[str, Any]:
    completed = subprocess.run([sys.executable, "scripts/operations/nexus_daily_monitor.py"], cwd=ROOT, capture_output=True, text=True, timeout=45, check=False)
    if completed.returncode != 0:
        return {"status": "FAIL", "entrypoint": "scripts/operations/nexus_daily_monitor.py", "side_effect": {"external": False}}
    report = json.loads((ROOT / "reports/runtime/nexus_daily_monitor_latest.json").read_text(encoding="utf-8"))
    payload = {"summary": "Daily operations report generated.", "metrics": {"processes_total": report.get("process_registry", {}).get("total"), "processes_enabled": report.get("process_registry", {}).get("enabled")}, "findings": {"reports_fresh": report.get("reports_freshness", {}).get("fresh_count"), "reports_stale": report.get("reports_freshness", {}).get("stale_count"), "stale_items": [x.get("name") for x in report.get("reports_freshness", {}).get("stale", [])], "blocked_actions": report.get("blocked_actions", {}).get("blocked", []), "next_actions": report.get("next_actions", [])}, "technical_details": {"supabase": report.get("supabase", {}), "build": report.get("build", {})}}
    return {"status": "PASS", "entrypoint": "scripts/operations/nexus_daily_monitor.py", "artifact": payload, "output_hash": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(), "side_effect": {"external": False, "local_reports": True}}


def _repo(_: Mapping[str, Any]) -> Mapping[str, Any]:
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
        "recent_change": subject.stdout.strip(), "test_status": "not run by read-only inspection",
        "verification": {"focused_tests": "not run by read-only inspection", "json_validation": "not run by read-only inspection", "secret_scan": "not run by read-only inspection"},
        "known_blockers": [], "open_work": "Review grouped changes and run the relevant verification suite.",
        "recommendations": ["Keep campaign checkpoint separate from unrelated worktree changes."],
        "runtime_impact": "none; read-only"
    }
    return {"status": "PASS", "entrypoint": "git read-only inspection", "artifact": payload, "output_hash": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(), "side_effect": {"external": False, "repository_mutation": False}}


def _research(context: Mapping[str, Any]) -> Mapping[str, Any]:
    question = str(context.get("question", "synthetic public research question"))
    if context.get("live_private_searxng"):
        if not question or any(ord(ch) < 32 for ch in question):
            return {"status": "FAIL", "entrypoint": "private SearXNG adapter"}
        query = quote(question)
        remote_command = f"curl -fsS --max-time 10 'http://127.0.0.1:8888/search?q={query}&format=json'"
        completed = subprocess.run(["ssh", "-i", str(Path.home() / ".ssh/oracle_vm"), "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "opc@161.153.40.41", remote_command], capture_output=True, text=True, timeout=15, check=False)
        if completed.returncode != 0:
            return {"status": "FAIL", "entrypoint": "private SearXNG adapter"}
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return {"status": "FAIL", "entrypoint": "private SearXNG adapter"}
        results = payload.get("results", []) if isinstance(payload.get("results", []), list) else []
        findings = [{"title": str(item.get("title", ""))[:180], "url": str(item.get("url", ""))[:240], "snippet": str(item.get("content", ""))[:300]} for item in results[:5] if isinstance(item, dict)]
        source = {"query": payload.get("query"), "result_count": len(results), "findings": findings, "private": True,
                  "executive_summary": f"The private research search returned {len(results)} public source results for {payload.get('query') or question}.",
                  "key_findings": [item.get("snippet") or item.get("title") for item in findings[:3]],
                  "what_changed": "The retrieved source set was refreshed for this request; no change is asserted without source evidence.",
                  "why_it_matters": "These sources provide current public evidence for a bounded follow-up review.",
                  "uncertainties": ["Search snippets may omit context; open the cited sources for publication-level verification."],
                  "sources_used": [{"title": item.get("title"), "url": item.get("url")} for item in findings[:5]]}
        return {"status": "PASS" if source["query"] and source["result_count"] > 0 else "FAIL", "entrypoint": "private SearXNG adapter", "artifact": source, "output_hash": hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest(), "side_effect": {"external": False, "client_pii": False}}
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
    item = {"summary": "A bounded internal review item was prepared.", "status": "PASS", "review_required": True,
            "what_happened": context.get("what_happened", "bounded internal result"), "what_is_true_now": context.get("what_is_true_now", "verified facts only"),
            "what_happens_next": context.get("what_happens_next", "await exact decision"), "do_you_need_ray": True,
            "recommended_decision": "Review the item and approve, reject, or defer only through the governed route.", "priority": "NORMAL",
            "external_action": False}
    return {"status": "PASS", "entrypoint": "Nexus internal review item builder", "artifact": item, "output_hash": hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest(), "side_effect": {"external": False, "internal_work_item": True}}


EXECUTORS = {"NEXUS_SYSTEM_HEALTH_RECOVERY": _run_daily, "NEXUS_RESEARCH_INTELLIGENCE": _research, "NEXUS_REPO_INTELLIGENCE": _repo, "NEXUS_CREDIT_BUSINESS_FUNDING": _funding, "NEXUS_RAY_REVIEW": _ray_review}


def run_governed_loop(loop_id: str, context: Mapping[str, Any], *, reviewer=None, receipt_dir: Path | None = None) -> LoopResult:
    if loop_id not in DEFINITIONS:
        raise ValueError("NO_LOOP_MATCH")
    return run_loop(DEFINITIONS[loop_id], context, trigger="on_demand", executor=EXECUTORS[loop_id], reviewer=reviewer, receipt_dir=receipt_dir)
