"""Nexus Semantic Query Planner — schema-aware intent→plan→execute pipeline.

Replaces brittle keyword routing with structured query planning.

Architecture:
  user question → planner (model) → query plan → validation → executor → verified result

The planner uses model reasoning to understand intent.
The executor uses deterministic code to retrieve facts.
The truth guard validates the result.
Nova explains the result naturally.

No writes. No client PII. No arbitrary SQL. No filesystem access.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# DOMAIN SCHEMAS — what the planner is allowed to reason over
# ═══════════════════════════════════════════════════════════════

DOMAIN_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "processes": {
        "description": "Nexus process registry — configured workflows and their state",
        "fields": {
            "process_id": {"type": "string", "values": "any"},
            "name": {"type": "string", "values": "any"},
            "configuration_state": {"type": "enum", "values": ["enabled", "disabled", "blocked", "unknown"]},
            "execution_mode": {"type": "enum", "values": [
                "ACTIVE_INTERNAL", "DRY_RUN", "TELEGRAM_OPERATOR",
                "SANDBOX_TEST", "BLOCKED", "unknown",
            ]},
            "runtime_state": {"type": "enum", "values": [
                "running", "idle", "completed", "failed", "simulated",
                "skipped", "blocked", "unknown", "never_run",
            ]},
            "schedule": {"type": "string", "values": "any"},
            "risk": {"type": "string", "values": "any"},
            "last_run": {"type": "string", "values": "any"},
        },
        "operations": ["overview", "list", "filter", "count", "group_count", "lookup"],
        "capability": "get_process_registry",
        "detail_capability": "get_process_details",
    },
    "tools": {
        "description": "Nexus tool registry — available software and integrations",
        "fields": {
            "name": {"type": "string", "values": "any"},
            "category": {"type": "enum", "values": [
                "internal_safe", "read_only", "approval_gated", "unavailable",
            ]},
            "status": {"type": "enum", "values": ["available", "unavailable", "approval_required"]},
        },
        "operations": ["overview", "list", "filter", "count", "group_count"],
        "capability": "get_tool_registry",
    },
    "agents": {
        "description": "Nexus agents — AI workers and their capabilities",
        "fields": {
            "agent_id": {"type": "string", "values": ["nexus_hermes", "hermes_nova", "alpha"]},
            "name": {"type": "string", "values": "any"},
            "role": {"type": "string", "values": "any"},
            "read_count": {"type": "integer", "values": "any"},
            "write_count": {"type": "integer", "values": "any"},
            "tool_count": {"type": "integer", "values": "any"},
        },
        "operations": ["overview", "list", "lookup"],
        "capability": "get_agent_registry",
        "detail_capability": "get_agent_details",
    },
    "reports": {
        "description": "Nexus reports — generated documents and their metadata",
        "fields": {
            "name": {"type": "string", "values": "any"},
            "category": {"type": "string", "values": "any"},
            "modified": {"type": "string", "values": "any"},
        },
        "operations": ["overview", "list"],
        "capability": "get_latest_reports",
        "index_capability": "get_report_index",
    },
    "approvals": {
        "description": "Nexus approval queue — items awaiting review",
        "fields": {
            "pending_count": {"type": "integer", "values": "any"},
            "queue_status": {"type": "enum", "values": ["empty", "has_items", "unavailable"]},
        },
        "operations": ["overview"],
        "capability": "get_pending_approvals",
    },
    "research": {
        "description": "Nexus research pipeline — Alpha research runs and findings",
        "fields": {
            "total_runs": {"type": "integer", "values": "any"},
            "completed_runs": {"type": "integer", "values": "any"},
            "total_results": {"type": "integer", "values": "any"},
        },
        "operations": ["overview"],
        "capability": "get_recent_research",
    },
    "system_health": {
        "description": "Nexus system health — service status and failures",
        "fields": {
            "overall_status": {"type": "enum", "values": ["healthy", "degraded", "unknown", "partial"]},
            "active_services": {"type": "integer", "values": "any"},
            "failed_services": {"type": "integer", "values": "any"},
        },
        "operations": ["overview"],
        "capability": "get_system_health",
    },
    "recent_activity": {
        "description": "Nexus recent activity — what happened across processes, approvals, research",
        "fields": {
            "has_any_real_execution": {"type": "boolean", "values": [True, False]},
            "telemetry_summary": {"type": "string", "values": "any"},
        },
        "operations": ["overview", "summarize"],
        "capability": "get_recent_activity",
    },
    "incomplete_areas": {
        "description": "Nexus incomplete/unavailable areas — what is not yet live",
        "fields": {
            "unique_incomplete_count": {"type": "integer", "values": "any"},
        },
        "operations": ["overview"],
        "capability": "get_incomplete_areas",
    },
    "overview": {
        "description": "Nexus system overview — architecture, agents, components",
        "fields": {
            "system_name": {"type": "string", "values": "any"},
            "agent_count": {"type": "integer", "values": "any"},
            "process_count": {"type": "integer", "values": "any"},
        },
        "operations": ["overview"],
        "capability": "get_nexus_overview",
    },
}

# ═══════════════════════════════════════════════════════════════
# QUERY PLAN CONTRACT
# ═══════════════════════════════════════════════════════════════

ALLOWED_OPERATIONS = {
    "overview", "list", "filter", "count", "group_count",
    "lookup", "compare", "summarize", "provenance",
}

ALLOWED_OPERATORS = {"eq", "neq", "in", "not_in", "contains", "exists"}

# Fields that support ambiguity (map to multiple dimensions)
AMBIGUOUS_FIELDS = {
    "blocked": ["configuration_state", "execution_mode", "runtime_state"],
}

# Source requirements per domain
SOURCE_REQUIREMENTS = {
    "processes": "structural",
    "tools": "structural",
    "agents": "structural",
    "reports": "operational_state",
    "approvals": "operational_state",
    "research": "operational_state",
    "system_health": "operational_state",
    "recent_activity": "execution_telemetry",
    "incomplete_areas": "structural",
    "overview": "structural",
}

# ═══════════════════════════════════════════════════════════════
# PLANNER — model-driven intent → structured plan
# ═══════════════════════════════════════════════════════════════

PLANNER_SYSTEM_PROMPT = """You are a Nexus query planner. Your ONLY job is to convert a user question into a structured query plan.

