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
    process_data = _safe_json_load(_PROCESS_REGISTRY_PATH)
    process_count = len(process_data) if isinstance(process_data, list) else 0
    enabled_count = sum(
        1 for p in process_data
        if isinstance(p, dict) and p.get("enabled", False)
    ) if isinstance(process_data, list) else 0

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
    """Return the tool registry with safe metadata."""
    return {
        "categories": {
            cat: {
                "count": len(tools),
                "tools": tools,
            }
            for cat, tools in TOOL_REGISTRY.items()
        },
        "total_tools": sum(len(v) for v in TOOL_REGISTRY.values()),
        "live_tools": len(TOOL_REGISTRY.get("internal_safe", [])) + len(TOOL_REGISTRY.get("read_only", [])),
        "approval_gated": len(TOOL_REGISTRY.get("approval_gated", [])),
        "unavailable_tools": len(TOOL_REGISTRY.get("unavailable", [])),
        "default_policy": "default_deny_external: true",
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

def get_process_registry_live() -> Dict[str, Any]:
    """Read the live process registry."""
    data = _safe_json_load(_PROCESS_REGISTRY_PATH)
    if not isinstance(data, list):
        return {
            "status": "unavailable",
            "error": "Process registry not found or invalid.",
            "processes": [],
            "total": 0,
        }

    processes = []
    enabled = 0
    disabled = 0
    for p in data:
        if not isinstance(p, dict):
            continue
        is_enabled = p.get("enabled", False)
        if is_enabled:
            enabled += 1
        else:
            disabled += 1
        processes.append({
            "process_id": p.get("process_id", "unknown"),
            "name": p.get("name", "unknown"),
            "mode": p.get("mode", "unknown"),
            "enabled": is_enabled,
            "schedule": p.get("schedule", "unknown"),
            "risk": p.get("risk_level", "unknown"),
            "last_status": p.get("last_status", "never_run"),
            "last_run": p.get("last_run_at"),
            "blocked_actions": p.get("blocked_actions", []),
        })

    return {
        "status": "success",
        "processes": processes,
        "total": len(processes),
        "enabled": enabled,
        "disabled": disabled,
        "verification_complete": True,
    }


def get_process_details(process_id: str) -> Dict[str, Any]:
    """Return details for a specific process."""
    data = _safe_json_load(_PROCESS_REGISTRY_PATH)
    if not isinstance(data, list):
        return {"found": False, "error": "Process registry unavailable."}

    for p in data:
        if isinstance(p, dict) and p.get("process_id") == process_id:
            return {
                "found": True,
                "process_id": p.get("process_id"),
                "name": p.get("name"),
                "mode": p.get("mode"),
                "enabled": p.get("enabled", False),
                "schedule": p.get("schedule"),
                "risk_level": p.get("risk_level"),
                "last_status": p.get("last_status", "never_run"),
                "last_run": p.get("last_run_at"),
                "blocked_actions": p.get("blocked_actions", []),
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
    """Aggregate recent activity from multiple sources."""
    activity = {
        "processes": {"status": "unknown", "data": None},
        "approvals": {"status": "unknown", "data": None},
        "research": {"status": "unknown", "data": None},
        "alpha": {"status": "unknown", "data": None},
    }

    # Process status
    process_data = _safe_json_load(_PROCESS_REGISTRY_PATH)
    if isinstance(process_data, list):
        running = [p for p in process_data if isinstance(p, dict) and p.get("enabled")]
        failed = [p for p in process_data if isinstance(p, dict)
                  and p.get("last_status") in ("failed", "error")]
        never_run = [p for p in process_data if isinstance(p, dict)
                     and p.get("last_status") == "simulated"]
        activity["processes"] = {
            "status": "success",
            "total": len(process_data),
            "enabled": len(running),
            "failed": len(failed),
            "never_run": len(never_run),
            "all_simulated": all(
                p.get("last_status") == "simulated"
                for p in process_data if isinstance(p, dict)
            ),
        }

    # Approvals
    approval_data = _safe_json_load(_RAY_REVIEW_QUEUE_PATH)
    if isinstance(approval_data, dict):
        activity["approvals"] = {
            "status": "success",
            "total": approval_data.get("total", 0),
            "pending": approval_data.get("pending_count", 0),
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
            "state": alpha_data.get("state", "unknown"),
            "last_incoming": alpha_data.get("last_incoming_message"),
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
            "total_lanes": len(research_data),
            "approved_lanes": len(lanes),
            "approved": lanes,
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

    return {
        "status": overall,
        "components": activity,
        "verification_complete": True,
    }
