"""Nexus Study Layer — governed read-only system discovery for Hermes Nova.

Nova may study, read, correlate, reason, observe, and recommend.
Nova may NOT modify Nexus, execute arbitrary code, or gain any write access.

This layer exposes BOUNDED, provenance-tagged reads over repository
configuration, docs, reports, and runtime state so Nova can build a
structured understanding of Nexus as a SYSTEM.

Principles:
  - Every read is read-only and bounded (no giant dumps into one context).
  - Every fact carries provenance: source_type, source_ref, freshness.
  - No secrets, credentials, raw client PII, or arbitrary file execution.
  - Study reads follow the same safe _handle_* -> allowlist pattern as
    the certified Nexus knowledge layer.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")

# Config registries that encode business/product/architecture knowledge
_OFFER_REGISTRY_PATH = os.path.join(_REPO_ROOT, "configs", "offer_registry.json")
_STRIPE_PRODUCT_PATH = os.path.join(_REPO_ROOT, "configs", "stripe_product_registry.json")
_REVENUE_FUNNEL_PATH = os.path.join(_REPO_ROOT, "configs", "revenue_funnel_registry.json")
_CONNECTOR_REGISTRY_PATH = os.path.join(_REPO_ROOT, "configs", "connector_registry.json")
_MONETIZATION_SAFETY_PATH = os.path.join(_REPO_ROOT, "configs", "monetization_safety_policy.json")
_ACTIVATION_CHECKLIST_PATH = os.path.join(_REPO_ROOT, "configs", "nexus_100_step_activation_checklist.json")
_RESEARCH_SOURCE_PATH = os.path.join(_REPO_ROOT, "configs", "research_source_registry.json")
_AUTOMATION_SCHEDULE_PATH = os.path.join(_REPO_ROOT, "configs", "automation_schedule_registry.json")
_CLI_CAPABILITY_PATH = os.path.join(_REPO_ROOT, "configs", "cli_capability_registry.json")

# Process registry (dynamic)
_PROCESS_REGISTRY_PATH = os.path.join(_REPO_ROOT, "data", "operations", "nexus_process_registry.json")
_STUDY_ARTIFACT_DIR = os.path.join(_REPO_ROOT, "reports", "nova_study")
_STUDY_SNAPSHOT_PATH = os.path.join(_STUDY_ARTIFACT_DIR, "nexus_study_snapshot.json")
_STUDY_GAPS_PATH = os.path.join(_STUDY_ARTIFACT_DIR, "nexus_gaps.json")
_STUDY_UNKNOWNS_PATH = os.path.join(_STUDY_ARTIFACT_DIR, "nexus_unknowns.json")


def _safe_json_load(path: str) -> Optional[Any]:
    """Load a JSON file safely, returning None on any error."""
    try:
        if not os.path.isfile(path):
            return None
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def _artifact_snapshot() -> Optional[Dict[str, Any]]:
    """Return the latest generated study snapshot artifact if available."""
    data = _safe_json_load(_STUDY_SNAPSHOT_PATH)
    if isinstance(data, dict) and data.get("status") == "success":
        data = dict(data)
        data.setdefault("source_type", "study_snapshot_artifact")
        data.setdefault("freshness", "generated_study_snapshot")
        data.setdefault("source_ref", "reports/nova_study/nexus_study_snapshot.json")
        return data
    return None


def _artifact_domain(domain: str) -> Optional[Dict[str, Any]]:
    snapshot = _artifact_snapshot()
    if not snapshot:
        return None
    domains = snapshot.get("domains", {})
    data = domains.get(domain)
    if not isinstance(data, dict):
        return None
    result = dict(data)
    result.setdefault("source_type", data.get("source_type", "study_snapshot_artifact"))
    result["source_ref"] = "reports/nova_study/nexus_study_snapshot.json"
    result["source_commit"] = snapshot.get("source_commit")
    result["generated_at"] = snapshot.get("generated_at")
    result["freshness"] = "generated_study_snapshot"
    return result


def _artifact_file(path: str, source_ref: str) -> Optional[Dict[str, Any]]:
    data = _safe_json_load(path)
    if not isinstance(data, dict) or data.get("status") != "success":
        return None
    result = dict(data)
    snapshot = _artifact_snapshot()
    if snapshot:
        result["source_commit"] = snapshot.get("source_commit")
        result["generated_at"] = snapshot.get("generated_at")
    result["source_ref"] = source_ref
    result["freshness"] = "generated_study_snapshot"
    return result


def _with_current_runtime_reconciliation(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Attach current runtime status without mutating historical study facts."""
    result = dict(snapshot)
    domains = result.get("domains", {})
    study_processes = domains.get("processes", {}) if isinstance(domains, dict) else {}
    study_has_real = study_processes.get("has_real_execution")
    try:
        from nexus_agent_platform.runtime.execution_telemetry import query_runtime_telemetry

        runtime = query_runtime_telemetry(operation="overview", window="last_24_hours", limit=5)
        event_count = runtime.get("summary", {}).get("event_count", 0)
        result["current_runtime_update"] = {
            "source_type": "verified_execution_telemetry",
            "freshness": "current_runtime",
            "telemetry_available_now": event_count > 0,
            "event_count_24h": event_count,
            "coverage": runtime.get("coverage", {}),
            "summary": runtime.get("summary", {}),
            "latest_runs": runtime.get("runs", [])[:5],
        }
        result["study_current_reconciliation"] = {
            "study_has_real_execution": study_has_real,
            "current_has_verified_execution_telemetry": event_count > 0,
            "changed_findings": (
                [
                    {
                        "id": "NEXUS-U01",
                        "title": "Which processes have verified real execution?",
                        "study_state": "unknown / insufficient evidence",
                        "current_state": "verified execution telemetry is now available",
                        "status": "partially_resolved_by_current_runtime_telemetry",
                    }
                ]
                if study_has_real is False and event_count > 0 else []
            ),
            "note": (
                "The study snapshot is historical. Current runtime telemetry is reported separately "
                "and must not overwrite the snapshot facts."
            ),
        }
    except Exception as exc:
        result["current_runtime_update"] = {
            "source_type": "verified_execution_telemetry",
            "freshness": "unavailable",
            "telemetry_available_now": False,
            "error_type": exc.__class__.__name__,
        }
    return result


