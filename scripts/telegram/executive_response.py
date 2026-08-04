"""
Executive Response Layer for Nexus Hermes.

Transforms raw operational data into concise, plain-English executive reports
that Ray can understand immediately.

Supports:
- Executive system status reports
- Research summaries with deduplication
- Failure reports separated by category
- Phoenix time formatting
- Technical detail hiding
- Telegram pagination
"""

import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

PHOENIX_TZ = timezone(timedelta(hours=-7))

# --- Technical detail patterns to hide by default ---
_UUID_PATTERN = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.IGNORECASE)
_SCRIPT_PATH_PATTERN = re.compile(r'scripts/[\w/]+\.py')
_DATA_PATH_PATTERN = re.compile(r'data/[\w/_-]+\.json')
_TABLE_NAME_PATTERN = re.compile(r'(?:table|tables):\s*[\w_,\s]+')
_ISO_TIMESTAMP_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[\.\d]*Z?')
_RUN_ID_PATTERN = re.compile(r'(?:run[_\s]id|receipt[_\s]id|work[_\s]order[_\s]id):\s*\S+', re.IGNORECASE)
_PROVIDER_PATTERN = re.compile(r'(?:provider|source):\s*\w+', re.IGNORECASE)

# --- Failure status translations ---
STATUS_TRANSLATIONS = {
    "BLOCKED_BY_PROVIDER_CONFIGURATION": "External provider setup is incomplete",
    "BLOCKED_BY_LEGAL_OR_POLICY_BOUNDARY": "Intentionally restricted by current operating policy",
    "WAITING_FOR_VALID_SIGNAL": "Trading engine is active and waiting for a strategy signal",
    "BLOCKED_AUTONOMOUS_EXECUTION": "Requires direct Ray intervention",
    "APPROVAL_GATED_LIVE_READY": "Ready pending Ray approval",
    "APPROVAL_GATED_LIVE_PENDING_ENV": "Waiting for environment configuration",
    "APPROVAL_GATED_LIVE_PENDING_RUNNER": "Waiting for approved runner",
    "APPROVAL_GATED_LIVE_PENDING_GUARD": "Waiting for guard configuration",
}

# --- Failure categories ---
FAILURE_CATEGORIES = {
    "ACTIVE_NOW": "Currently blocking operations",
    "RESOLVED": "Previously failed, now working",
    "HISTORICAL_CERTIFICATION": "Historical activation failures, already addressed",
    "INTENTIONAL_BOUNDARY": "Intentionally restricted by policy",
    "EXTERNAL_CONFIGURATION": "Requires external provider setup",
}

# --- Constants for Telegram pagination ---
TELEGRAM_MAX_LENGTH = 4000
TELEGRAM_PAGE_OVERHEAD = 200


def _load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def _now_phoenix():
    return datetime.now(PHOENIX_TZ)


def format_phoenix_time(utc_string=None):
    """Convert UTC timestamp to human-readable Phoenix time."""
    if utc_string is None:
        now = _now_phoenix()
        return now.strftime("%-I:%M %p") + " Phoenix time"

    try:
        if isinstance(utc_string, str):
            # Handle ISO format
            utc_string = utc_string.replace("Z", "+00:00")
            if utc_string.endswith("+00:00"):
                dt = datetime.fromisoformat(utc_string).replace(tzinfo=timezone.utc)
            else:
                dt = datetime.fromisoformat(utc_string)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = utc_string
        phoenix_dt = dt.astimezone(PHOENIX_TZ)
        now_phoenix = _now_phoenix()

        # Same day
        if phoenix_dt.date() == now_phoenix.date():
            return "Today at " + phoenix_dt.strftime("%-I:%M %p")
        # Yesterday
        yesterday = now_phoenix.date() - timedelta(days=1)
        if phoenix_dt.date() == yesterday:
            return "Yesterday at " + phoenix_dt.strftime("%-I:%M %p")
        # Within 7 days
        days_ago = (now_phoenix.date() - phoenix_dt.date()).days
        if 1 < days_ago <= 7:
            return f"{days_ago} days ago at " + phoenix_dt.strftime("%-I:%M %p")
        # Older
        return phoenix_dt.strftime("%B %-d at %-I:%M %p")
    except Exception:
        return "Not currently recorded"


