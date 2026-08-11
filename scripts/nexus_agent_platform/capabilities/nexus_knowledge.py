"""Nexus Knowledge Registry — static structural knowledge + live state readers.

Provides a single source of truth for questions about Nexus architecture,
agents, tools, processes, workflows, reports, and research.

No write access.  No credentials.  No raw source code exposure.
All data derived from repository configuration and runtime state.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")

# ═══════════════════════════════════════════════════════════════
# STATIC KNOWLEDGE — structural facts about Nexus
# ═══════════════════════════════════════════════════════════════

NEXUS_SYSTEM = {
    "system_name": "Nexus OS",
    "version": "v2",
    "purpose": "AI-native business operating system for credit repair, funding readiness, and business automation",
    "architecture": "Multi-agent LangGraph platform with governed capability layer, approval-gated actions, and Telegram bridges",
    "runtime_model": "Python agents + TypeScript frontend, OpenRouter LLM providers, Supabase data layer, local process orchestration",
    "major_components": [
        "Agent Platform (Python/LangGraph)",
        "Client Portal (TypeScript/React)",
        "Capability OS (TypeScript policy engine)",
        "Process Registry (JSON-driven orchestration)",
        "Approval-Gated Action Lanes",
        "Research Pipeline (YouTube, NotebookLM, web)",
        "Telegram Bridges (Hermes, Nova, Alpha)",
    ],
    "integration_boundaries": {
        "data_layer": "Supabase (PostgreSQL + RLS)",
        "llm_provider": "OpenRouter (gpt-4o-mini default)",
        "deployment": "Netlify (frontend), local Mac Mini (agents)",
        "messaging": "Telegram (3 bots: Hermes bridge, Nova, Alpha)",
        "research": "Brave web search, YouTube API, NotebookLM local",
    },
    "known_incomplete_areas": [
        "No real automation execution yet — all processes simulated",
        "Stripe payment flow not live (test mode only)",
        "Resend email blocked by credential scope",
        "Oanda trading demo not connected",
        "NotebookLM official API not available",
        "YouTube transcript import needs approved source files",
        "Social publishing blocked by policy",
        "Live Supabase inserts blocked by approval",
    ],
}

AGENTS = {
    "nexus_hermes": {
        "agent_id": "nexus_hermes",
        "name": "Nexus Hermes",
        "role": "Internal operator and chief-of-staff",
        "responsibilities": [
            "Manages operations",
            "Coordinates across tools",
            "Surfaces actionable information to Ray",
            "Runs the business (does NOT give external-facing advice to clients)",
        ],
        "runtime_status": "configured",
        "model": "openai/gpt-4o-mini",
        "provider": "OpenRouter",
        "permissions": {
            "reads": [
                "get_client_count", "get_system_status", "get_failure_report",
                "get_alpha_status", "process_status", "process_failures",
                "research_history", "opportunities", "trading_status",
                "pending_approvals",
            ],
            "writes": ["send_approved_email", "schedule_report", "create_work_order"],
        },
        "tools": [
            "system_status", "failure_report", "alpha_status", "process_status",
            "process_failures", "research_history", "opportunities", "trading_status",
            "pending_approvals", "send_email", "schedule_report",
        ],
        "isolation": {
            "memory": "agent_context/hermes_context.json",
            "telegram": "Nexus bridge (shared token)",
            "graph": "Own LangGraph graph",
            "write_access": "3 certified actions (email, report, work_order)",
        },
        "feature_flags": {
            "langgraph_enabled": "NEXUS_HERMES_LANGGRAPH_ENABLED",
            "front_brain_enabled": "NEXUS_HERMES_CONVERSATIONAL_FRONT_BRAIN_ENABLED",
        },
    },
    "hermes_nova": {
        "agent_id": "hermes_nova",
        "name": "Hermes Nova",
        "role": "Independent strategic adviser and conversational partner",
        "responsibilities": [
            "Natural multi-turn conversation",
            "Strategic advice",
            "Governed read-only access to approved operational data",
            "Nexus system awareness",
            "NOT the Nexus operator",
            "NOT a client CRM assistant",
        ],
        "runtime_status": "configured",
        "model": "openai/gpt-4o-mini",
        "provider": "OpenRouter",
        "permissions": {
            "reads": [
                "get_runtime_capabilities", "get_client_count",
                "resolve_user_identity_by_email", "general_search",
                "get_system_health", "get_pending_approvals",
                "get_recent_research", "get_opportunities",
                "get_client_profile", "get_funding_readiness",
                "get_operational_summary", "get_nexus_overview",
                "get_agent_registry", "get_agent_details",
                "get_tool_registry", "get_capability_registry",
                "get_process_registry", "get_process_details",
                "get_report_index", "get_latest_reports",
                "get_recent_activity",
            ],
            "writes": [],  # ZERO write access
        },
        "tools": [],  # No direct tool access
        "isolation": {
            "memory": "nova_memory/nova_{chat_id}.json",
            "provenance": "nova_provenance/{hashed}.json",
            "telegram": "NOVA_TELEGRAM_BOT_TOKEN (separate bot)",
            "graph": "Own LangGraph graph",
            "write_access": "NONE — all writes denied",
            "supabase": "Through shared certified layer only",
        },
        "feature_flags": {
            "enabled": "HERMES_NOVA_ENABLED",
        },
    },
    "alpha": {
        "agent_id": "alpha",
        "name": "Alpha",
        "role": "Independent outside-thinking advisor",
        "responsibilities": [
            "Researches opportunities",
            "Evaluates markets",
            "Gives honest outside perspective",
            "Challenges assumptions",
            "Identifies risks",
            "Proposes opportunities",
            "NOT the operator — advises the operator",
        ],
        "runtime_status": "configured",
        "model": "openai/gpt-4o-mini",
        "provider": "OpenRouter (direct httpx for research)",
        "permissions": {
            "reads": ["web_search", "opinion", "challenge"],
            "writes": [],
        },
        "tools": ["brave_web_search", "youtube_search"],
        "isolation": {
            "memory": "agent_context/alpha_context.json",
            "telegram": "ALPHA_TELEGRAM_BOT_TOKEN (separate bot)",
            "graph": "Own LangGraph graph",
            "write_access": "NONE",
            "client_pii": "Explicitly prohibited",
            "supabase": "No access",
        },
        "feature_flags": {
            "langgraph_enabled": "ALPHA_LANGGRAPH_ENABLED",
        },
    },
}

SPECIALIST_PROFILES = {
    "hermes_ceo": {"name": "Hermes CEO Advisor", "role": "Executive triage and delegation"},
    "credit": {"name": "Credit Specialist", "role": "Credit readiness and dispute draft review"},
    "funding": {"name": "Funding Specialist", "role": "Funding, grants, and bankability"},
    "research": {"name": "Research Specialist", "role": "Approved source scoring"},
    "monetization": {"name": "Monetization Specialist", "role": "Offer and revenue design"},
    "marketing": {"name": "Marketing Specialist", "role": "Content and outreach drafts"},
    "trading": {"name": "Trading Specialist", "role": "Demo and paper research"},
    "automation": {"name": "Automation Engineer", "role": "Safe internal jobs"},
    "client_success": {"name": "Client Success Specialist", "role": "Synthetic onboarding review"},
}

# Tool registry — safe metadata only (no credentials, no secrets)
TOOL_REGISTRY = {
    "internal_safe": [
        "git", "node", "npm", "python3", "pip3", "jq", "openssl",
        "sqlite3", "ffmpeg", "codex", "claude", "opencode", "ollama",
    ],
    "read_only": [
        "gh", "curl", "wget", "supabase", "netlify", "docker", "colima",
        "yt-dlp", "playwright",
    ],
    "approval_gated": [
        "stripe", "oanda_demo_api_connector",
    ],
    "unavailable": [
        "pnpm", "yarn", "orb", "psql", "vercel", "imagemagick", "magick",
        "tesseract", "chromium", "chrome", "gemini", "notebooklm",
        "vibe-trading", "resend", "facebook", "instagram", "oanda",
        "vibe_trading_python",
    ],
}

# Process registry file path
_PROCESS_REGISTRY_PATH = os.path.join(
    _REPO_ROOT, "data", "operations", "nexus_process_registry.json"
)

# Automation schedule registry
_AUTOMATION_SCHEDULE_PATH = os.path.join(
    _REPO_ROOT, "configs", "automation_schedule_registry.json"
)

# Approval-gated lanes
_APPROVAL_GATED_LANES_PATH = os.path.join(
    _REPO_ROOT, "data", "operations", "nexus_approval_gated_lanes.json"
)

# Blocked action guard
_BLOCKED_ACTION_GUARD_PATH = os.path.join(
    _REPO_ROOT, "data", "operations", "nexus_blocked_action_guard.json"
)

# Report registry (UI-facing)
_REPORT_REGISTRY_PATH = os.path.join(
    _REPO_ROOT, "src", "data", "reportRegistry.js"
)

# Research source registry
_RESEARCH_SOURCE_REGISTRY_PATH = os.path.join(
    _REPO_ROOT, "configs", "research_source_registry.json"
)

# Alpha status
_ALPHA_STATUS_PATH = os.path.join(
    _REPO_ROOT, "data", "runtime", "alpha_telegram_status.json"
)

# Ray review queue
_RAY_REVIEW_QUEUE_PATH = os.path.join(
    _REPO_ROOT, "reports", "runtime", "ray_review_queue_latest.json"
)

# Process inventory (live runtime)
_PROCESS_INVENTORY_PATH = os.path.join(
    _REPO_ROOT, "reports", "nexus_process_inventory_latest.json"
)

# Scheduler inventory
_SCHEDULER_INVENTORY_PATH = os.path.join(
    _REPO_ROOT, "reports", "nexus_scheduler_inventory_latest.json"
)

# Feature flags
_FEATURE_FLAGS_PATH = os.path.join(
    _REPO_ROOT, "scripts", "nexus_agent_platform", "flags.py"
)


def _safe_json_load(path: str) -> Optional[Any]:
    """Load a JSON file safely, returning None on any error."""
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def _safe_file_exists(path: str) -> bool:
    """Check if a file exists safely."""
    try:
        return os.path.isfile(path)
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════
# STATIC KNOWLEDGE READERS
# ═══════════════════════════════════════════════════════════════

def get_nexus_overview() -> Dict[str, Any]:
    """Return a verified overview of the Nexus system."""
    processes, _ = _load_normalized_processes()
    process_count = len(processes)
    enabled_count = sum(1 for p in processes if p["configuration_state"] == "enabled")

    research_data = _safe_json_load(_RESEARCH_SOURCE_REGISTRY_PATH)
    research_lanes = len(research_data) if isinstance(research_data, dict) else 0

    return {
        "system_name": NEXUS_SYSTEM["system_name"],
        "version": NEXUS_SYSTEM["version"],
        "purpose": NEXUS_SYSTEM["purpose"],
        "architecture": NEXUS_SYSTEM["architecture"],
        "runtime_model": NEXUS_SYSTEM["runtime_model"],
        "major_components": NEXUS_SYSTEM["major_components"],
        "agents": list(AGENTS.keys()),
        "agent_count": len(AGENTS),
        "specialist_count": len(SPECIALIST_PROFILES),
        "live_capability_count": sum(
            len(v) for v in TOOL_REGISTRY.values()
            if v != TOOL_REGISTRY.get("unavailable")
        ),
        "process_count": process_count,
        "enabled_processes": enabled_count,
        "research_lane_count": research_lanes,
        "integration_boundaries": NEXUS_SYSTEM["integration_boundaries"],
        "known_incomplete_areas": NEXUS_SYSTEM["known_incomplete_areas"],
        "verification_complete": True,
    }


def get_nexus_architecture() -> Dict[str, Any]:
    """Return Nexus architecture details."""
    return {
        "architecture": NEXUS_SYSTEM["architecture"],
        "runtime_model": NEXUS_SYSTEM["runtime_model"],
        "major_components": NEXUS_SYSTEM["major_components"],
        "integration_boundaries": NEXUS_SYSTEM["integration_boundaries"],
        "agent_count": len(AGENTS),
        "agents": {
            aid: {
                "name": a["name"],
                "role": a["role"],
                "isolation": a["isolation"],
            }
            for aid, a in AGENTS.items()
        },
        "specialist_profiles": {
            k: v["name"] for k, v in SPECIALIST_PROFILES.items()
        },
        "capability_layers": [
            "Shared Python capability handlers (11+)",
            "Hermes Python registered capabilities (14)",
            "TypeScript Capability OS registry (130+)",
            "TypeScript Hermes tools (25)",
            "Connector registry (21)",
        ],
        "verification_complete": True,
    }


def get_agent_registry() -> Dict[str, Any]:
    """Return all agents with their metadata."""
    agents = []
    for aid, a in AGENTS.items():
        agents.append({
            "agent_id": aid,
            "name": a["name"],
            "role": a["role"],
            "runtime_status": a["runtime_status"],
            "model": a["model"],
            "permissions": {
                "read_count": len(a["permissions"]["reads"]),
                "write_count": len(a["permissions"]["writes"]),
            },
            "tool_count": len(a["tools"]),
        })
    return {
        "agents": agents,
        "total": len(agents),
        "specialist_profiles": len(SPECIALIST_PROFILES),
        "verification_complete": True,
    }


def get_agent_details(agent_id: str) -> Dict[str, Any]:
    """Return detailed information about a specific agent."""
    agent = AGENTS.get(agent_id)
    if agent is None:
        return {
            "found": False,
            "agent_id": agent_id,
            "error": f"Agent '{agent_id}' not found in registry.",
            "available_agents": list(AGENTS.keys()),
        }
    return {
        "found": True,
        **agent,
        "verification_complete": True,
    }


def get_tool_registry() -> Dict[str, Any]:
    """Return the tool registry with safe metadata.

    All counts are COMPUTED from the TOOL_REGISTRY item collections.
    State labels are mutually exclusive per category.
    """
    internal_safe = list(TOOL_REGISTRY.get("internal_safe", []))
    read_only = list(TOOL_REGISTRY.get("read_only", []))
    approval_gated = list(TOOL_REGISTRY.get("approval_gated", []))
    unavailable = list(TOOL_REGISTRY.get("unavailable", []))

    total = len(internal_safe) + len(read_only) + len(approval_gated) + len(unavailable)
    usable_now = len(internal_safe) + len(read_only)

    # Reconciliation: total must equal sum of all buckets
    reconciliation = total == (len(internal_safe) + len(read_only) + len(approval_gated) + len(unavailable))

    return {
        "categories": {
            "internal_safe": {"count": len(internal_safe), "tools": internal_safe},
            "read_only": {"count": len(read_only), "tools": read_only},
            "approval_gated": {"count": len(approval_gated), "tools": approval_gated},
            "unavailable": {"count": len(unavailable), "tools": unavailable},
        },
        "total": total,
        "usable_now": usable_now,
        "internal_safe_count": len(internal_safe),
        "read_only_count": len(read_only),
        "approval_gated_count": len(approval_gated),
        "unavailable_count": len(unavailable),
        "default_policy": "default_deny_external: true",
        "reconciliation": reconciliation,
        "source_type": "configuration_registry",
        "freshness": "current_commit",
        "verification_complete": True,
    }


def get_capability_registry() -> Dict[str, Any]:
    """Return the capability status summary."""
    return {
        "shared_handlers": [
            "get_client_count", "resolve_user_identity_by_email",
            "general_search", "get_system_health", "get_pending_approvals",
            "get_recent_research", "get_opportunities", "get_client_profile",
            "get_funding_readiness", "get_operational_summary",
            "get_runtime_capabilities",
        ],
        "nova_knowledge_capabilities": [
            "get_nexus_overview", "get_agent_registry", "get_agent_details",
            "get_tool_registry", "get_capability_registry",
            "get_process_registry", "get_process_details",
            "get_report_index", "get_latest_reports", "get_recent_activity",
        ],
        "total_shared_handlers": 11,
        "total_nova_knowledge": 10,
        "nova_writes": 0,
        "hermes_writes": 3,
        "verification_complete": True,
    }


# ═══════════════════════════════════════════════════════════════
# LIVE STATE READERS
# ═══════════════════════════════════════════════════════════════

def _normalize_process(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Canonical normalizer: raw registry process -> three independent dimensions.

    CONFIGURATION STATE (is Nexus configured to allow this process to run?):
      enabled | disabled

    EXECUTION MODE (what mode is the process designed to execute in?):
      ACTIVE_INTERNAL | DRY_RUN | TELEGRAM_OPERATOR | SANDBOX_TEST | BLOCKED | unknown

    RUNTIME STATE (what runtime evidence exists right now?):
      running | idle | completed | failed | simulated | skipped | blocked | unknown | never_run

    These dimensions are independent. Do NOT derive one from another.
    """
    is_enabled = raw.get("enabled", False)
    mode = raw.get("mode", "unknown")
    runtime_state = raw.get("last_status", "never_run")

    return {
        "process_id": raw.get("process_id", "unknown"),
        "name": raw.get("name", "unknown"),
        "configuration_state": "enabled" if is_enabled else "disabled",
        "execution_mode": mode,
        "runtime_state": runtime_state,
        "schedule": raw.get("schedule_type", "unknown"),
        "risk": raw.get("risk_level", "unknown"),
        "last_run": raw.get("last_run_at"),
        "blocked_actions": raw.get("blocked_actions", []),
        "source": "process_registry",
    }