def _safe_file_exists(path: str) -> bool:
    """Check if a file exists safely."""
    try:
        return os.path.isfile(path)
    except Exception:
        return False


def _source_commit() -> str:
    """Return the current git HEAD short SHA, or 'unknown'."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()[:12] or "unknown"
    except Exception:
        pass
    return "unknown"


def _bounded_markdown_notes(path: str, max_lines: int = 40) -> List[str]:
    """Return a bounded slice of a markdown file's content (headings + visible brevity)."""
    if not _safe_file_exists(path):
        return []
    try:
        with open(path) as f:
            lines = f.readlines()[:max_lines]
        # Keep non-empty lines only
        return [line.rstrip() for line in lines if line.strip()][:max_lines]
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
# 1. SYSTEM ARCHITECTURE STUDY
# ═══════════════════════════════════════════════════════════════

def get_architecture_summary() -> Dict[str, Any]:
    """Return a bounded architecture-level study of how Nexus is built."""
    artifact = _artifact_domain("system_architecture")
    if artifact:
        return artifact

    from nexus_agent_platform.capabilities.nexus_knowledge import (
        NEXUS_SYSTEM, get_nexus_architecture,
    )

    base = get_nexus_architecture()
    repo_top = []
    try:
        for entry in sorted(os.listdir(_REPO_ROOT)):
            full = os.path.join(_REPO_ROOT, entry)
            if entry.startswith("."):
                continue
            kind = "dir" if os.path.isdir(full) else "file"
            repo_top.append({"name": entry, "kind": kind})
    except Exception:
        pass

    # Count scripts packages (bounded: top-level of scripts/)
    script_packages = []
    scripts_dir = os.path.join(_REPO_ROOT, "scripts")
    try:
        if os.path.isdir(scripts_dir):
            for entry in sorted(os.listdir(scripts_dir)):
                if os.path.isdir(os.path.join(scripts_dir, entry)) and not entry.startswith("."):
                    script_packages.append(entry)
    except Exception:
        pass

    # Frontend stack from package.json (bounded)
    frontend_deps = {}
    pkg_path = os.path.join(_REPO_ROOT, "package.json")
    pkg = _safe_json_load(pkg_path)
    if isinstance(pkg, dict):
        deps = pkg.get("dependencies", {})
        frontend_deps = {k: v for k, v in list(deps.items())[:8]}

    return {
        "status": "success",
        "architecture": base.get("architecture"),
        "runtime_model": base.get("runtime_model"),
        "major_components": NEXUS_SYSTEM.get("major_components", [])[:8],
        "integration_boundaries": {
            k: v for k, v in NEXUS_SYSTEM.get("integration_boundaries", {}).items()
        },
        "repo_top_level": repo_top[:40],
        "script_packages": script_packages[:40],
        "frontend_dependencies": frontend_deps,
        "source_commit": _source_commit(),
        "source_type": "repo_scan",
        "freshness": "current_commit",
        "verification_complete": True,
    }


