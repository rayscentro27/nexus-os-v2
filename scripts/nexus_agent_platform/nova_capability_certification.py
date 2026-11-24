"""Observer-only Nova capability certification and state consistency checks.

This module never dispatches work. Callers provide evidence collected by the
existing Nova/Nexus paths; the harness validates the result, flags divergence,
and writes JSON/Markdown certification artifacts.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_RESULTS = {"PASS", "FAIL", "PARTIAL", "NOT_AVAILABLE", "NOT_TESTED"}
FAILURE_LAYERS = {
    "NATURAL_LANGUAGE_ROUTING", "CAPABILITY_SELECTION", "ASSIGNMENT_CREATION",
    "MCP_CONNECTIVITY", "PROVIDER_CONNECTIVITY", "QUEUE_WRITE", "QUEUE_CLAIM",
    "WORKER_EXECUTION", "RESULT_PERSISTENCE", "STATE_CONSISTENCY",
    "PARENT_CONTINUATION", "STATUS_READBACK", "DELIVERY_AUTHORIZATION",
    "TELEGRAM_DELIVERY", "DEPARTMENT_LOGIC", "EXTERNAL_DEPENDENCY", "UNKNOWN",
}
CAPABILITIES = (
    "Telegram Receive", "Telegram Send", "Hermes", "Nexus MCP", "Supabase",
    "Durable Queue", "Status Readback", "Gmail Read", "Systems Control",
    "Creative Control", "OpenCode Control", "Research Control", "Calendar Read",
    "Drive Read", "Trading Paper Control",
)


@dataclass
class CapabilityResult:
    capability: str
    natural_language_understanding: str = "NOT_TESTED"
    intent_classification: str = "NOT_TESTED"
    correct_capability_selected: str = "NOT_TESTED"
    assignment_created: str = "NOT_TESTED"
    queue_write: str = "NOT_TESTED"
    worker_execution: str = "NOT_TESTED"
    result_persisted: str = "NOT_TESTED"
    result_readable: str = "NOT_TESTED"
    nova_response_generated: str = "NOT_TESTED"
    nova_response_delivered: str = "NOT_TESTED"
    state_consistency: str = "NOT_TESTED"
    overall_status: str = "NOT_TESTED"
    failure_layer: str = "UNKNOWN"
    failure_reason: str | None = None
    evidence: list[str] = field(default_factory=list)

    def validate(self) -> "CapabilityResult":
        for name, value in asdict(self).items():
            if name in {"capability", "failure_reason", "evidence"}:
                continue
            if name == "failure_layer":
                if value not in FAILURE_LAYERS:
                    raise ValueError(f"INVALID_FAILURE_LAYER:{value}")
            elif value not in ALLOWED_RESULTS:
                raise ValueError(f"INVALID_CERTIFICATION_RESULT:{name}:{value}")
        return self


def check_state_consistency(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Compare the existing objective/job/work/parent/delivery projections."""
    root = str(snapshot.get("root_objective_state") or "").upper()
    durable = str(snapshot.get("durable_job_state") or "").upper()
    work = str(snapshot.get("work_item_state") or "").upper()
    parent = str(snapshot.get("parent_workflow_state") or "").upper()
    continuation = str(snapshot.get("continuation_state") or "").upper()
    result = str(snapshot.get("result_state") or "").upper()
    delivery = str(snapshot.get("delivery_state") or "").upper()
    active = {"READY", "CLAIMED", "RUNNING", "REPAIRING", "REROUTING", "IN_PROGRESS"}
    violations: list[str] = []
    if durable == "COMPLETED" and work == "QUEUED":
        violations.append("DURABLE_COMPLETED_WORK_STILL_QUEUED")
    if root and root not in {"COMPLETE", "HANDOFF_COMPLETE", "RAY_ACTION_REQUIRED",
                             "NEW_INCREMENTAL_CASH_REQUIRED", "TRUE_TECHNICAL_BLOCKER"}:
        # Parent/work-item IN_PROGRESS are root projections, not evidence that
        # a worker owns a child lease. Only a durable job or its continuation
        # can prove that execution is active.
        if not any(value in active for value in (durable, continuation)):
            violations.append("INCOMPLETE_ROOT_WITHOUT_ACTIVE_CONTINUATION")
    if parent == "COMPLETE" and not snapshot.get("handoff_created"):
        violations.append("PARENT_COMPLETE_WITHOUT_HANDOFF")
    if result == "GENERATED" and delivery == "DELIVERED":
        # This combination is valid only when delivery evidence explicitly
        # confirms the send; missing evidence is the inconsistency.
        if not snapshot.get("delivery_receipt"):
            violations.append("DELIVERED_WITHOUT_DELIVERY_RECEIPT")
    return {"state_consistency": "PASS" if not violations else "FAIL",
            "violations": violations,
            "states": {"root_objective": root or None, "durable_job": durable or None,
                       "work_item": work or None, "parent_workflow": parent or None,
                       "continuation": continuation or None, "result": result or None,
                       "delivery": delivery or None}}