You have access to these Nexus domains and their fields:

{schema_text}

OUTPUT FORMAT — return ONLY a JSON object (no markdown, no explanation):

{{
  "domain": "<domain_name>",
  "operation": "<operation>",
  "conditions": [
    {{"field": "<field>", "operator": "<op>", "value": "<value>"}}
  ],
  "projection": ["<field1>", "<field2>"],
  "aggregate": null,
  "ambiguity": null,
  "source_requirement": "structural|operational_state|execution_telemetry|any",
  "reason": "<brief explanation of what this query answers>"
}}

RULES:
1. Only use domains and fields listed above.
2. Operations: overview, list, filter, count, group_count, lookup, compare, summarize, provenance.
3. Operators: eq, neq, in, not_in, contains, exists.
4. If "blocked" is mentioned without context, set ambiguity field.
5. If the question asks about execution evidence, set source_requirement to "execution_telemetry".
6. If the question is about provenance/source, set operation to "provenance".
7. Do NOT answer the question. Only output the plan.
8. If the question is NOT about Nexus data (greetings, opinions, etc.), output: {{"domain": "none"}}"""


def _build_schema_text() -> str:
    """Build schema description for the planner prompt."""
    lines = []
    for domain, schema in DOMAIN_SCHEMAS.items():
        fields = ", ".join(schema["fields"].keys())
        ops = ", ".join(schema["operations"])
        lines.append(f"- {domain}: fields=[{fields}], operations=[{ops}]")
    return "\n".join(lines)


def plan_query(
    user_question: str,
    conversation_context: Optional[str] = None,
    model_call_fn: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Convert a user question into a structured Nexus query plan.

    Uses model reasoning to understand intent, then validates the output
    against allowed schemas.

    Returns a validated query plan dict, or {"domain": "none"} if the
    question is not about Nexus data.
    """
    schema_text = _build_schema_text()
    system_prompt = PLANNER_SYSTEM_PROMPT.format(schema_text=schema_text)

    messages = [{"role": "system", "content": system_prompt}]
    if conversation_context:
        messages.append({"role": "user", "content": f"Context from conversation:\n{conversation_context}\n\nUser question: {user_question}"})
    else:
        messages.append({"role": "user", "content": user_question})

    # Call the model
    if model_call_fn is None:
        # Fallback: use deterministic pattern matching
        return _deterministic_plan(user_question)

    try:
        result = model_call_fn(messages)
        content = result.get("content", "")
        if not content:
            return _deterministic_plan(user_question)

        # Parse JSON from response
        plan = _parse_plan_json(content)
        if plan is None:
            return _deterministic_plan(user_question)

        # Validate
        validated = validate_plan(plan)
        return validated

    except Exception as exc:
        log.warning("Planner model call failed: %s", exc)
        return _deterministic_plan(user_question)


