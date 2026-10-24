"""Nexus Study Runner — bounded, read-only systematic Nexus study pass.

This is a TRUSTED RUNTIME script. It is NOT part of Nova's capability layer.
It collects source snapshots, studies each domain, cross-checks contradictions,
identifies facts/gaps/unknowns, and writes a safe local study artifact.

Nova write permissions remain 0. The study artifact is written by this runner.

Usage:
    python -m nexus_agent_platform.study.study_runner [--passes N] [--out DIR]

Bounded: '--passes' accepts 1..4 (hard maximum). Each pass re-scans live
sources; the artifact is written after the first pass and can be refreshed.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

log = logging.getLogger(__name__)

_MAX_PASSES = 4
_DEFAULT_OUT = "reports/nova_study"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def _commit_sha(root: Path) -> str:
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(root), capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()[:12] or "unknown"
    except Exception:
        pass
    return "unknown"


def _run_study_pass(domain_names: List[str]) -> Dict[str, Any]:
    """Run one full study pass: collect snapshots, summarize, reconcile."""
    from nexus_agent_platform.capabilities import nexus_study

    readers = {
        "system_architecture": nexus_study.get_architecture_summary,
        "agents": nexus_study.get_agent_inventory,
        "tools": nexus_study.get_tool_inventory,
        "processes": nexus_study.get_process_inventory,
        "runtime": nexus_study.get_runtime_execution_summary,
        "product": nexus_study.get_product_inventory,
        "client_workflow": nexus_study.get_client_workflow_summary,
        "business_model": nexus_study.get_business_model_summary,
        "integrations": nexus_study.get_integration_inventory,
        "security": nexus_study.get_security_boundary_summary,
        "reports": nexus_study.get_safe_report_index,
        "repo_map": nexus_study.get_repo_system_map,
        "recent_changes": nexus_study.get_recent_system_changes,
        "gaps": nexus_study.get_nexus_gap_summary,
        "unknowns": nexus_study.get_nexus_unknowns,
        "snapshot": nexus_study.get_nexus_study_snapshot,
    }

    study: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    for name in domain_names:
        reader = readers.get(name)
        if reader is None:
            continue
        try:
            study[name] = reader() if name != "recent_changes" else reader(limit=10)
        except Exception as exc:
            errors[name] = str(exc)
            study[name] = {"status": "error", "error": str(exc)}

    # Cross-source reconciliation: registry vs telemetry contradictions
    contradictions = []
    processes_data = study.get("processes", {})
    runtime_data = study.get("runtime", {})
    if isinstance(processes_data, dict):
        for p in processes_data.get("processes", []):
            pid = p.get("process_id")
            config_state = p.get("configuration_state")
            runtime_state = p.get("runtime_state")
            if config_state == "enabled" and runtime_state in ("simulated", "skipped", "blocked", "never_run"):
                contradictions.append({
                    "kind": "configured_vs_runtime",
                    "entity": pid,
                    "registry": f"configuration_state={config_state}",
                    "runtime": f"runtime_state={runtime_state}",
                    "interpretation": "CONFIGURED_NOT_EXECUTING or NOT_TELEMETRY_COVERED",
                })

    business = study.get("business_model", {})
    if isinstance(business, dict):
        if business.get("operational_revenue_paths"):
            for path in business["operational_revenue_paths"]:
                if business.get("stripe_live_mode_allowed") is False:
                    contradictions.append({
                        "kind": "planned_vs_operational",
                        "entity": path.get("offer_id"),
                        "registry": "operational_revenue_paths includes this",
                        "runtime": "stripe live mode not allowed",
                        "interpretation": "offers may appear operational but payment path is test-only",
                    })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _commit_sha(_repo_root()),
        "domains": study,
        "contradictions": contradictions,
        "errors": errors,
    }


def write_study_artifacts(pass_result: Dict[str, Any], out_dir: Path) -> List[str]:
    """Write safe local study artifacts (snapshot, summary, gaps, unknowns)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []

    # Study index / snapshot
    snapshot_path = out_dir / "nexus_study_snapshot.json"
    snapshot = pass_result.get("domains", {}).get("snapshot", {})
    snapshot["contradictions"] = pass_result.get("contradictions", [])
    snapshot["study_errors"] = pass_result.get("errors", {})
    snapshot_path.write_text(json.dumps(snapshot, indent=2, default=str))
    written.append(str(snapshot_path))

    # Gaps
    gaps_path = out_dir / "nexus_gaps.json"
    gaps_data = pass_result.get("domains", {}).get("gaps", {})
    if not isinstance(gaps_data, dict):
        gaps_data = {"gap_count": 0, "gaps": []}
    gaps_path.write_text(json.dumps(gaps_data, indent=2, default=str))
    written.append(str(gaps_path))

    # Unknowns
    unknowns_path = out_dir / "nexus_unknowns.json"
    unknowns_data = pass_result.get("domains", {}).get("unknowns", {})
    if not isinstance(unknowns_data, dict):
        unknowns_data = {"unknown_count": 0, "unknowns": []}
    unknowns_path.write_text(json.dumps(unknowns_data, indent=2, default=str))
    written.append(str(unknowns_path))

    # Bounded human summary
    summary_path = out_dir / "nexus_study_summary.md"
    summary = _build_summary_markdown(pass_result)
    summary_path.write_text(summary)
    written.append(str(summary_path))

    return written