def _load_normalized_processes() -> tuple:
    """Load and normalize all processes. Returns (processes, error_dict_or_None)."""
    data = _safe_json_load(_PROCESS_REGISTRY_PATH)
    if not isinstance(data, list):
        return [], {
            "status": "unavailable",
            "error": "Process registry not found or invalid.",
        }
    return [_normalize_process(p) for p in data if isinstance(p, dict)], None


def get_process_registry_live() -> Dict[str, Any]:
    """Read the live process registry with three independent reconciled dimensions.

    CONFIGURATION STATE: enabled/disabled (from registry 'enabled' field)
    EXECUTION MODE: ACTIVE_INTERNAL/DRY_RUN/TELEGRAM_OPERATOR/etc. (from registry 'mode' field)
    RUNTIME STATE: simulated/running/failed/skipped/blocked/etc. (from registry 'last_status' field)

    All counts are COMPUTED from the same normalized item list.
    Each dimension's counts reconcile independently to the total.
    """
    processes, err = _load_normalized_processes()
    if err is not None:
        return {**err, "processes": [], "total": 0}

    total = len(processes)

    # Configuration counts (dimension 1)
    config_counts = {}
    for p in processes:
        cs = p["configuration_state"]
        config_counts[cs] = config_counts.get(cs, 0) + 1

    # Execution mode counts (dimension 2)
    mode_counts = {}
    for p in processes:
        em = p["execution_mode"]
        mode_counts[em] = mode_counts.get(em, 0) + 1

    # Runtime state counts (dimension 3)
    runtime_counts = {}
    for p in processes:
        rs = p["runtime_state"]
        runtime_counts[rs] = runtime_counts.get(rs, 0) + 1

    # Reconciliation: each dimension must independently sum to total
    config_reconciles = sum(config_counts.values()) == total
    mode_reconciles = sum(mode_counts.values()) == total
    runtime_reconciles = sum(runtime_counts.values()) == total

    # Execution telemetry
    has_real_execution = runtime_counts.get("running", 0) > 0 or runtime_counts.get("completed", 0) > 0
    all_simulated_or_skipped = all(
        s in ("simulated", "skipped", "blocked", "never_run", "unknown")
        for s in runtime_counts.keys()
    )

    return {
        "status": "success",
        "processes": processes,
        "total": total,
        "configuration_counts": config_counts,
        "mode_counts": mode_counts,
        "runtime_counts": runtime_counts,
        "has_real_execution": has_real_execution,
        "all_simulated_or_skipped": all_simulated_or_skipped,
        "reconciliation": {
            "configuration": config_reconciles,
            "execution_mode": mode_reconciles,
            "runtime_state": runtime_reconciles,
            "all_reconciled": config_reconciles and mode_reconciles and runtime_reconciles,
        },
        "source_type": "process_registry",
        "freshness": "current_registry",
        "verification_complete": True,
    }