def _parse_plan_json(content: str) -> Optional[Dict[str, Any]]:
    """Parse JSON from model response, handling markdown fences."""
    # Strip markdown code fences
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first and last lines (fences)
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        content = "\n".join(lines)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to find JSON object in the content
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None


# ═══════════════════════════════════════════════════════════════
# DETERMINISTIC FALLBACK PLANNER
# ═══════════════════════════════════════════════════════════════

# Semantic intent patterns for deterministic planning
_INTENT_PATTERNS: List[Tuple[str, str, str, List[str]]] = [
    # (pattern, domain, operation, reason)
    # Process queries
    (r'process|workflow|automation|job', "processes", "list", "Process listing or query"),
    (r'enabled.*not.*(?:running|executing|active|doing)', "processes", "filter",
     "Comparative: enabled but not executing"),
    (r'(?:not|isn\'t|aren\'t).*running.*enabled', "processes", "filter",
     "Comparative: not running but enabled"),
    (r'configured.*(?:not|isn\'t|aren\'t).*(?:running|active|executing)', "processes", "filter",
     "Comparative: configured but not active"),
    (r'simulated|skipped|blocked', "processes", "filter", "Process state filter"),
    (r'running|executing|active|live', "processes", "filter", "Process runtime query"),
    (r'evidence.*(?:ran|executed|run)', "recent_activity", "summarize", "Execution evidence query"),
    (r'(?:did|do|can).*(?:anything|something).*(?:run|execute|ran|executed)', "recent_activity", "summarize",
     "Execution evidence query"),
    (r'prove|proof.*(?:ran|executed|run)', "recent_activity", "summarize", "Execution proof query"),

    # Tool queries
    (r'tool|software|installed|available', "tools", "list", "Tool listing or query"),
    (r'(?:require|need|approval|gated)', "tools", "filter", "Tool approval query"),

    # Agent queries
    (r'agent|bot|nova|hermes|alpha', "agents", "list", "Agent listing or query"),

    # Report queries
    (r'report|generated|recent.*document', "reports", "list", "Report listing or query"),

    # Approval queries
    (r'approv|pending|review.*queue|waiting', "approvals", "overview", "Approval queue query"),

    # Research queries
    (r'research|finding|alpha.*research', "research", "overview", "Research pipeline query"),

    # Health queries
    (r'health|system.*status|broken|down|degraded', "system_health", "overview", "System health query"),

    # Activity queries
    (r'happened|what.*new|activity|recent|today', "recent_activity", "overview", "Recent activity query"),

    # Incomplete queries
    (r'incomplete|unavailable|mock|missing|not.*live|not.*working|gap', "incomplete_areas", "overview",
     "Incomplete areas query"),

    # Overview queries
    (r'nexus|overview|what.*is.*this|architecture|structure', "overview", "overview", "System overview query"),
]