def get_agent_inventory() -> Dict[str, Any]:
    """Return a structured study profile of all agents and their boundaries."""
    from nexus_agent_platform.capabilities.nexus_knowledge import (
        AGENTS, get_agent_registry,
    )

    reg = get_agent_registry()
    agents = []
    for aid, a in AGENTS.items():
        agents.append({
            "agent_id": aid,
            "name": a.get("name"),
            "role": a.get("role"),
            "runtime_status": a.get("runtime_status"),
            "model": a.get("model"),
            "provider": a.get("provider"),
            "read_count": len(a.get("permissions", {}).get("reads", [])),
            "write_count": len(a.get("permissions", {}).get("writes", [])),
            "tool_count": len(a.get("tools", [])),
            "isolation": {k: str(v)[:80] for k, v in a.get("isolation", {}).items()},
        })
    return {
        "status": "success",
        "agents": agents,
        "specialist_count": reg.get("specialist_profiles", 0) if isinstance(reg, dict) else 0,
        "source_type": "agent_registry",
        "freshness": "current_commit",
        "verification_complete": True,
    }


def get_tool_inventory() -> Dict[str, Any]:
    """Return the canonical tool registry with bounded per-category detail."""
    from nexus_agent_platform.capabilities.nexus_knowledge import (
        TOOL_REGISTRY, get_tool_registry,
    )

    reg = get_tool_registry()
    categories = reg.get("categories", [])
    category_detail = {}
    source = TOOL_REGISTRY
    for cat in categories:
        items = source.get(cat, [])
        if isinstance(items, list):
            category_detail[cat] = {"count": len(items), "tools": items[:10]}
    return {
        "status": "success",
        "categories": category_detail,
        "category_list": categories,
        "total": reg.get("total", 0),
        "usable_now": reg.get("usable_now", 0),
        "counts": {
            "internal_safe": reg.get("internal_safe_count", 0),
            "read_only": reg.get("read_only_count", 0),
            "approval_gated": reg.get("approval_gated_count", 0),
            "unavailable": reg.get("unavailable_count", 0),
        },
        "reconciliation": reg.get("reconciliation", {}),
        "source_type": "tool_registry",
        "freshness": "current_commit",
        "verification_complete": True,
    }


def get_process_inventory() -> Dict[str, Any]:
    """Return the normalized process registry with three independent dimensions."""
    from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live

    reg = get_process_registry_live()
    processes = [
        {
            "process_id": p.get("process_id"),
            "name": p.get("name"),
            "configuration_state": p.get("configuration_state"),
            "execution_mode": p.get("execution_mode"),
            "runtime_state": p.get("runtime_state"),
            "schedule": p.get("schedule"),
        }
        for p in reg.get("processes", [])
    ]
    return {
        "status": reg.get("status", "success"),
        "total": reg.get("total", 0),
        "configuration_counts": reg.get("configuration_counts", {}),
        "mode_counts": reg.get("mode_counts", {}),
        "runtime_counts": reg.get("runtime_counts", {}),
        "has_real_execution": reg.get("has_real_execution", False),
        "all_simulated_or_skipped": reg.get("all_simulated_or_skipped", False),
        "reconciliation": reg.get("reconciliation", {}),
        "processes": processes,
        "source_type": "process_registry",
        "freshness": "current_registry",
        "verification_complete": True,
    }


