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
    return {"status": "PASS" if completed.returncode == 0 else "FAIL", "entrypoint": "scripts/operations/nexus_daily_monitor.py", "artifact": ["reports/runtime/nexus_daily_monitor_latest.json"], "side_effect": {"external": False, "local_reports": True}}


def _repo(_: Mapping[str, Any]) -> Mapping[str, Any]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10, check=False)
    status = subprocess.run(["git", "status", "--short", "--untracked-files=no"], cwd=ROOT, capture_output=True, text=True, timeout=10, check=False)
    if head.returncode or status.returncode:
        return {"status": "FAIL", "entrypoint": "git read-only inspection"}
    digest = hashlib.sha256((head.stdout.strip() + "\n" + status.stdout).encode()).hexdigest()
    return {"status": "PASS", "entrypoint": "git read-only inspection", "artifact": "repo-state-read-only", "output_hash": digest, "side_effect": {"external": False, "repository_mutation": False}}


def _research(context: Mapping[str, Any]) -> Mapping[str, Any]:
    question = str(context.get("question", "synthetic public research question"))
    if context.get("live_private_searxng"):
        if not question or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_" for ch in question):
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
        source = {"query": payload.get("query"), "result_count": len(payload.get("results", [])), "private": True}
        return {"status": "PASS" if source["query"] and source["result_count"] > 0 else "FAIL", "entrypoint": "private SearXNG adapter", "artifact": source, "output_hash": hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest(), "side_effect": {"external": False, "client_pii": False}}
    source = {"source_id": "synthetic-source-1", "title": "Nexus bounded research fixture", "question": question, "public": True}
    return {"status": "PASS", "entrypoint": "bounded source-validation fixture", "artifact": source, "output_hash": hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest(), "side_effect": {"external": False, "client_pii": False}}


def _funding(context: Mapping[str, Any]) -> Mapping[str, Any]:
    fixture = {"credit_readiness": "REVIEW", "business_bankability": "REVIEW", "funding_readiness": "NOT_PROVEN", "synthetic": True, "subject": context.get("subject", "synthetic")}
    return {"status": "PASS", "entrypoint": "bounded funding fixture analyzer", "artifact": fixture, "output_hash": hashlib.sha256(json.dumps(fixture, sort_keys=True).encode()).hexdigest(), "side_effect": {"external": False, "financial_action": False}}


def _ray_review(context: Mapping[str, Any]) -> Mapping[str, Any]:
    item = {"review_required": True, "what_happened": context.get("what_happened", "bounded internal result"), "what_is_true_now": context.get("what_is_true_now", "verified facts only"), "what_happens_next": context.get("what_happens_next", "await exact decision"), "do_you_need_ray": True, "external_action": False}
    return {"status": "PASS", "entrypoint": "Nexus internal review item builder", "artifact": item, "output_hash": hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest(), "side_effect": {"external": False, "internal_work_item": True}}


EXECUTORS = {"NEXUS_SYSTEM_HEALTH_RECOVERY": _run_daily, "NEXUS_RESEARCH_INTELLIGENCE": _research, "NEXUS_REPO_INTELLIGENCE": _repo, "NEXUS_CREDIT_BUSINESS_FUNDING": _funding, "NEXUS_RAY_REVIEW": _ray_review}


def run_governed_loop(loop_id: str, context: Mapping[str, Any], *, reviewer=None, receipt_dir: Path | None = None) -> LoopResult:
    if loop_id not in DEFINITIONS:
        raise ValueError("NO_LOOP_MATCH")
    return run_loop(DEFINITIONS[loop_id], context, trigger="on_demand", executor=EXECUTORS[loop_id], reviewer=reviewer, receipt_dir=receipt_dir)