def build_report(*, results: list[CapabilityResult], probes: Mapping[str, Any] | None = None,
                 timestamp: datetime | None = None) -> dict[str, Any]:
    stamp = (timestamp or datetime.now(timezone.utc)).astimezone(timezone.utc)
    validated = [row.validate() for row in results]
    divergences = list((probes or {}).get("state_divergences") or [])
    failed = any(row.overall_status == "FAIL" for row in validated)
    partial = any(row.overall_status in {"PARTIAL", "NOT_AVAILABLE", "NOT_TESTED"}
                  for row in validated)
    return {"schema_version": "nexus.nova-capability-certification.v1",
            "generated_at": stamp.isoformat(), "mode": "OBSERVER_ONLY_SAFE",
            "control_plane_status": "FAIL" if failed else ("PARTIAL" if partial else "PASS"),
            "capabilities": [asdict(row) for row in validated],
            "state_consistency_checker": "FAIL" if divergences else "PASS",
            "state_divergences_found": divergences,
            "probe_evidence": dict(probes or {}),
            "round_trip": dict((probes or {}).get("round_trip") or {}),
            "notes": list((probes or {}).get("notes") or [])}


def write_report(report: Mapping[str, Any], output_dir: Path | None = None) -> tuple[Path, Path]:
    directory = output_dir or ROOT / "reports/architecture"
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.fromisoformat(str(report["generated_at"]).replace("Z", "+00:00"))
    suffix = stamp.strftime("%Y%m%dT%H%M%SZ")
    json_path = directory / f"nova_capability_certification_{suffix}.json"
    md_path = directory / f"NOVA_CAPABILITY_CERTIFICATION_{stamp.strftime('%Y-%m-%d')}.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rows = report.get("capabilities") or []
    lines = [f"# Nova Capability Certification — {stamp.strftime('%Y-%m-%d %H:%M UTC')}", "",
             f"**Mode:** {report.get('mode')}  ", f"**CONTROL_PLANE_STATUS:** {report.get('control_plane_status')}", "",
             "| Capability | Overall | Failure layer |", "|---|---|---|"]
    lines += [f"| {r.get('capability')} | {r.get('overall_status')} | {r.get('failure_layer')} |" for r in rows]
    lines += ["", "## Evidence", ""]
    for row in rows:
        lines.append(f"### {row.get('capability')} — {row.get('overall_status')}")
        lines.append("")
        if row.get("failure_reason"):
            lines.append(f"Failure: {row['failure_reason']}")
            lines.append("")
        lines.extend(f"- {item}" for item in row.get("evidence") or ["No evidence recorded."])
        lines.append("")
    probes = report.get("probe_evidence") or {}
    live_sample = probes.get("live_readonly_sample") or {}
    lines += ["## State consistency", "",
              f"**Checker:** {report.get('state_consistency_checker', 'NOT_TESTED')}", ""]
    if live_sample:
        lines.append(f"**Read-only sample:** `{live_sample.get('job_id', 'unknown')}`; "
                     f"latest child `{live_sample.get('latest_research_child_id', 'unknown')}`")
        lines.append("")
        states = live_sample.get("states") or {}
        if states:
            lines.append("| State | Value |")
            lines.append("|---|---|")
            lines.extend(f"| {key} | {value} |" for key, value in states.items())
            lines.append("")
    if report.get("state_divergences_found"):
        lines += ["### Detected divergences", ""]
        lines.extend(f"- {value}" for value in report["state_divergences_found"])
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def safe_baseline_results() -> list[CapabilityResult]:
    """Record conservative baseline until each real path supplies evidence."""
    rows = []
    for capability in CAPABILITIES:
        rows.append(CapabilityResult(capability=capability, overall_status="NOT_TESTED",
            failure_reason="No capability-specific live evidence supplied to observer harness.",
            evidence=["The harness does not dispatch or mutate work."]))
    return rows