def _build_summary_markdown(pass_result: Dict[str, Any]) -> str:
    """Build a bounded readable study summary."""
    lines = [
        "# Nexus Study Summary",
        "",
        f"- Generated: {pass_result.get('generated_at', 'unknown')}",
        f"- Source commit: {pass_result.get('source_commit', 'unknown')}",
        "",
    ]

    domains = pass_result.get("domains", {})

    # System
    snapshot = domains.get("snapshot", {})
    system = snapshot.get("system", {})
    if system:
        lines += [
            "## What Nexus Is",
            "",
            f"- Name: {system.get('name')}",
            f"- Purpose: {system.get('purpose')}",
            f"- Agents: {system.get('agent_count')}",
            f"- Processes: {system.get('process_count')} (enabled: {system.get('enabled_processes')})",
            "",
        ]

    # Processes
    processes = domains.get("processes", {})
    if isinstance(processes, dict):
        lines += [
            "## Processes",
            "",
            f"- Total: {processes.get('total', 0)}",
            f"- Configuration: {processes.get('configuration_counts', {})}",
            f"- Runtime: {processes.get('runtime_counts', {})}",
            f"- Has real execution: {processes.get('has_real_execution', False)}",
            f"- All simulated/skipped: {processes.get('all_simulated_or_skipped', False)}",
            "",
        ]

    # Business
    business = domains.get("business_model", {})
    if isinstance(business, dict):
        lines += [
            "## Business Model",
            "",
            f"- Offers: {business.get('offers_count', 0)}",
            f"- Operational revenue paths: {len(business.get('operational_revenue_paths', []))}",
            f"- Planned revenue paths: {len(business.get('planned_revenue_paths', []))}",
            f"- Stripe mode: {business.get('stripe_mode')} (live allowed: {business.get('stripe_live_mode_allowed')})",
            "",
        ]

    # Integrations
    integrations = domains.get("integrations", {})
    if isinstance(integrations, dict):
        lines += [
            "## Integrations",
            "",
            f"- Connectors: {integrations.get('connector_count', 0)}",
            f"- Live enabled: {integrations.get('live_enabled_count', 0)}",
            f"- Status counts: {integrations.get('status_counts', {})}",
            "",
        ]

    # Gaps
    gaps = domains.get("gaps", {})
    if isinstance(gaps, dict) and gaps.get("gaps"):
        lines += ["## Top Gaps", ""]
        for g in gaps["gaps"][:10]:
            lines.append(f"- **{g.get('gap_id')}** [{g.get('domain')}] {g.get('title')}")
        lines.append("")

    # Unknowns
    unknowns = domains.get("unknowns", {})
    if isinstance(unknowns, dict) and unknowns.get("unknowns"):
        lines += ["## Unknowns", ""]
        for u in unknowns["unknowns"][:10]:
            lines.append(f"- **{u.get('unknown_id')}** {u.get('title')}")
        lines.append("")

    # Contradictions
    contradictions = pass_result.get("contradictions", [])
    if contradictions:
        lines += ["## Contradictions (Nexus tells two stories)", ""]
        for c in contradictions[:15]:
            lines.append(
                f"- {c.get('kind')}: {c.get('entity')} — "
                f"registry says {c.get('registry')}, runtime says {c.get('runtime')}"
            )
        lines.append("")

    # Errors
    errors = pass_result.get("errors", {})
    if errors:
        lines += ["## Study Errors", ""]
        for name, err in errors.items():
            lines.append(f"- {name}: {err[:200]}")
        lines.append("")

    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Bounded Nexus study pass")
    parser.add_argument("--passes", type=int, default=1, help="Number of passes (1..%d)" % _MAX_PASSES)
    parser.add_argument("--out", default=_DEFAULT_OUT, help="Output directory for study artifacts")
    parser.add_argument("--domains", nargs="*", default=None,
                        help="Optional domain subset (default: all)")
    args = parser.parse_args(argv)

    passes = max(1, min(args.passes, _MAX_PASSES))
    all_domains = [
        "system_architecture", "agents", "tools", "processes", "runtime",
        "product", "client_workflow", "business_model", "integrations",
        "security", "reports", "repo_map", "recent_changes", "gaps",
        "unknowns", "snapshot",
    ]
    domains = args.domains if args.domains else all_domains

    import subprocess
    subprocess.run(["mkdir", "-p", str(_repo_root() / "reports" / "nova_study")], check=False)

    print(f"Nexus study pass — starting commit {_commit_sha(_repo_root())}")
    print(f"Passes: {passes} | Domains: {len(domains)}")

    final = None
    for i in range(passes):
        print(f"  pass {i + 1}/{passes}...", flush=True)
        start = time.time()
        final = _run_study_pass(domains)
        duration = time.time() - start
        final["duration_seconds"] = round(duration, 2)
        print(f"  pass {i + 1} done in {duration:.1f}s — "
              f"domains={len(final['domains'])} contradictions={len(final['contradictions'])} errors={len(final['errors'])}")

    out_dir = _repo_root() / args.out
    written = write_study_artifacts(final, out_dir)
    print("\nStudy artifacts written:")
    for w in written:
        print(f"  {w}")

    summary_md = out_dir / "nexus_study_summary.md"
    if summary_md.exists():
        print("\n=== STUDY SUMMARY ===\n")
        print(summary_md.read_text())

    return 0


if __name__ == "__main__":
    sys.exit(main())