def get_runtime_execution_summary() -> Dict[str, Any]:
    """Return verified runtime telemetry summary."""
    from nexus_agent_platform.runtime.execution_telemetry import query_runtime_telemetry

    try:
        res = query_runtime_telemetry(operation="overview")
        return {
            "status": "success",
            "data": res if isinstance(res, dict) else {"overview": res},
            "source_type": "verified_execution_telemetry",
            "freshness": "live",
            "verification_complete": True,
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "source_type": "verified_execution_telemetry",
            "freshness": "unknown",
            "verification_complete": False,
        }


# ═══════════════════════════════════════════════════════════════
# 2. PRODUCT STUDY
# ═══════════════════════════════════════════════════════════════

def get_product_inventory() -> Dict[str, Any]:
    """Return the product/offer catalog with fulfillment and stripe status."""
    offers_data = _safe_json_load(_OFFER_REGISTRY_PATH)
    stripe_data = _safe_json_load(_STRIPE_PRODUCT_PATH)

    offers = []
    if isinstance(offers_data, dict):
        for o in offers_data.get("offers", []):
            offers.append({
                "offer_id": o.get("offer_id"),
                "name": o.get("name"),
                "price_usd": o.get("price_usd"),
                "target_customer": o.get("target_customer"),
                "promise": o.get("promise"),
                "stripe_status": o.get("stripe_status"),
                "onboarding_automation_status": o.get("onboarding_automation_status"),
                "fulfillment_workflow": o.get("fulfillment_workflow"),
            })

    stripe_status = None
    if isinstance(stripe_data, dict):
        stripe_status = {
            "mode": stripe_data.get("mode"),
            "live_mode_allowed": stripe_data.get("live_mode_allowed"),
            "product_count": len(stripe_data.get("products", [])) if isinstance(stripe_data.get("products"), list) else (len(stripe_data.get("products", {})) if isinstance(stripe_data.get("products"), dict) else 0),
        }

    return {
        "status": "success",
        "product_count": len(offers),
        "offers": offers,
        "stripe": stripe_status,
        "source_type": "offer_registry",
        "freshness": "current_commit",
        "verification_complete": True,
    }


# ═══════════════════════════════════════════════════════════════
# 3. CLIENT WORKFLOW STUDY
# ═══════════════════════════════════════════════════════════════

def get_client_workflow_summary() -> Dict[str, Any]:
    """Return the intended client journey and its implementation status."""
    funnel = _safe_json_load(_REVENUE_FUNNEL_PATH)
    checklist = _safe_json_load(_ACTIVATION_CHECKLIST_PATH)

    stages = funnel.get("stages", []) if isinstance(funnel, dict) else []
    external_actions_default = (
        funnel.get("external_actions_default") if isinstance(funnel, dict) else None
    )

    journey = [
        "client onboarding",
        "credit profile",
        "credit repair/readiness",
        "business foundation",
        "business bankability",
        "funding readiness",
        "recommendations/funding opportunities",
        "review/next action",
    ]

    return {
        "status": "success",
        "funnel_stages": stages,
        "external_actions_default": external_actions_default,
        "primary_offer": funnel.get("primary_offer") if isinstance(funnel, dict) else None,
        "conceptual_client_journey": journey,
        "checklist_total_steps": len(checklist) if isinstance(checklist, list) else 0,
        "source_type": "revenue_funnel_registry",
        "freshness": "current_commit",
        "verification_complete": True,
    }


# ═══════════════════════════════════════════════════════════════
# 4. BUSINESS MODEL STUDY
# ═══════════════════════════════════════════════════════════════