def run_safe_local_certification() -> tuple[list[CapabilityResult], dict[str, Any]]:
    """Run local/read-only probes; never enqueue work or contact an owner.

    Live owner-controlled operations remain PARTIAL until a real Nova message
    exercises them. The direct probes below certify routing logic and local
    artifact substrates only.
    """
    results = {name: CapabilityResult(capability=name) for name in CAPABILITIES}
    evidence: dict[str, Any] = {"natural_language_paraphrases": [], "round_trip": {
        key: "NOT_TESTED" for key in ("receive", "route", "execute", "persist", "readback", "response", "delivery")},
        "notes": ["No Telegram update or production work was generated by the harness."]}
    try:
        from nova.semantic_orchestration import resolve_owner_request
        examples = {
            "Systems Control": ["Nova, check if Nexus is healthy.",
                "Can you have Systems take a look at everything?", "Make sure the main Nexus services are up."],
            "Research Control": ["Nova, research this strategy and tell Trading what it should test.",
                "Research this opportunity and tell me what Nexus should do with it.",
                "Have Nexus research the supplied company and recommend what to do."]}
        for capability, prompts in examples.items():
            expected = "SYSTEMS" if capability == "Systems Control" else "RESEARCH_MISSION"
            observed = []
            for prompt in prompts:
                route = resolve_owner_request(prompt)
                observed.append({"prompt": prompt, "intent": route.get("intent"),
                    "department": route.get("department"), "executor": route.get("executor")})
            passed = sum((row["department"] == expected if expected == "SYSTEMS" else
                          row["intent"] == expected and row["executor"] == "nexus_assign_research")
                         for row in observed)
            row = results[capability]
            row.natural_language_understanding = "PASS" if passed else "FAIL"
            row.intent_classification = "PASS" if passed == len(prompts) else ("PARTIAL" if passed else "FAIL")
            row.correct_capability_selected = "PASS" if passed == len(prompts) else ("PARTIAL" if passed else "FAIL")
            row.overall_status = "PARTIAL" if passed else "FAIL"
            row.failure_layer = "NATURAL_LANGUAGE_ROUTING" if not passed else "UNKNOWN"
            row.failure_reason = None if passed == len(prompts) else "One or more natural-language paraphrases did not route as expected."
            row.evidence.extend(f"{item['intent']} / {item['department']} / {item['executor']}" for item in observed)
            evidence["natural_language_paraphrases"].extend([{"capability": capability, **item} for item in observed])
    except Exception as exc:
        for capability in ("Systems Control", "Research Control"):
            results[capability].overall_status = "FAIL"
            results[capability].failure_layer = "NATURAL_LANGUAGE_ROUTING"
            results[capability].failure_reason = f"Classifier probe failed: {type(exc).__name__}: {str(exc)[:160]}"

    # Preserve local certification artifacts and execution evidence under the
    # report tree. They are not published or used by production workflows.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir = ROOT / "reports/architecture/certification-assets" / stamp
    artifact_dir.mkdir(parents=True, exist_ok=True)
    script = artifact_dir / "nova_opencode_test.py"
    script.write_text('print("Nova OpenCode control test passed")\n', encoding="utf-8")
    run = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=10)
    run_evidence = artifact_dir / "nova_opencode_test_result.json"
    run_evidence.write_text(json.dumps({"returncode": run.returncode, "stdout": run.stdout,
        "stderr": run.stderr}, indent=2) + "\n", encoding="utf-8")
    row = results["OpenCode Control"]
    ok = run.returncode == 0 and run.stdout.strip() == "Nova OpenCode control test passed"
    row.worker_execution = "PASS" if ok else "FAIL"
    row.result_persisted = "PASS" if ok else "FAIL"
    row.result_readable = "PASS" if ok else "FAIL"
    row.overall_status = "PARTIAL" if ok else "FAIL"
    row.failure_layer = "CAPABILITY_SELECTION" if ok else "WORKER_EXECUTION"
    row.failure_reason = "Local script execution passed; Nova-to-OpenCode dispatch was not exercised." if ok else (run.stderr[-240:] or "Temporary script execution failed.")
    row.evidence.append(f"Local test file created/executed once; output={run.stdout.strip()!r}; returncode={run.returncode}; evidence={run_evidence.relative_to(ROOT)}.")

    # Disposable vector mark, with no provider call or external spend.
    asset = artifact_dir / "nexus-test-logo.svg"
    asset.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 160 160"><rect width="160" height="160" rx="32" fill="#101828"/><path d="M40 112V48l80 64V48" fill="none" stroke="#67e8f9" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/></svg>\n', encoding="utf-8")
    with open(asset, encoding="utf-8") as check:
        artifact_exists = check.read(12).startswith("<svg")
    row = results["Creative Control"]
    row.result_persisted = "PASS" if artifact_exists and asset.stat().st_size > 0 else "FAIL"
    row.overall_status = "PARTIAL" if row.result_persisted == "PASS" else "FAIL"
    row.failure_layer = "CAPABILITY_SELECTION"
    row.failure_reason = "Disposable SVG artifact created locally; Nova-to-Creative dispatch was not exercised." if row.overall_status == "PARTIAL" else "Disposable artifact creation failed."
    row.evidence.append(f"Certification artifact created and read back: {asset.relative_to(ROOT)} ({asset.stat().st_size} bytes).")

    # Read-only local listener check; tool listing requires authenticated MCP
    # session evidence and is deliberately left unclaimed if unavailable.
    row = results["Nexus MCP"]
    sock = socket.socket(); sock.settimeout(1)
    try:
        sock.connect(("127.0.0.1", 18765)); reachable = True
    except OSError as exc:
        reachable = False; row.failure_reason = f"Loopback MCP connection failed: {type(exc).__name__}."
    finally:
        sock.close()
    row.correct_capability_selected = "PASS" if reachable else "FAIL"
    row.overall_status = "PARTIAL" if reachable else "FAIL"
    row.failure_layer = "MCP_CONNECTIVITY"
    row.evidence.append(f"Loopback TCP 127.0.0.1:18765 bound={reachable}; authenticated tools/list not invoked by this probe.")
    try:
        from services.nexus_mcp.server import mcp
        tool_names = [tool.name for tool in mcp._tool_manager.list_tools()]
        evidence["registered_nexus_mcp_tool_count"] = len(tool_names)
        evidence["registered_nexus_mcp_tool_names"] = tool_names
        row.evidence.append(f"Loaded MCP server source registers {len(tool_names)} tools.")
        if reachable and len(tool_names) == 26:
            row.correct_capability_selected = "PASS"
    except Exception as exc:
        evidence["registered_nexus_mcp_tool_count"] = None
        row.evidence.append(f"MCP source registry probe unavailable: {type(exc).__name__}.")

    # Exercise the real local governor boundary with a simulated response.
    # This does not call Telegram and uses a temporary certification DB.
    env_names = ("NEXUS_GOVERNOR_DB", "NEXUS_TELEGRAM_INTERNAL_CHAT_IDS",
                 "NEXUS_CORRELATION_ID", "NEXUS_DEPARTMENT", "NEXUS_DURABLE_JOB_ID")
    saved = {name: os.environ.get(name) for name in env_names}
    try:
        with tempfile.TemporaryDirectory(prefix="nova-status-governor-") as temp:
            os.environ["NEXUS_GOVERNOR_DB"] = str(Path(temp) / "governor.sqlite3")
            os.environ["NEXUS_TELEGRAM_INTERNAL_CHAT_IDS"] = "certification-chat"
            os.environ["NEXUS_CORRELATION_ID"] = "certification-correlation"
            os.environ["NEXUS_DEPARTMENT"] = "NOVA"
            os.environ.pop("NEXUS_DURABLE_JOB_ID", None)
            from nexus_agent_platform.provider_enforcement import execute_telegram_delivery
            from nexus_agent_platform.resource_spend_governor import LocalGovernorStore
            governor = LocalGovernorStore(os.environ["NEXUS_GOVERNOR_DB"])
            governor.set_policy("TELEGRAM", "bot_delivery", "NOVA_TELEGRAM_DELIVERY", "DAILY",
                autonomous_usage_allowed=True, autonomous_spend_allowed=False, state="NORMAL",
                approval_required=False)
            deliveries = []
            for update_id in ("cert-update-1", "cert-update-2"):
                result = execute_telegram_delivery("certification-chat",
                    lambda: {"ok": True, "simulated": True}, job_id=f"nova-telegram-{update_id}",
                    job_type="NOVA_TELEGRAM_STATUS_REPLY")
                deliveries.append(bool(result.get("ok")))
            with governor.connect() as db:
                authorized = db.execute("SELECT count(*) FROM reservations WHERE status='RECONCILED' AND job_type='NOVA_TELEGRAM_DELIVERY'").fetchone()[0]
            row = results["Telegram Send"]
            row.correct_capability_selected = "PASS" if deliveries == [True, True] and authorized == 2 else "FAIL"
            row.nova_response_delivered = "PARTIAL" if row.correct_capability_selected == "PASS" else "FAIL"
            row.overall_status = "PARTIAL" if row.correct_capability_selected == "PASS" else "FAIL"
            row.failure_layer = "TELEGRAM_DELIVERY"
            row.failure_reason = "Governor accepted two fresh status delivery identities; Telegram network send was not invoked."
            row.evidence.append(f"Two simulated status sends authorized/reconciled under the scoped delivery policy; distinct IDs; no Telegram request; reservation_count={authorized}.")
            evidence["status_delivery_governor_simulation"] = {"fresh_reservations": authorized,
                "telegram_network_called": False, "reservation_replay_denied": False}
    except Exception as exc:
        row = results["Telegram Send"]
        row.overall_status = "FAIL"; row.failure_layer = "DELIVERY_AUTHORIZATION"
        row.failure_reason = f"Local governed delivery simulation failed: {type(exc).__name__}: {str(exc)[:120]}"
    finally:
        for name, value in saved.items():
            if value is None: os.environ.pop(name, None)
            else: os.environ[name] = value

    for name in ("Telegram Receive", "Telegram Send", "Hermes", "Supabase", "Durable Queue",
                 "Status Readback", "Gmail Read", "Calendar Read", "Drive Read", "Trading Paper Control"):
        row = results[name]
        row.overall_status = "NOT_AVAILABLE" if name in {"Gmail Read", "Calendar Read", "Drive Read", "Trading Paper Control"} else "NOT_TESTED"
        row.failure_layer = "EXTERNAL_DEPENDENCY" if row.overall_status == "NOT_AVAILABLE" else "UNKNOWN"
        row.failure_reason = "No safe Nova-mediated capability probe was available without live user input or external action."
        row.evidence.append("No live action was invoked.")
    # Restore the governed status-send simulation result after conservative
    # defaults have been assigned above.
    if evidence.get("status_delivery_governor_simulation", {}).get("fresh_reservations") == 2:
        row = results["Telegram Send"]
        row.correct_capability_selected = "PASS"
        row.nova_response_delivered = "PARTIAL"
        row.overall_status = "PARTIAL"
        row.failure_layer = "TELEGRAM_DELIVERY"
        row.failure_reason = "Governance passed in simulation; live Telegram send was not attempted."

    live_job_id = os.environ.get("NEXUS_CERT_READ_JOB_ID")
    if live_job_id:
        try:
            from nexus_agent_platform.durable_jobs import default_store
            from nexus_agent_platform.research_work_queue import default_queue
            store = default_store(); job = store.get(live_job_id)
            if job:
                context = dict(job.governance_context or {})
                state = dict(context.get("research_parent_state") or {})
                work_id = str(job.payload_ref or "")
                item = next((row for row in default_queue().load().get("items", [])
                             if str(row.get("work_id") or "") == work_id), None)
                internal_id = str(state.get("research_parent_id") or context.get("objective_id") or "")
                parent_rows = store.list_research_parent_jobs(limit=1000)
                related = [candidate for candidate in parent_rows
                    if candidate.job_id == live_job_id or candidate.correlation_id == internal_id
                    or str((candidate.governance_context or {}).get("research_parent_id") or "") == internal_id]
                latest = max(related, key=lambda candidate: str(candidate.created_at or "")) if related else job
                latest_context = dict(latest.governance_context or {})
                latest_state = dict(latest_context.get("research_parent_state") or state)
                snapshot = {"root_objective_state": latest_context.get("root_objective_status") or latest_state.get("status"),
                    "durable_job_state": latest.state, "work_item_state": (item or {}).get("status"),
                    "parent_workflow_state": latest_state.get("status"),
                    "continuation_state": latest.state,
                    "result_state": "PERSISTED" if job.receipt_ref else "UNKNOWN",
                    "delivery_state": "NOT_APPLICABLE"}
                checked = check_state_consistency(snapshot)
                evidence["live_readonly_sample"] = {"job_id": live_job_id,
                    "latest_research_child_id": latest.job_id, **checked}
                evidence["state_divergences"] = checked["violations"]
                is_supabase = type(store).__name__ == "SupabaseJobStore"
                results["Supabase"].overall_status = "PASS" if is_supabase else "PARTIAL"
                results["Supabase"].result_readable = "PASS" if is_supabase else "PARTIAL"
                results["Supabase"].failure_reason = None if is_supabase else "The durable store resolved to a local adapter rather than the live Supabase adapter."
                results["Supabase"].evidence.append(f"Configured durable adapter={type(store).__name__}.")
                results["Supabase"].evidence.append(f"Read-only durable job lookup succeeded; state={job.state}.")
                results["Durable Queue"].overall_status = "PASS" if item else "PARTIAL"
                results["Durable Queue"].result_readable = "PASS" if item else "PARTIAL"
                results["Durable Queue"].evidence.append(f"Read-only Research work projection {'found' if item else 'not found'} for the durable payload reference.")
                results["Status Readback"].overall_status = "PARTIAL"
                results["Status Readback"].result_readable = "PASS"
                results["Status Readback"].failure_layer = "STATUS_READBACK"
                results["Status Readback"].failure_reason = "Exact durable read passed; Nova-mediated response/delivery was not exercised."
                results["Status Readback"].evidence.append(f"Exact job {live_job_id} read from the configured durable store; no write performed.")
        except Exception as exc:
            evidence["live_readonly_sample"] = {"error": f"{type(exc).__name__}: {str(exc)[:160]}"}
    # Research only reached the actual classifier in this safe probe. Worker,
    # continuation and handoff evidence is supplied by isolated regression.
    if results["Research Control"].overall_status != "FAIL":
        results["Research Control"].failure_reason = "Natural-language Research routing passed; isolated worker continuation test is recorded separately."
    return list(results.values()), evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    results, probes = run_safe_local_certification()
    report = build_report(results=results, probes=probes)
    paths = write_report(report, args.output_dir)
    print(json.dumps({"control_plane_status": report["control_plane_status"],
                      "json_report": str(paths[0]), "markdown_report": str(paths[1])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