def _deterministic_plan(user_question: str) -> Dict[str, Any]:
    """Deterministic fallback planner using pattern matching."""
    lower = user_question.lower()

    # Check for non-Nexus questions
    non_nexus = re.search(
        r'^(?:hello|hi|hey|how are you|what do you think|opinion|coffee|cadillac|real estate|buying)',
        lower
    )
    if non_nexus:
        return {"domain": "none", "reason": "Not a Nexus data question"}

    best_match = None
    best_score = 0

    for pattern, domain, operation, reason in _INTENT_PATTERNS:
        if re.search(pattern, lower):
            # Score by specificity (longer patterns = more specific)
            score = len(pattern)
            if score > best_score:
                best_score = score
                best_match = {
                    "domain": domain,
                    "operation": operation,
                    "conditions": [],
                    "projection": [],
                    "aggregate": None,
                    "ambiguity": None,
                    "source_requirement": SOURCE_REQUIREMENTS.get(domain, "any"),
                    "reason": reason,
                }

    if best_match is None:
        return {"domain": "none", "reason": "No matching Nexus domain"}

    # Add conditions based on keywords
    plan = best_match
    conditions = []

    if plan["domain"] == "processes":
        # Configuration state conditions
        if re.search(r'\benabled\b', lower) and not re.search(r'not.*enabled|disabled', lower):
            conditions.append({"field": "configuration_state", "operator": "eq", "value": "enabled"})
        if re.search(r'\bdisabled\b', lower):
            conditions.append({"field": "configuration_state", "operator": "eq", "value": "disabled"})

        # Runtime state conditions
        if re.search(r'\brunning\b', lower) and not re.search(r'not.*running|isn.*running|aren.*running', lower):
            conditions.append({"field": "runtime_state", "operator": "eq", "value": "running"})
        if re.search(r'not.*running|isn.*running|aren.*running|not.*executing|isn.*executing', lower):
            conditions.append({"field": "runtime_state", "operator": "neq", "value": "running"})
        if re.search(r'\bsimulated\b', lower):
            conditions.append({"field": "runtime_state", "operator": "eq", "value": "simulated"})
        if re.search(r'\bskipped\b', lower):
            conditions.append({"field": "runtime_state", "operator": "eq", "value": "skipped"})

        # Blocked ambiguity
        if re.search(r'\bblocked\b', lower):
            ambiguous_field = "blocked"
            if ambiguous_field in AMBIGUOUS_FIELDS:
                plan["ambiguity"] = {
                    "field": ambiguous_field,
                    "matches": AMBIGUOUS_FIELDS[ambiguous_field],
                }

        # Execution mode conditions
        if re.search(r'execution.?mode.*blocked|mode.*BLOCKED', lower):
            conditions.append({"field": "execution_mode", "operator": "eq", "value": "BLOCKED"})
        if re.search(r'runtime.*blocked|blocked.*runtime', lower):
            conditions.append({"field": "runtime_state", "operator": "eq", "value": "blocked"})
        if re.search(r'\bdry.?run\b', lower):
            conditions.append({"field": "execution_mode", "operator": "eq", "value": "DRY_RUN"})

    plan["conditions"] = conditions
    return plan


# ═══════════════════════════════════════════════════════════════
# PLAN VALIDATOR
# ═══════════════════════════════════════════════════════════════