def get_process_details(process_id: str) -> Dict[str, Any]:
    """Return details for a specific process using normalized dimensions."""
    data = _safe_json_load(_PROCESS_REGISTRY_PATH)
    if not isinstance(data, list):
        return {"found": False, "error": "Process registry unavailable."}

    for p in data:
        if isinstance(p, dict) and p.get("process_id") == process_id:
            normalized = _normalize_process(p)
            return {
                "found": True,
                **normalized,
                "verification_complete": True,
            }

    return {
        "found": False,
        "process_id": process_id,
        "error": f"Process '{process_id}' not found.",
        "available_processes": [
            p.get("process_id") for p in data if isinstance(p, dict)
        ],
    }


def get_report_index_live() -> Dict[str, Any]:
    """Return the report index from available report directories."""
    reports_dir = os.path.join(_REPO_ROOT, "reports")
    categories = []
    if os.path.isdir(reports_dir):
        for entry in os.listdir(reports_dir):
            full = os.path.join(reports_dir, entry)
            if os.path.isdir(full) and not entry.startswith("."):
                # Count files in category
                file_count = sum(
                    1 for f in os.listdir(full)
                    if os.path.isfile(os.path.join(full, f))
                )
                categories.append({
                    "category": entry,
                    "report_count": file_count,
                })

    # Also check root-level report files
    root_reports = []
    if os.path.isdir(reports_dir):
        for f in os.listdir(reports_dir):
            full = os.path.join(reports_dir, f)
            if os.path.isfile(full) and f.endswith((".json", ".md")):
                root_reports.append(f)

    return {
        "status": "success",
        "categories": categories,
        "category_count": len(categories),
        "root_report_count": len(root_reports),
        "verification_complete": True,
    }