def get_business_model_summary() -> Dict[str, Any]:
    """Return a governed model of how Nexus is supposed to make money."""
    artifact = _artifact_domain("business_model")
    if artifact:
        return artifact

    offers_data = _safe_json_load(_OFFER_REGISTRY_PATH)
    funnel = _safe_json_load(_REVENUE_FUNNEL_PATH)
    stripe_data = _safe_json_load(_STRIPE_PRODUCT_PATH)
    safety = _safe_json_load(_MONETIZATION_SAFETY_PATH)

    offers = []
    live_revenue_paths = []
    planned_revenue_paths = []
    if isinstance(offers_data, dict):
        for o in offers_data.get("offers", []):
            offer_id = o.get("offer_id")
            oid = offer_id or "unknown"
            stripe_status = o.get("stripe_status", "")
            price = o.get("price_usd")
            entry = {
                "offer_id": oid,
                "name": o.get("name"),
                "price_usd": price,
                "stripe_status": stripe_status,
            }
            offers.append(entry)
            if stripe_status in ("live", "test_checkout_open", "purchasable", "active"):
                live_revenue_paths.append(entry)
            else:
                planned_revenue_paths.append(entry)

    return {
        "status": "success",
        "offers": offers,
        "offers_count": len(offers),
        "operational_revenue_paths": live_revenue_paths,
        "planned_revenue_paths": planned_revenue_paths,
        "stripe_mode": stripe_data.get("mode") if isinstance(stripe_data, dict) else None,
        "stripe_live_mode_allowed": stripe_data.get("live_mode_allowed") if isinstance(stripe_data, dict) else None,
        "funnel_stage_count": len(funnel.get("stages", [])) if isinstance(funnel, dict) else 0,
        "external_actions_default": funnel.get("external_actions_default") if isinstance(funnel, dict) else None,
        "safety_policy": bool(safety),
        "verification_note": (
            "stripe_live_mode_allowed=False or offers in draft/test mode indicate "
            "payments are NOT live. Do not claim live revenue without verified evidence."
        ),
        "source_type": "revenue_registries",
        "freshness": "current_commit",
        "verification_complete": True,
    }


# ═══════════════════════════════════════════════════════════════
# 5. INTEGRATION STUDY
# ═══════════════════════════════════════════════════════════════

def get_integration_inventory() -> Dict[str, Any]:
    """Return a bounded integration inventory from the connector registry."""
    artifact = _artifact_domain("integrations")
    if artifact:
        return artifact

    connectors_data = _safe_json_load(_CONNECTOR_REGISTRY_PATH)

    connectors = []
    if isinstance(connectors_data, dict):
        for c in connectors_data.get("connectors", []):
            connectors.append({
                "connector_id": c.get("connector_id"),
                "name": c.get("name"),
                "category": c.get("category"),
                "mode": c.get("mode"),
                "status": c.get("status"),
                "live_enabled": c.get("live_enabled", False),
                "approval_required": c.get("approval_required", False),
                "configured": c.get("configured", False),
                "external_action_performed": c.get("external_action_performed", False),
                "blocked_actions": c.get("blocked_actions", [])[:5],
            })

    status_counts = {}
    mode_counts = {}
    for c in connectors:
        status_counts[c["status"]] = status_counts.get(c["status"], 0) + 1
        mode_counts[c["mode"]] = mode_counts.get(c["mode"], 0) + 1

    live_enabled = [c["connector_id"] for c in connectors if c["live_enabled"]]

    return {
        "status": "success",
        "connectors": connectors,
        "connector_count": len(connectors),
        "status_counts": status_counts,
        "mode_counts": mode_counts,
        "live_enabled_count": len(live_enabled),
        "live_enabled_connectors": live_enabled,
        "source_type": "connector_registry",
        "freshness": "current_commit",
        "verification_complete": True,
    }


# ═══════════════════════════════════════════════════════════════
# 6. SECURITY / GOVERNANCE STUDY
# ═══════════════════════════════════════════════════════════════

def get_security_boundary_summary() -> Dict[str, Any]:
    """Return a bounded read-only security/governance study."""
    from nexus_agent_platform.capabilities.shared import (
        NOVA_ALLOWED_READS, NOVA_ALLOWED_WRITES,
    )

    # RLS admin policy file present?
    rls_files = []
    migrations_dir = os.path.join(_REPO_ROOT, "supabase", "migrations")
    try:
        if os.path.isdir(migrations_dir):
            for f in sorted(os.listdir(migrations_dir)):
                if "admin_read_policies" in f or "rls" in f.lower():
                    rls_files.append(f)
    except Exception:
        pass

    # Read bounded content from the admin RLS policy file
    rls_notes = []
    for f in rls_files[:2]:
        notes = _bounded_markdown_notes(os.path.join(migrations_dir, f), max_lines=20)
        if not notes:
            # SQL file — read first lines
            try:
                with open(os.path.join(migrations_dir, f)) as fh:
                    rls_notes = [line.rstrip() for line in fh.readlines()[:20] if line.strip()]
            except Exception:
                pass
        else:
            rls_notes = notes

    # Config safety policies present?
    safety_policies = []
    configs_dir = os.path.join(_REPO_ROOT, "configs")
    try:
        if os.path.isdir(configs_dir):
            for f in sorted(os.listdir(configs_dir)):
                if "safety_policy" in f or "high_risk" in f or "data_boundary" in f:
                    safety_policies.append(f)
    except Exception:
        pass

    return {
        "status": "success",
        "nova_read_capability_count": len(NOVA_ALLOWED_READS),
        "nova_write_capability_count": len(NOVA_ALLOWED_WRITES),
        "nova_writes_frozen": NOVA_ALLOWED_WRITES == frozenset(),
        "rls_admin_policy_files": rls_files,
        "rls_policy_notes": rls_notes,
        "safety_policy_files": safety_policies,
        "security_reports_dir": "reports/security/",
        "source_type": "security_registry",
        "freshness": "current_commit",
        "verification_complete": True,
    }