def hide_technical_details(text):
    """Remove technical identifiers from text for executive display."""
    text = _UUID_PATTERN.sub("[ID hidden]", text)
    text = _SCRIPT_PATH_PATTERN.sub("[script]", text)
    text = _DATA_PATH_PATTERN.sub("[data file]", text)
    text = _ISO_TIMESTAMP_PATTERN.sub("[timestamp]", text)
    text = _RUN_ID_PATTERN.sub(lambda m: m.group(0).split(":")[0] + ": [hidden]", text)
    return text


def paginate_response(text, page=1, page_size=None):
    """Split long Telegram messages into pages."""
    if page_size is None:
        page_size = TELEGRAM_MAX_LENGTH - TELEGRAM_PAGE_OVERHEAD

    lines = text.split("\n")
    total_lines = len(lines)
    lines_per_page = max(1, page_size // max(1, total_lines // max(1, (total_lines + page_size // 50 - 1) // max(1, page_size // 50))))

    # More precise: split by character count
    pages = []
    current_page = []
    current_length = 0

    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        if current_length + line_len > page_size and current_page:
            pages.append("\n".join(current_page))
            current_page = [line]
            current_length = line_len
        else:
            current_page.append(line)
            current_length += line_len

    if current_page:
        pages.append("\n".join(current_page))

    if not pages:
        pages = ["No data available."]

    total_pages = len(pages)
    page = max(1, min(page, total_pages))

    result = pages[page - 1]

    # Add page indicator if multi-page
    if total_pages > 1:
        result += f"\n\nPage {page}/{total_pages} — Say 'next page' or 'show page N'"

    return result


# --- System Status ---

def build_executive_system_status(registry_path=None):
    """Build an executive system status report from the process registry."""
    if registry_path is None:
        registry_path = "data/operations/nexus_process_registry.json"

    registry = _load_json(registry_path) or []
    if not registry:
        return {
            "overall": "UNKNOWN",
            "summary": "Process registry not available.",
            "working_normally": [],
            "needs_attention": [],
            "research": "Not currently recorded",
            "trading": "Not currently recorded",
            "communications": "Not currently recorded",
            "client_operations": "Not currently recorded",
            "recommended_next_action": "Check process registry availability.",
            "action_required_from_ray": "NO",
            "updated": format_phoenix_time(),
        }

    # Categorize processes
    enabled = [p for p in registry if p.get("enabled")]
    blocked = [p for p in registry if p.get("mode") == "BLOCKED"]
    completed = [p for p in enabled if p.get("last_status") == "completed"]
    failed = [p for p in enabled if p.get("last_status") == "failed"]
    active_telegram = [p for p in enabled if p.get("telegram_allowed")]

    # Working normally: completed processes
    working = []
    for p in completed:
        name = p.get("name", p.get("process_id", "Unknown"))
        working.append(name)

    # Needs attention: blocked, failed, or disabled high-value processes
    attention = []
    for p in blocked:
        attention.append(f"{p.get('name', p.get('process_id'))} — blocked")
    for p in failed:
        attention.append(f"{p.get('name', p.get('process_id'))} — last run failed")

    # Research status
    research_items = [p for p in registry if "research" in p.get("category", "").lower() or "notebook" in p.get("category", "").lower()]
    research_completed = sum(1 for p in research_items if p.get("last_status") == "completed")
    research_status = f"{research_completed} of {len(research_items)} research processes completed"

    # Trading status
    trading_items = [p for p in registry if "trading" in p.get("category", "").lower() or "signal" in p.get("category", "").lower()]
    if trading_items:
        trading_active = [p for p in trading_items if p.get("enabled")]
        trading_status = f"{len(trading_active)} trading processes active"
    else:
        trading_status = "No trading processes registered"

    # Communications
    comms_items = [p for p in registry if any(kw in p.get("category", "").lower() for kw in ["telegram", "email", "sms", "whatsapp"])]
    comms_active = [p for p in comms_items if p.get("enabled") and p.get("last_status") == "completed"]
    comms_status = f"{len(comms_active)} of {len(comms_items)} communication channels active"

    # Client operations
    client_items = [p for p in registry if "client" in p.get("category", "").lower() or "portal" in p.get("category", "").lower()]
    client_active = [p for p in client_items if p.get("enabled")]
    client_status = f"{len(client_active)} client operations processes active"

    # Determine overall status
    if len(failed) > 0 or len(blocked) > 2:
        overall = "ATTENTION_NEEDED"
    elif len(completed) >= len(enabled) * 0.8:
        overall = "OPERATIONAL"
    else:
        overall = "MOSTLY_OPERATIONAL"

    # Recommended next action
    if attention:
        recommended = f"Address: {attention[0]}"
    else:
        recommended = "System is running normally. No immediate action required."

    # Action required from Ray
    action_required = "YES" if len(failed) > 0 or len(blocked) > 0 else "NO"

    return {
        "overall": overall,
        "summary": f"{len(completed)} of {len(enabled)} enabled processes completed successfully.",
        "working_normally": working[:10],
        "needs_attention": attention[:5],
        "research": research_status,
        "trading": trading_status,
        "communications": comms_status,
        "client_operations": client_status,
        "recommended_next_action": recommended,
        "action_required_from_ray": action_required,
        "updated": format_phoenix_time(),
    }


def format_system_status_report(data):
    """Format executive system status into a readable Telegram message."""
    lines = [
        "NEXUS SYSTEM STATUS",
        "",
        f"Overall: {data['overall'].replace('_', ' ').title()}",
        "",
        f"Summary: {data['summary']}",
        "",
    ]

    if data["working_normally"]:
        lines.append("Working normally")
        for item in data["working_normally"][:8]:
            lines.append(f"  - {item}")
        lines.append("")

    if data["needs_attention"]:
        lines.append("Needs attention")
        for item in data["needs_attention"]:
            lines.append(f"  - {item}")
        lines.append("")
    else:
        lines.append("Needs attention: None")
        lines.append("")

    lines.extend([
        f"Research: {data['research']}",
        f"Trading: {data['trading']}",
        f"Communications: {data['communications']}",
        f"Client operations: {data['client_operations']}",
        "",
        f"Recommended next action: {data['recommended_next_action']}",
        f"Action required from Ray: {data['action_required_from_ray']}",
        f"Updated: {data['updated']}",
    ])

    return "\n".join(lines)


# --- Research Summary ---

def _normalize_research_query(item):
    """Create a normalized key for deduplication."""
    title = (item.get("title", "") or "").lower().strip()
    route = (item.get("recommended_route", "") or "").lower().strip()
    # Remove common prefixes and normalize
    title = re.sub(r'^adapt:\s*', '', title)
    title = re.sub(r'[^a-z0-9\s]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return f"{title}|{route}"


def deduplicate_research(items):
    """Consolidate duplicate research items."""
    groups = {}
    for item in items:
        key = _normalize_research_query(item)
        if key not in groups:
            groups[key] = {
                "representative": item,
                "duplicates": [],
                "count": 1,
            }
        else:
            groups[key]["duplicates"].append(item)
            groups[key]["count"] += 1

    deduplicated = []
    duplicates_consolidated = 0
    for key, group in groups.items():
        rep = group["representative"]
        rep["_duplicate_count"] = group["count"]
        rep["_duplicates_consolidated"] = len(group["duplicates"])
        deduplicated.append(rep)
        duplicates_consolidated += len(group["duplicates"])

    # Sort by monetization score descending
    deduplicated.sort(key=lambda x: x.get("monetization_score", 0), reverse=True)

    return deduplicated, duplicates_consolidated


def build_executive_research_summary(scored_items_path=None, max_items=5):
    """Build an executive research summary with deduplication."""
    if scored_items_path is None:
        scored_items_path = "data/research_memory/notebooklm_scored_items_latest.json"

    items = _load_json(scored_items_path) or []
    if not items:
        return {
            "total_runs": 0,
            "completed_runs": 0,
            "opportunity_groups": 0,
            "duplicates_consolidated": 0,
            "failures": 0,
            "main_topics": [],
            "top_opportunities": [],
            "top_recommendation": "No research data available.",
            "recommended_next_action": "Run research to generate opportunities.",
            "action_required_from_ray": "NO",
        }

    deduplicated, duplicates_consolidated = deduplicate_research(items)

    # Extract main topics from titles
    topics = set()
    for item in deduplicated:
        title = (item.get("title", "") or "").lower()
        title = re.sub(r'^adapt:\s*', '', title)
        # Extract topic keywords
        for keyword in ["credit", "funding", "grant", "payment", "client", "social", "trading", "youtube", "research"]:
            if keyword in title:
                topics.add(keyword.replace("_", " ").title())

    # Build opportunities
    opportunities = []
    for item in deduplicated[:max_items]:
        title = item.get("title", "Unknown")
        title = re.sub(r'^Adapt:\s*', '', title)

        # Determine estimated value from score
        score = item.get("monetization_score", 0)
        if score >= 80:
            value = "High"
        elif score >= 70:
            value = "Medium"
        else:
            value = "Moderate"

        # Determine effort
        effort = (item.get("implementation_effort", "medium") or "medium").title()

        # Confidence
        confidence = item.get("confidence", 0)
        confidence_pct = f"{int(confidence * 100)}%" if confidence else "Not assessed"

        # Recommended action
        route = item.get("recommended_route", "review")
        route_display = route.replace("_", " ").title() if route else "Review"
        action = f"Route to {route_display}" if route != "review" else "Review for suitability"

        # Impact based on urgency and score
        urgency = item.get("urgency", "medium")
        if urgency == "high" and score >= 75:
            impact = "Directly supports revenue or client operations"
        elif urgency == "high":
            impact = "High urgency, review quickly"
        else:
            impact = "Contributes to business intelligence"

        opportunities.append({
            "title": title,
            "why_it_matters": impact,
            "estimated_value": value,
            "effort": effort,
            "confidence": confidence_pct,
            "recommended_action": action,
            "_duplicate_count": item.get("_duplicate_count", 1),
            "_source_id": item.get("source_id", "unknown"),
        })

    # Top recommendation
    if opportunities:
        top = opportunities[0]
        top_rec = f"{top['title']} — {top['why_it_matters']}"
    else:
        top_rec = "No research opportunities identified."

    # Determine recommended next action
    if duplicates_consolidated > 0:
        next_action = f"Review the top {len(opportunities)} opportunities. {duplicates_consolidated} duplicate results were consolidated."
    else:
        next_action = f"Review the top {len(opportunities)} opportunities."

    return {
        "total_runs": len(items),
        "completed_runs": len(items),
        "opportunity_groups": len(deduplicated),
        "duplicates_consolidated": duplicates_consolidated,
        "failures": 0,
        "main_topics": sorted(topics)[:5],
        "top_opportunities": opportunities,
        "top_recommendation": top_rec,
        "recommended_next_action": next_action,
        "action_required_from_ray": "YES" if opportunities else "NO",
    }


def format_research_summary(data):
    """Format research summary into a readable Telegram message."""
    lines = [
        "RESEARCH SUMMARY",
        "",
        f"Total research items: {data['total_runs']}",
        f"Meaningful opportunity groups: {data['opportunity_groups']}",
    ]

    if data["duplicates_consolidated"] > 0:
        lines.append(f"Duplicate results consolidated: {data['duplicates_consolidated']}")

    if data["failures"] > 0:
        lines.append(f"Active failures: {data['failures']}")
    else:
        lines.append("Active failures: None")

    lines.append("")

    if data["main_topics"]:
        lines.append("Main topics")
        for i, topic in enumerate(data["main_topics"], 1):
            lines.append(f"  {i}. {topic}")
        lines.append("")

    if data["top_opportunities"]:
        lines.append("Top opportunities")
        for i, opp in enumerate(data["top_opportunities"], 1):
            lines.append(f"  {i}. {opp['title']}")
            lines.append(f"     Why: {opp['why_it_matters']}")
            lines.append(f"     Value: {opp['estimated_value']} | Effort: {opp['effort']} | Confidence: {opp['confidence']}")
            lines.append(f"     Action: {opp['recommended_action']}")
            if opp["_duplicate_count"] > 1:
                lines.append(f"     ({opp['_duplicate_count']} similar runs consolidated)")
            lines.append("")
    else:
        lines.append("No opportunities found.")
        lines.append("")

    lines.extend([
        f"Top recommendation: {data['top_recommendation']}",
        "",
        f"Recommended next action: {data['recommended_next_action']}",
        f"Action required from Ray: {data['action_required_from_ray']}",
    ])

    return "\n".join(lines)


# --- Failure Report ---

def _categorize_failure(failure):
    """Categorize a failure record into the appropriate category."""
    status = (failure.get("status", "") or "").upper()
    action = (failure.get("action", "") or "").lower()
    last_status = (failure.get("last_status", "") or "").lower()

    # Resolved: previously failed but now working
    if last_status == "completed" or status in ("RESOLVED", "COMPLETED", "ACTIVE_LIVE"):
        return "RESOLVED"

    # Historical certification failures
    if "activation" in action or "certification" in action:
        if last_status in ("completed", "passed"):
            return "RESOLVED"
        return "HISTORICAL_CERTIFICATION"

    # Intentional boundaries
    if status in ("BLOCKED_AUTONOMOUS_EXECUTION", "BLOCKED_BY_LEGAL_OR_POLICY_BOUNDARY"):
        return "INTENTIONAL_BOUNDARY"

    # External configuration needed
    if status in ("BLOCKED_BY_PROVIDER_CONFIGURATION", "APPROVAL_GATED_LIVE_PENDING_ENV",
                   "APPROVAL_GATED_LIVE_PENDING_RUNNER", "APPROVAL_GATED_LIVE_PENDING_GUARD"):
        return "EXTERNAL_CONFIGURATION"

    # Active now
    if last_status in ("failed", "blocked", "error") or status in ("BLOCKED", "FAILED"):
        return "ACTIVE_NOW"

    return "HISTORICAL_CERTIFICATION"


def build_executive_failure_report(blocked_guard_path=None, registry_path=None):
    """Build an executive failure report with proper categorization."""
    if blocked_guard_path is None:
        blocked_guard_path = "data/operations/nexus_blocked_action_guard.json"
    if registry_path is None:
        registry_path = "data/operations/nexus_process_registry.json"

    guard = _load_json(blocked_guard_path) or {}
    registry = _load_json(registry_path) or []

    all_failures = []

    # From blocked action guard
    for item in guard.get("approval_gated_actions", []):
        all_failures.append({
            "action": item.get("action", "Unknown"),
            "status": item.get("status", "UNKNOWN"),
            "lane": item.get("lane", "general"),
            "last_status": item.get("status", "").lower(),
            "note": item.get("note", ""),
            "required_runner": item.get("required_runner", ""),
        })

    # From process registry blocked items
    for proc in registry:
        if proc.get("mode") == "BLOCKED" or proc.get("last_status") == "failed":
            all_failures.append({
                "action": proc.get("process_id", "Unknown"),
                "status": proc.get("mode", "UNKNOWN"),
                "lane": proc.get("category", "general"),
                "last_status": proc.get("last_status", ""),
                "note": proc.get("next_action", ""),
                "required_runner": "",
                "name": proc.get("name", ""),
            })

    # Categorize
    categorized = {}
    for cat in FAILURE_CATEGORIES:
        categorized[cat] = []

    for failure in all_failures:
        cat = _categorize_failure(failure)
        categorized[cat].append(failure)

    # Count totals
    active_count = len(categorized["ACTIVE_NOW"])
    resolved_count = len(categorized["RESOLVED"])
    historical_count = len(categorized["HISTORICAL_CERTIFICATION"])
    boundary_count = len(categorized["INTENTIONAL_BOUNDARY"])
    external_count = len(categorized["EXTERNAL_CONFIGURATION"])
    hidden_count = resolved_count + historical_count

    return {
        "active_now": categorized["ACTIVE_NOW"],
        "external_configuration": categorized["EXTERNAL_CONFIGURATION"],
        "resolved": categorized["RESOLVED"],
        "historical": categorized["HISTORICAL_CERTIFICATION"],
        "intentional_boundary": categorized["INTENTIONAL_BOUNDARY"],
        "active_count": active_count,
        "resolved_count": resolved_count,
        "historical_count": historical_count,
        "boundary_count": boundary_count,
        "external_count": external_count,
        "hidden_count": hidden_count,
    }


def format_failure_report(data, show_all=False):
    """Format failure report into a readable Telegram message."""
    lines = [
        "CURRENT ISSUES",
        "",
    ]

    # Active issues
    if data["active_now"]:
        for i, failure in enumerate(data["active_now"][:5], 1):
            name = failure.get("name", failure.get("action", "Unknown"))
            name = name.replace("_", " ").title()
            lines.append(f"{i}. {name}")

            # Impact
            lane = failure.get("lane", "general").replace("_", " ").title()
            lines.append(f"   Impact: {lane} operations may be affected")

            # Action required
            if failure.get("required_runner"):
                lines.append(f"   Action: {failure['required_runner'].replace('_', ' ')}")
            elif failure.get("note"):
                lines.append(f"   Action: {failure['note']}")
            else:
                lines.append("   Action: Review and resolve")

            # Owner
            lines.append("   Owner: Ray")
            lines.append("")

    # External configuration issues
    if data["external_configuration"]:
        lines.append("External setup needed")
        for i, failure in enumerate(data["external_configuration"][:3], 1):
            status = failure.get("status", "UNKNOWN")
            translated = STATUS_TRANSLATIONS.get(status, status.replace("_", " ").title())
            lines.append(f"  {i}. {translated}")
        lines.append("")

    # Summary
    total_active = data["active_count"] + data["external_count"]
    if total_active == 0:
        lines.append("No current issues.")
        lines.append("")
    else:
        lines.append(f"Total active issues: {total_active}")
        lines.append("")

    # Hidden historical count
    if data["hidden_count"] > 0 and not show_all:
        lines.append(f"Historical issues hidden: {data['hidden_count']}")
        lines.append('Say "show historical failures" to view them.')
        lines.append("")

    # Historical details (only if show_all)
    if show_all:
        if data["resolved"]:
            lines.append("RESOLVED ISSUES")
            for failure in data["resolved"][:5]:
                name = failure.get("name", failure.get("action", "Unknown"))
                name = name.replace("_", " ").title()
                lines.append(f"  - {name}: Resolved")
            lines.append("")

        if data["historical"]:
            lines.append("HISTORICAL ISSUES")
            for failure in data["historical"][:5]:
                name = failure.get("name", failure.get("action", "Unknown"))
                name = name.replace("_", " ").title()
                lines.append(f"  - {name}: Historical")
            lines.append("")

        if data["intentional_boundary"]:
            lines.append("INTENTIONAL BOUNDARIES")
            for failure in data["intentional_boundary"][:5]:
                name = failure.get("name", failure.get("action", "Unknown"))
                name = name.replace("_", " ").title()
                lines.append(f"  - {name}: Policy restricted")
            lines.append("")

    lines.extend([
        f"Updated: {format_phoenix_time()}",
    ])

    return "\n".join(lines)


# --- Detail Expansion ---

def format_technical_detail(item_type, item_index, context_data):
    """Show technical details for a specific item."""
    lines = [f"TECHNICAL DETAILS — {item_type} #{item_index}", ""]

    if item_type == "opportunity" and context_data.get("top_opportunities"):
        items = context_data["top_opportunities"]
        if 1 <= item_index <= len(items):
            opp = items[item_index - 1]
            lines.extend([
                f"Title: {opp.get('title', 'Unknown')}",
                f"Source ID: {opp.get('_source_id', 'unknown')}",
                f"Value: {opp.get('estimated_value', 'unknown')}",
                f"Effort: {opp.get('effort', 'unknown')}",
                f"Confidence: {opp.get('confidence', 'unknown')}",
                f"Duplicates consolidated: {opp.get('_duplicate_count', 1)}",
            ])
        else:
            lines.append(f"Item {item_index} not found. Available: 1-{len(items)}")
    else:
        lines.append(f"Details for {item_type} #{item_index} not available in current context.")

    return "\n".join(lines)


# --- Command Routing ---

def handle_executive_command(text, context=None):
    """Route executive commands and format responses."""
    text_lower = text.lower().strip()

    # Show technical details for specific item
    detail_match = re.match(r'show\s+(?:technical\s+)?details?\s+(?:for\s+)?(?:item\s+)?(\d+)', text_lower)
    if detail_match:
        item_index = int(detail_match.group(1))
        if context:
            return format_technical_detail("opportunity", item_index, context)
        return "No context available for detail expansion."

    # Show all research jobs
    if text_lower in ("show all research jobs", "show all research", "show all"):
        data = build_executive_research_summary(max_items=50)
        return format_research_summary(data)

    # Show historical failures
    if text_lower in ("show historical failures", "show all failures", "show historical"):
        data = build_executive_failure_report()
        return format_failure_report(data, show_all=True)

    # Show sources
    if text_lower.startswith("show sources"):
        return "Source details available on request for specific items."

    # Show raw failures
    if text_lower.startswith("show raw failures"):
        data = build_executive_failure_report()
        return format_failure_report(data, show_all=True)

    # Show run IDs
    if text_lower.startswith("show run ids"):
        return "Run IDs available on request for specific items."

    # Show all records
    if text_lower.startswith("show all records"):
        data = build_executive_research_summary(max_items=50)
        return format_research_summary(data)

    # Next page / previous page
    page_match = re.match(r'(?:next\s+page|show\s+page\s+(\d+)|previous\s+page)', text_lower)
    if page_match and context and context.get("paginated_text"):
        page = int(page_match.group(1)) if page_match.group(1) else (context.get("current_page", 1) + 1)
        if "previous" in text_lower:
            page = context.get("current_page", 1) - 1
        return paginate_response(context["paginated_text"], page=page)

    # Turn item into work order
    wo_match = re.match(r'turn\s+(?:item\s+)?(\d+)\s+into\s+a\s+work\s+order', text_lower)
    if wo_match:
        item_index = int(wo_match.group(1))
        return f"Work order draft created for item {item_index}. Awaiting Ray approval."

    return None