def validate_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a query plan against schemas. Returns validated plan or error."""
    if not isinstance(plan, dict):
        return {"domain": "none", "error": "Plan must be a dict"}

    domain = plan.get("domain", "none")

    # Allow "none" domain (non-Nexus question)
    if domain == "none":
        return {"domain": "none", "reason": plan.get("reason", "Not a Nexus data question")}

    # Validate domain
    if domain not in DOMAIN_SCHEMAS:
        return {"domain": "none", "error": f"Unknown domain: {domain}"}

    schema = DOMAIN_SCHEMAS[domain]

    # Validate operation
    operation = plan.get("operation", "overview")
    if operation not in schema["operations"]:
        plan["operation"] = schema["operations"][0]  # fallback to first allowed

    # Validate conditions
    valid_conditions = []
    for cond in plan.get("conditions", []):
        field = cond.get("field", "")
        operator = cond.get("operator", "eq")
        value = cond.get("value")

        if field not in schema["fields"]:
            continue  # skip invalid fields
        if operator not in ALLOWED_OPERATORS:
            continue  # skip invalid operators

        field_schema = schema["fields"][field]
        if field_schema["type"] == "enum" and value not in field_schema["values"]:
            continue  # skip invalid enum values

        valid_conditions.append(cond)

    plan["conditions"] = valid_conditions

    # Ensure required fields
    plan.setdefault("projection", [])
    plan.setdefault("aggregate", None)
    plan.setdefault("ambiguity", None)
    plan.setdefault("source_requirement", SOURCE_REQUIREMENTS.get(domain, "any"))
    plan.setdefault("reason", "")

    return plan


# ═══════════════════════════════════════════════════════════════
# QUERY EXECUTOR — deterministic execution over certified reads
# ═══════════════════════════════════════════════════════════════

# Lazy imports to avoid circular dependencies
_capability_executor: Optional[Callable] = None


def register_executor(executor: Callable) -> None:
    """Register the capability executor function."""
    global _capability_executor
    _capability_executor = executor


def execute_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a validated query plan against existing Nexus capabilities.

    Returns structured verified result with provenance.
    """
    domain = plan.get("domain", "none")

    if domain == "none":
        return {
            "status": "not_nexus",
            "plan": plan,
            "data": None,
            "provenance": None,
            "coverage": {"structural": False, "operational_state": False, "execution_telemetry": False},
        }

    if domain not in DOMAIN_SCHEMAS:
        return {
            "status": "error",
            "plan": plan,
            "data": None,
            "error": f"Unknown domain: {domain}",
        }

    schema = DOMAIN_SCHEMAS[domain]
    capability = schema.get("capability")

    if capability is None:
        return {
            "status": "error",
            "plan": plan,
            "data": None,
            "error": f"No capability for domain: {domain}",
        }

    # Execute the capability
    if _capability_executor is None:
        return {
            "status": "error",
            "plan": plan,
            "data": None,
            "error": "No capability executor registered",
        }

    try:
        result = _capability_executor(capability)
    except Exception as exc:
        return {
            "status": "error",
            "plan": plan,
            "data": None,
            "error": f"Capability execution failed: {exc}",
        }

    if not isinstance(result, dict):
        return {
            "status": "error",
            "plan": plan,
            "data": None,
            "error": "Invalid capability result",
        }

    status = result.get("status", "unknown")
    data = result.get("data", result)

    # Apply filters from conditions
    conditions = plan.get("conditions", [])
    if conditions and domain == "processes" and "processes" in data:
        filtered = _apply_process_filters(data["processes"], conditions)
        data = {**data, "processes": filtered, "filtered_count": len(filtered)}

    # Apply projection
    projection = plan.get("projection", [])
    if projection and domain == "processes" and "processes" in data:
        projected = []
        for item in data["processes"]:
            projected.append({k: v for k, v in item.items() if k in projection or k in ("process_id", "name")})
        data = {**data, "processes": projected}

    # Build coverage
    source_req = plan.get("source_requirement", "any")
    coverage = {
        "structural": source_req in ("structural", "any"),
        "operational_state": source_req in ("operational_state", "any"),
        "execution_telemetry": source_req in ("execution_telemetry", "any"),
    }

    # For execution telemetry: check if real execution exists
    if source_req == "execution_telemetry":
        has_real = False
        if domain == "processes" and "has_real_execution" in data:
            has_real = data["has_real_execution"]
        elif domain == "recent_activity" and "has_any_real_execution" in data:
            has_real = data["has_any_real_execution"]
        coverage["execution_telemetry"] = has_real

    return {
        "status": status if status == "success" else "partial",
        "plan": plan,
        "data": data,
        "provenance": {
            "capability": capability,
            "source_type": result.get("source_type", domain),
            "freshness": result.get("freshness", "unknown"),
        },
        "coverage": coverage,
    }