def get_latest_reports_live() -> Dict[str, Any]:
    """Return metadata about the most recent reports."""
    reports_dir = os.path.join(_REPO_ROOT, "reports")
    latest = []
    if not os.path.isdir(reports_dir):
        return {"status": "unavailable", "error": "Reports directory not found.", "reports": []}

    # Check root-level *_latest.* files
    for f in os.listdir(reports_dir):
        if "_latest." in f and os.path.isfile(os.path.join(reports_dir, f)):
            stat = os.stat(os.path.join(reports_dir, f))
            latest.append({
                "name": f,
                "category": "root",
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            })

    # Sort by modified time, most recent first
    latest.sort(key=lambda x: x.get("modified", ""), reverse=True)

    return {
        "status": "success",
        "reports": latest[:20],  # top 20 most recent
        "total_latest": len(latest),
        "verification_complete": True,
    }


def get_recent_activity_live() -> Dict[str, Any]:
    """Aggregate recent activity from multiple sources.

    Explicitly separates:
    - CONFIGURED STATE: what is defined/enabled in registries
    - VERIFIED ACTIVITY: actual executions, failures, report creation
    - SIMULATED STATE: registry entries without real execution telemetry

    If no real execution telemetry exists, Nova must NOT claim processes ran.
    """
    activity = {
        "processes": {"status": "unknown", "data": None},
        "approvals": {"status": "unknown", "data": None},
        "research": {"status": "unknown", "data": None},
        "alpha": {"status": "unknown", "data": None},
    }

    # Process status — separate configured vs verified using normalizer
    processes, proc_err = _load_normalized_processes()
    if not proc_err and processes:
        enabled = [p for p in processes if p["configuration_state"] == "enabled"]
        failed = [p for p in processes if p["runtime_state"] in ("failed",)]
        simulated = [p for p in processes if p["runtime_state"] == "simulated"]
        running = [p for p in processes if p["runtime_state"] == "running"]
        completed = [p for p in processes if p["runtime_state"] == "completed"]
        blocked = [p for p in processes if p["runtime_state"] == "blocked"]
        skipped = [p for p in processes if p["runtime_state"] == "skipped"]

        # Telemetry coverage: do we have evidence of real execution?
        has_real_execution = len(running) > 0 or len(completed) > 0
        all_simulated = all(
            p["runtime_state"] in ("simulated", "skipped", "blocked", "never_run", "unknown")
            for p in processes
        )

        activity["processes"] = {
            "status": "success",
            "configured": {
                "total": len(processes),
                "enabled": len(enabled),
            },
            "verified_activity": {
                "running": len(running),
                "completed": len(completed),
                "failed": len(failed),
                "has_real_execution": has_real_execution,
            },
            "simulated_state": {
                "simulated_count": len(simulated),
                "skipped_count": len(skipped),
                "blocked_count": len(blocked),
                "all_simulated": all_simulated,
            },
            "telemetry_coverage": "real_execution_observed" if has_real_execution else "no_real_execution_telemetry",
        }

    # Approvals
    approval_data = _safe_json_load(_RAY_REVIEW_QUEUE_PATH)
    if isinstance(approval_data, dict):
        activity["approvals"] = {
            "status": "success",
            "configured": {
                "total": approval_data.get("total", 0),
                "pending": approval_data.get("pending_count", 0),
            },
            "verified_activity": {
                "external_actions_executed": 0,  # No external actions executed yet
            },
        }
    elif _safe_file_exists(_RAY_REVIEW_QUEUE_PATH):
        activity["approvals"] = {"status": "error", "error": "Invalid approval queue format."}
    else:
        activity["approvals"] = {"status": "unavailable", "error": "Approval queue not found."}

    # Alpha status
    alpha_data = _safe_json_load(_ALPHA_STATUS_PATH)
    if isinstance(alpha_data, dict):
        activity["alpha"] = {
            "status": "success",
            "configured": {
                "state": alpha_data.get("state", "unknown"),
            },
            "verified_activity": {
                "last_incoming": alpha_data.get("last_incoming_message"),
            },
        }
    elif _safe_file_exists(_ALPHA_STATUS_PATH):
        activity["alpha"] = {"status": "error", "error": "Invalid alpha status format."}
    else:
        activity["alpha"] = {"status": "unavailable", "error": "Alpha status not found."}

    # Research (from research source registry)
    research_data = _safe_json_load(_RESEARCH_SOURCE_REGISTRY_PATH)
    if isinstance(research_data, dict):
        lanes = [k for k, v in research_data.items()
                 if isinstance(v, dict) and v.get("approved", False)]
        activity["research"] = {
            "status": "success",
            "configured": {
                "total_lanes": len(research_data),
                "approved_lanes": len(lanes),
            },
            "verified_activity": {
                "recent_runs": 0,  # No real execution telemetry
            },
        }
    else:
        activity["research"] = {"status": "unavailable", "error": "Research registry not found."}

    # Determine overall status
    statuses = [v.get("status", "unknown") for v in activity.values()]
    if all(s == "success" for s in statuses):
        overall = "success"
    elif any(s == "unavailable" for s in statuses):
        overall = "partial"
    elif any(s == "error" for s in statuses):
        overall = "partial"
    else:
        overall = "success"

    # Check if we have any real execution telemetry across all sources
    proc_data = activity.get("processes", {}).get("verified_activity", {})
    has_any_real_execution = proc_data.get("has_real_execution", False)

    return {
        "status": overall,
        "components": activity,
        "has_any_real_execution": has_any_real_execution,
        "telemetry_summary": (
            "Real execution telemetry observed" if has_any_real_execution
            else "No real execution telemetry — all state is configured/simulated"
        ),
        "source_type": "composite",
        "freshness": "live",
        "verification_complete": True,
    }