# ═══════════════════════════════════════════════════════════════
# 7. REPO SYSTEM MAP
# ═══════════════════════════════════════════════════════════════

def get_repo_system_map() -> Dict[str, Any]:
    """Return a bounded repo-level system map."""
    top = []
    try:
        for entry in sorted(os.listdir(_REPO_ROOT)):
            full = os.path.join(_REPO_ROOT, entry)
            if entry.startswith("."):
                continue
            kind = "dir" if os.path.isdir(full) else "file"
            size = None
            if kind == "file":
                try:
                    size = os.path.getsize(full)
                except Exception:
                    size = None
            top.append({"name": entry, "kind": kind, "size_bytes": size})
    except Exception:
        pass

    # Entry points
    entry_points = []
    scripts_dir = os.path.join(_REPO_ROOT, "scripts")
    try:
        if os.path.isdir(scripts_dir):
            for f in sorted(os.listdir(scripts_dir)):
                if f.startswith("run_") and f.endswith(".py"):
                    entry_points.append(f)
    except Exception:
        pass

    # Repo report dirs
    report_dirs = []
    reports_dir = os.path.join(_REPO_ROOT, "reports")
    try:
        if os.path.isdir(reports_dir):
            for entry in sorted(os.listdir(reports_dir)):
                if os.path.isdir(os.path.join(reports_dir, entry)) and not entry.startswith("."):
                    report_dirs.append(entry)
    except Exception:
        pass

    return {
        "status": "success",
        "top_level": top,
        "entry_points": entry_points,
        "report_dirs": report_dirs[:50],
        "source_commit": _source_commit(),
        "source_type": "repo_scan",
        "freshness": "current_commit",
        "verification_complete": True,
    }


# ═══════════════════════════════════════════════════════════════
# 8. RECENT SYSTEM CHANGES (bounded git log)
# ═══════════════════════════════════════════════════════════════