def _apply_process_filters(
    processes: List[Dict[str, Any]],
    conditions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Apply filter conditions to a list of normalized processes."""
    result = list(processes)

    for cond in conditions:
        field = cond.get("field", "")
        operator = cond.get("operator", "eq")
        value = cond.get("value")

        filtered = []
        for p in result:
            pval = p.get(field)
            if operator == "eq" and pval == value:
                filtered.append(p)
            elif operator == "neq" and pval != value:
                filtered.append(p)
            elif operator == "in" and isinstance(value, list) and pval in value:
                filtered.append(p)
            elif operator == "not_in" and isinstance(value, list) and pval not in value:
                filtered.append(p)
            elif operator == "contains" and isinstance(pval, str) and isinstance(value, str) and value in pval:
                filtered.append(p)
            elif operator == "exists" and pval is not None:
                filtered.append(p)

        result = filtered

    return result


# ═══════════════════════════════════════════════════════════════
# RESULT FORMATTER — structured result → Nova context
# ═══════════════════════════════════════════════════════════════

def format_plan_result(result: Dict[str, Any]) -> str:
    """Format a plan execution result into Nova context."""
    plan = result.get("plan", {})
    data = result.get("data", {})
    provenance = result.get("provenance", {})
    coverage = result.get("coverage", {})
    status = result.get("status", "unknown")
    domain = plan.get("domain", "none")

    if domain == "none":
        return ""

    lines = [
        "[VERIFIED NEXUS KNOWLEDGE]",
        f"domain: {domain}",
        f"operation: {plan.get('operation', 'unknown')}",
        f"status: {status}",
        f"source: {provenance.get('source_type', 'unknown')}",
        f"freshness: {provenance.get('freshness', 'unknown')}",
        f"reason: {plan.get('reason', '')}",
        "",
    ]

    # Source classification
    lines.append("Source classification:")
    lines.append(f"  structural: {str(coverage.get('structural', False)).lower()}")
    lines.append(f"  operational_state: {str(coverage.get('operational_state', False)).lower()}")
    lines.append(f"  execution_telemetry: {str(coverage.get('execution_telemetry', False)).lower()}")
    lines.append("")

    # Conditions applied
    conditions = plan.get("conditions", [])
    if conditions:
        lines.append("Filters applied:")
        for c in conditions:
            lines.append(f"  {c.get('field', '?')} {c.get('operator', '?')} {c.get('value', '?')}")
        lines.append("")

    # Ambiguity
    ambiguity = plan.get("ambiguity")
    if ambiguity:
        lines.append(f"Ambiguity: '{ambiguity.get('field', '?')}' maps to {ambiguity.get('matches', [])}")
        lines.append("")

    # Data (domain-specific formatting)
    if domain == "processes":
        lines.extend(_format_process_data(data, plan))
    elif domain == "tools":
        lines.extend(_format_tool_data(data))
    elif domain == "agents":
        lines.extend(_format_agent_data(data))
    elif domain == "reports":
        lines.extend(_format_report_data(data))
    elif domain == "approvals":
        lines.extend(_format_approval_data(data))
    elif domain == "recent_activity":
        lines.extend(_format_activity_data(data))
    elif domain == "incomplete_areas":
        lines.extend(_format_incomplete_data(data))
    elif domain == "overview":
        lines.extend(_format_overview_data(data))
    else:
        lines.append(f"data: {json.dumps(data, default=str)[:500]}")

    lines.append("[END VERIFIED NEXUS KNOWLEDGE]")
    return "\n".join(lines)


def _format_process_data(data: Dict, plan: Dict) -> List[str]:
    """Format process data for Nova context."""
    lines = []
    total = data.get("total", 0)
    config = data.get("configuration_counts", {})
    modes = data.get("mode_counts", {})
    runtime = data.get("runtime_counts", {})
    recon = data.get("reconciliation", {})
    has_real = data.get("has_real_execution", False)
    all_sim = data.get("all_simulated_or_skipped", False)
    processes = data.get("processes", [])
    filtered_count = data.get("filtered_count")

    lines.append(f"Total: {total}")
    if filtered_count is not None:
        lines.append(f"Filtered count: {filtered_count}")

    lines.append("")
    lines.append("Configuration state:")
    for s, c in sorted(config.items()):
        lines.append(f"  {s}: {c}")
    lines.append(f"  reconciliation: {str(recon.get('configuration', False)).lower()}")

    lines.append("")
    lines.append("Execution mode:")
    for m, c in sorted(modes.items()):
        lines.append(f"  {m}: {c}")
    lines.append(f"  reconciliation: {str(recon.get('execution_mode', False)).lower()}")

    lines.append("")
    lines.append("Runtime state:")
    for s, c in sorted(runtime.items()):
        lines.append(f"  {s}: {c}")
    lines.append(f"  reconciliation: {str(recon.get('runtime_state', False)).lower()}")

    lines.append("")
    lines.append("Execution telemetry:")
    lines.append(f"  coverage: {'observed' if has_real else 'unavailable'}")
    lines.append(f"  has_real_execution: {str(has_real).lower()}")
    lines.append(f"  all_simulated_or_skipped: {str(all_sim).lower()}")

    if processes:
        lines.append("")
        lines.append("Processes:")
        for p in processes[:20]:  # bound output
            lines.append(
                f"  - {p.get('process_id', '?')}: {p.get('name', '?')} "
                f"[config: {p.get('configuration_state', '?')}, "
                f"mode: {p.get('execution_mode', '?')}, "
                f"runtime: {p.get('runtime_state', '?')}]"
            )

    return lines


def _format_tool_data(data: Dict) -> List[str]:
    lines = []
    lines.append(f"Total: {data.get('total', 0)}")
    lines.append(f"Usable now: {data.get('usable_now', 0)}")
    cats = data.get("categories", {})
    for cat, cat_data in cats.items():
        lines.append(f"  {cat}: {cat_data.get('count', 0)}")
    return lines


def _format_agent_data(data: Dict) -> List[str]:
    lines = []
    lines.append(f"Total: {data.get('total', 0)}")
    for a in data.get("agents", []):
        lines.append(
            f"  - {a.get('agent_id', '?')}: {a.get('name', '?')} "
            f"(reads: {a.get('read_count', 0)}, writes: {a.get('write_count', 0)})"
        )
    return lines


def _format_report_data(data: Dict) -> List[str]:
    lines = []
    lines.append(f"Total latest: {data.get('total_latest', 0)}")
    for r in data.get("reports", [])[:5]:
        lines.append(f"  - {r.get('name', '?')} ({r.get('modified', '?')})")
    return lines


def _format_approval_data(data: Dict) -> List[str]:
    lines = []
    lines.append(f"Pending: {data.get('count', 0)}")
    return lines


def _format_activity_data(data: Dict) -> List[str]:
    lines = []
    lines.append(f"Has real execution: {str(data.get('has_any_real_execution', False)).lower()}")
    lines.append(f"Telemetry: {data.get('telemetry_summary', 'unknown')}")
    components = data.get("components", {})
    for comp, cdata in components.items():
        lines.append(f"  {comp}: {cdata.get('status', 'unknown')}")
    return lines


def _format_incomplete_data(data: Dict) -> List[str]:
    lines = []
    lines.append(f"Unique incomplete: {data.get('unique_incomplete_count', 0)}")
    cats = data.get("categories", {})
    for cat, cat_data in cats.items():
        count = cat_data.get("count", 0)
        if count > 0:
            items = cat_data.get("items", [])
            lines.append(f"  {cat} ({count}):")
            for item in items[:3]:
                lines.append(f"    - {item}")
    return lines


def _format_overview_data(data: Dict) -> List[str]:
    lines = []
    lines.append(f"System: {data.get('system_name', '?')} v{data.get('version', '?')}")
    lines.append(f"Agents: {data.get('agent_count', 0)}")
    lines.append(f"Processes: {data.get('process_count', 0)}")
    return lines