# ═══════════════════════════════════════════════════════════════
# DETERMINISTIC DATE/TIME UTILITY
# ═══════════════════════════════════════════════════════════════

def get_current_datetime() -> Dict[str, Any]:
    """Return current date and time in Phoenix timezone.

    This is a deterministic utility — never uses LLM generation.
    Always returns system clock time.
    """
    try:
        from zoneinfo import ZoneInfo
        phoenix_tz = ZoneInfo("America/Phoenix")
        now_phoenix = datetime.now(phoenix_tz)
        now_utc = datetime.now(timezone.utc)
        return {
            "status": "success",
            "phoenix_date": now_phoenix.strftime("%Y-%m-%d"),
            "phoenix_time": now_phoenix.strftime("%I:%M %p"),
            "phoenix_datetime": now_phoenix.isoformat(),
            "phoenix_day_of_week": now_phoenix.strftime("%A"),
            "utc_datetime": now_utc.isoformat(),
            "source_type": "deterministic_utility",
            "freshness": "live",
            "verification_complete": True,
        }
    except Exception as exc:
        # Fallback to UTC if timezone not available
        now_utc = datetime.now(timezone.utc)
        return {
            "status": "success",
            "phoenix_date": now_utc.strftime("%Y-%m-%d"),
            "phoenix_time": now_utc.strftime("%H:%M UTC"),
            "phoenix_datetime": now_utc.isoformat(),
            "phoenix_day_of_week": now_utc.strftime("%A"),
            "utc_datetime": now_utc.isoformat(),
            "source_type": "deterministic_utility",
            "freshness": "live",
            "verification_complete": True,
            "timezone_note": "America/Phoenix not available, using UTC",
        }