def get_recent_system_changes(limit: int = 10) -> Dict[str, Any]:
    """Return the most recent bounded commit history for study."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-n", str(int(limit)),
             "--pretty=format:%h|%ad|%s", "--date=short"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
        changes = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("|", 2)
            changes.append({
                "sha": parts[0],
                "date": parts[1] if len(parts) > 1 else "",
                "message": parts[2] if len(parts) > 2 else "",
            })
        return {
            "status": "success",
            "recent_changes": changes,
            "source_type": "git_history",
            "freshness": "live",
            "verification_complete": True,
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "recent_changes": [],
            "source_type": "git_history",
            "freshness": "unknown",
            "verification_complete": False,
        }


# ═══════════════════════════════════════════════════════════════
# 9. SAFE REPORT INDEX
# ═══════════════════════════════════════════════════════════════

def get_safe_report_index() -> Dict[str, Any]:
    """Return a bounded, safe report index (metadata only, no content dumps)."""
    reports_dir = os.path.join(_REPO_ROOT, "reports")
    categories = []
    if os.path.isdir(reports_dir):
        for entry in os.listdir(reports_dir):
            full = os.path.join(reports_dir, entry)
            if os.path.isdir(full) and not entry.startswith("."):
                try:
                    file_count = sum(
                        1 for f in os.listdir(full)
                        if os.path.isfile(os.path.join(full, f))
                    )
                except Exception:
                    file_count = 0
                categories.append({"category": entry, "report_count": file_count})

    categories.sort(key=lambda c: c["category"])
    # Don't dump files; keep counts + latest lists per major category
    latest = []
    if os.path.isdir(reports_dir):
        try:
            for f in sorted(os.listdir(reports_dir)):
                if "_latest." in f and os.path.isfile(os.path.join(reports_dir, f)):
                    latest.append(f)
        except Exception:
            pass

    return {
        "status": "success",
        "categories": categories,
        "category_count": len(categories),
        "latest_reports": latest[:40],
        "source_type": "report_index",
        "freshness": "live",
        "verification_complete": True,
    }


# ═══════════════════════════════════════════════════════════════
# 10. GAP MODEL
# ═══════════════════════════════════════════════════════════════

def get_nexus_gap_summary() -> Dict[str, Any]:
    """Cross-source reconciliation into a structured gap model."""
    artifact = _artifact_file(_STUDY_GAPS_PATH, "reports/nova_study/nexus_gaps.json")
    if artifact:
        return artifact

    from nexus_agent_platform.capabilities.nexus_knowledge import (
        _load_normalized_processes, TOOL_REGISTRY,
    )
    from nexus_agent_platform.runtime.execution_telemetry import query_runtime_telemetry

    processes, _ = _load_normalized_processes()
    gaps = []
    gap_id = 0

    # Process-level gaps
    for p in processes:
        pid = p["process_id"]
        name = p["name"]
        cs = p["configuration_state"]
        em = p["execution_mode"]
        rs = p["runtime_state"]

        if cs == "disabled":
            gap_id += 1
            gaps.append({
                "gap_id": f"NEXUS-G{gap_id:02d}",
                "domain": "processes",
                "title": f"Process disabled: {name}",
                "description": f"{name} is configured disabled.",
                "evidence": f"process:{pid} configuration_state=disabled",
                "severity": "medium",
                "confidence": "high",
                "source": "process_registry",
                "recommended_next_step": "Confirm whether it should be enabled or retired.",
            })
        elif cs == "enabled" and rs in ("simulated", "skipped", "never_run", "unknown", "blocked"):
            gap_id += 1
            gaps.append({
                "gap_id": f"NEXUS-G{gap_id:02d}",
                "domain": "processes",
                "title": f"Enabled but not verified running: {name}",
                "description": (
                    f"{name} is enabled (config) but runtime state is '{rs}' "
                    f"and execution mode is '{em}'."
                ),
                "evidence": f"process:{pid} configuration_state=enabled runtime_state={rs}",
                "severity": "high" if rs == "blocked" else "medium",
                "confidence": "high" if em != "ACTIVE_INTERNAL" else "medium",
                "source": "cross_source:process_registry",
                "recommended_next_step": "Verify the process runs in production environment.",
            })

    # Tool gaps
    for tool in TOOL_REGISTRY.get("unavailable", []):
        gap_id += 1
        gaps.append({
            "gap_id": f"NEXUS-G{gap_id:02d}",
            "domain": "tools",
            "title": f"Tool unavailable: {tool}",
            "description": f"{tool} listed in the tool registry as unavailable.",
            "evidence": "tool_registry.unavailable",
            "severity": "low",
            "confidence": "high",
            "source": "tool_registry",
            "recommended_next_step": "Assess whether {tool} is needed.",
        })

    # Integration gaps from connector registry
    connectors_data = _safe_json_load(_CONNECTOR_REGISTRY_PATH)
    if isinstance(connectors_data, dict):
        for c in connectors_data.get("connectors", []):
            if c.get("status") in ("blocked", "connector_missing", "unconfigured"):
                gap_id += 1
                gaps.append({
                    "gap_id": f"NEXUS-G{gap_id:02d}",
                    "domain": "integrations",
                    "title": f"Integration {c.get('status')}: {c.get('name', c.get('connector_id'))}",
                    "description": f"{c.get('name')} is not live (status={c.get('status')}, mode={c.get('mode')}).",
                    "evidence": f"connector:{c.get('connector_id')} status={c.get('status')}",
                    "severity": "medium" if c.get("live_enabled") is False else "low",
                    "confidence": "high",
                    "source": "connector_registry",
                    "recommended_next_step": c.get("next_setup_step", "Review integration setup.")[:200],
                })

    # Telemetry gap
    try:
        telemetry = query_runtime_telemetry(operation="overview")
        telemetry_count = (
            telemetry.get("summary", {}).get("event_count", 0)
            if isinstance(telemetry, dict) else 0
        )
        if telemetry_count == 0:
            gap_id += 1
            gaps.append({
                "gap_id": f"NEXUS-G{gap_id:02d}",
                "domain": "runtime",
                "title": "No verified execution telemetry events",
                "description": "Execution telemetry store is empty; no verified runtime proof.",
                "evidence": "execution_telemetry event_count=0",
                "severity": "high",
                "confidence": "high",
                "source": "execution_telemetry",
                "recommended_next_step": "Instrument and run a real process through telemetry.",
            })
    except Exception:
        pass

    return {
        "status": "success",
        "gap_count": len(gaps),
        "gaps": gaps,
        "gap_id_count": gap_id,
        "source_type": "cross_source_reconciliation",
        "freshness": "current_registry",
        "verification_complete": True,
    }


def get_nexus_unknowns() -> Dict[str, Any]:
    """Return structured unknowns — areas with insufficient evidence."""
    artifact = _artifact_file(_STUDY_UNKNOWNS_PATH, "reports/nova_study/nexus_unknowns.json")
    if artifact:
        return artifact

    unknowns = [
        {
            "unknown_id": "NEXUS-U01",
            "domain": "runtime",
            "title": "Which processes have verified real execution?",
            "evidence_status": "insufficient",
            "recommended_step": "Enable execution telemetry and observe a real run.",
        },
        {
            "unknown_id": "NEXUS-U02",
            "domain": "business",
            "title": "What is the actual current revenue position?",
            "evidence_status": "insufficient",
            "recommended_step": "Confirm Stripe production checkout is authorized.",
        },
        {
            "unknown_id": "NEXUS-U03",
            "domain": "product",
            "title": "Which client workflows are backend-supported end-to-end?",
            "evidence_status": "insufficient",
            "recommended_step": "Trace each workflow from intake to delivery.",
        },
    ]
    return {
        "status": "success",
        "unknown_count": len(unknowns),
        "unknowns": unknowns,
        "source_type": "cross_source_unknowns",
        "freshness": "current_commit",
        "verification_complete": True,
    }


# ═══════════════════════════════════════════════════════════════
# 11. STUDY SNAPSHOT — one bounded composite
# ═══════════════════════════════════════════════════════════════

_STUDY_DOMAIN_READERS = {
    "system_architecture": get_architecture_summary,
    "agents": get_agent_inventory,
    "tools": get_tool_inventory,
    "processes": get_process_inventory,
    "runtime": get_runtime_execution_summary,
    "product": get_product_inventory,
    "client_workflow": get_client_workflow_summary,
    "business_model": get_business_model_summary,
    "integrations": get_integration_inventory,
    "security": get_security_boundary_summary,
    "gaps": get_nexus_gap_summary,
    "unknowns": get_nexus_unknowns,
}


def get_nexus_study_snapshot() -> Dict[str, Any]:
    """Assemble a bounded study snapshot across all study domains."""
    artifact = _artifact_snapshot()
    if artifact:
        return _with_current_runtime_reconciliation(artifact)

    from nexus_agent_platform.capabilities.nexus_knowledge import get_nexus_overview

    overview = get_nexus_overview()
    domains = {}
    errors = {}
    for domain_name, reader in _STUDY_DOMAIN_READERS.items():
        try:
            domains[domain_name] = reader()
        except Exception as exc:
            errors[domain_name] = str(exc)
            domains[domain_name] = {"status": "error", "error": str(exc)}

    return {
        "status": "success",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _source_commit(),
        "system": {
            "name": overview.get("system_name"),
            "purpose": overview.get("purpose"),
            "agent_count": overview.get("agent_count"),
            "process_count": overview.get("process_count"),
            "enabled_processes": overview.get("enabled_processes"),
        },
        "domains": domains,
        "errors": errors,
        "source_coverage": {
            domain: bool(d.get("verification_complete", False))
            for domain, d in domains.items()
        },
        "verification_complete": True,
    }