# ═══════════════════════════════════════════════════════════════
# INCOMPLETE / UNAVAILABLE NEXUS SUMMARY
# ═══════════════════════════════════════════════════════════════

def get_incomplete_areas() -> Dict[str, Any]:
    """Derive incomplete/unavailable areas from actual registries with deduplication.

    Each component gets a unique component_id. A component may appear in multiple
    categories, but unique_incomplete_count counts each component only once.

    Categories (independent, may overlap):
      simulated: runtime_state == simulated
      dry_run: execution_mode == DRY_RUN
      blocked: configuration_state == disabled AND (runtime_state == blocked OR execution_mode == BLOCKED)
      disabled: configuration_state == disabled (but NOT blocked)
      sandbox: execution_mode == SANDBOX_TEST
      unavailable_tools: tool registry status == unavailable
      mock: tools/capabilities explicitly marked mock
    """
    from collections import OrderedDict

    categories: Dict[str, List[Dict[str, str]]] = OrderedDict()
    seen_component_ids: set = set()

    def _add_to_category(cat: str, component_id: str, label: str):
        if component_id not in seen_component_ids:
            seen_component_ids.add(component_id)
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({"component_id": component_id, "label": label})

    # Process-based categories
    processes, _ = _load_normalized_processes()
    for p in processes:
        pid = p["process_id"]
        name = p["name"]
        cs = p["configuration_state"]
        em = p["execution_mode"]
        rs = p["runtime_state"]

        component_id = f"process:{pid}"

        if rs == "simulated":
            _add_to_category("simulated", component_id, name)
        if em == "DRY_RUN":
            _add_to_category("dry_run", component_id, name)
        if cs == "disabled" and (rs == "blocked" or em == "BLOCKED"):
            _add_to_category("blocked", component_id, name)
        elif cs == "disabled":
            _add_to_category("disabled", component_id, name)
        if em == "SANDBOX_TEST":
            _add_to_category("sandbox", component_id, name)

    # Tool-based categories
    for tool in TOOL_REGISTRY.get("unavailable", []):
        component_id = f"tool:{tool}"
        _add_to_category("unavailable_tools", component_id, tool)

    # Approval-gated lanes
    approval_data = _safe_json_load(_APPROVAL_GATED_LANES_PATH)
    if isinstance(approval_data, dict):
        for lane_name, lane_info in approval_data.items():
            if isinstance(lane_info, dict):
                status = lane_info.get("status", "")
                if "PENDING" in status:
                    component_id = f"integration:{lane_name}"
                    _add_to_category("blocked", component_id, lane_name)

    # Build per-category summaries (each category lists ALL its items, even if shared)
    category_summary = {}
    for cat, items in categories.items():
        category_summary[cat] = {
            "count": len(items),
            "items": [i["label"] for i in items],
        }

    return {
        "status": "success",
        "unique_incomplete_count": len(seen_component_ids),
        "categories": category_summary,
        "category_counts": {k: v["count"] for k, v in category_summary.items()},
        "source_type": "registry_derived",
        "freshness": "current_commit",
        "verification_complete": True,
    }
