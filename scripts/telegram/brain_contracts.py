#!/usr/bin/env python3
"""
Brain Contracts — Advisor (open-world) vs Command (closed-world) routing.

Core rule:
  Advisor answers the world.
  Command answers Nexus.
  Ray approves action.

Advisor = open-world thinker, researcher, explainer, strategist.
Command = closed-world Nexus operator, reports/work orders/approvals/execution.
"""

import re
from datetime import datetime, timezone

# --- Contract Definitions ---

ADVISOR = "advisor"
COMMAND = "command"

# Patterns that explicitly route to COMMAND (closed-world)
COMMAND_EXPLICIT_PATTERNS = [
    r"^command\b",
    r"^nexus\s+command\b",
    r"^command\s+bot\b",
    r"^system\s+status\b",
    r"^/report\b",
    r"^/status\b",
    r"^/daily\b",
    r"^/research\b",
    r"^/content\b",
    r"^/approvals\b",
    r"^/orders\b",
    r"^/processes\b",
    r"^/blocked\b",
    r"^/run\b",
    r"^work\s+orders?\b",
    r"^approvals?\b",
    r"^status\s+report\b",
    r"^logs?\b",
    r"^scheduler\b",
    r"^launchd\b",
    r"^database\b",
    r"^internal\s+plan\b",
    r"^create\s+nexus\s+plan\b",
    r"^map\s+this\s+into\s+nexus\b",
    r"^command\s+create\s+a?\s*nexus\s+plan\b",
    r"^command\s+map\s+this\b",
    r"^command\s+create\s+implementation\b",
    r"^command\s+turn\s+last\b",
]

# Patterns that explicitly route to ADVISOR (open-world)
ADVISOR_EXPLICIT_PATTERNS = [
    r"^advisor\b",
    r"^hermes\s+advisor\b",
    r"^alpha\b",
    r"^outside\s+opinion\b",
    r"^research\b",
    r"^explain\b",
    r"^what\s+is\b",
    r"^why\s+is\b",
    r"^how\s+does\b",
    r"^give\s+me\s+ideas\b",
    r"^pros\s+and\s+cons\b",
    r"^how\s+can\s+i\s+make\s+money\b",
    r"^how\s+can\s+i\s+make\s+money\s+in\s+\d+\s+days\b",
    r"^find\s+business\s+ideas\b",
    r"^give\s+me\s+new\s+business\s+ideas\b",
    r"^advisor\s+find\b",
    r"^advisor\s+give\b",
]

# Patterns for idea brief creation
IDEA_BRIEF_PATTERNS = [
    r"turn\s+(?:number\s+)?(\d+)\s+into\s+(?:an?\s+)?idea\s+brief",
    r"create\s+(?:an?\s+)?idea\s+brief\s+for\s+(?:number\s+)?(\d+)",
    r"send\s+(?:number\s+)?(\d+)\s+to\s+(?:nexus\s+)?command",
    r"send\s+this\s+to\s+nexus",
    r"turn\s+this\s+into\s+(?:a\s+)?nexus\s+idea",
]

# Patterns for command consuming advisor idea briefs
COMMAND_PLAN_PATTERNS = [
    r"^command\s+create\s+a?\s*nexus\s+plan\s+from\s+(?:this\s+idea|number\s+(\d+)|last\s+advisor)",
    r"^command\s+map\s+this\s+idea\s+into\s+nexus",
    r"^command\s+create\s+implementation\s+plan\s+from\s+last\s+advisor",
    r"^command\s+turn\s+last\s+advisor\s+idea\s+into\s+work\s+orders",
    r"create\s+a?\s*nexus\s+plan\s+from\s+(?:this|number\s+(\d+)|last)",
    r"(?:nexus|command)[\s,:\-]+create\s+a?\s*(?:nexus\s+)?plan\s+from\s+(?:this|this\s+idea|number\s+(\d+)|last)",
    r"(?:nexus|command)[\s,:\-]+map\s+(?:this|this\s+idea)\s+into\s+nexus",
    r"(?:nexus|command)[\s,:\-]+turn\s+(?:this|last)\s+(?:advisor\s+)?idea\s+into\s+(?:a\s+)?(?:nexus\s+)?plan",
]


def detect_brain_mode(text):
    """
    Detect whether the message should route to Advisor or Command.
    Returns (mode, explicit_match) where mode is ADVISOR or COMMAND.
    """
    t = text.lower().strip()

    # Check explicit command patterns first
    for pat in COMMAND_EXPLICIT_PATTERNS:
        if re.search(pat, t):
            return COMMAND, True

    # Check explicit advisor patterns
    for pat in ADVISOR_EXPLICIT_PATTERNS:
        if re.search(pat, t):
            return ADVISOR, True

    # Default: route to Advisor for open-world questions
    # Command only handles explicit system/internal requests
    return ADVISOR, False


def detect_idea_brief_request(text):
    """
    Check if the user wants to create an Advisor Idea Brief.
    Returns (is_brief_request, item_number_or_None).
    """
    t = text.lower().strip()
    for pat in IDEA_BRIEF_PATTERNS:
        m = re.search(pat, t)
        if m:
            try:
                idx = int(m.group(1)) if m.group(1) else None
            except (IndexError, ValueError, TypeError):
                idx = None
            return True, idx
    return False, None


def detect_command_plan_request(text):
    """
    Check if the user wants Command to create a Nexus plan from an Advisor idea.
    Returns (is_plan_request, item_number_or_None).
    """
    t = text.lower().strip()
    for pat in COMMAND_PLAN_PATTERNS:
        m = re.search(pat, t)
        if m:
            try:
                idx = int(m.group(1)) if m.group(1) else None
            except (IndexError, ValueError, TypeError):
                idx = None
            return True, idx
    return False, None


def create_idea_brief(item, topic, source_context="advisor_recommendation"):
    """
    Create an Advisor Idea Brief from a context item.
    Returns the brief dict and saves to disk.
    """
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%dT%H%M%SZ")

    brief = {
        "type": "advisor_idea_brief",
        "created_by": "hermes_advisor",
        "status": "draft",
        "idea_title": item.get("title", "Untitled idea"),
        "category": source_context,
        "summary": item.get("summary", ""),
        "why_this_idea": item.get("why", item.get("summary", "")),
        "target_customer": "Small business owners needing credit/funding guidance",
        "revenue_model": item.get("revenue_model", "$97 readiness review or consultation"),
        "estimated_cost": item.get("cost", "$0-$100"),
        "time_to_test": item.get("time_to_execute", "1-7 days"),
        "time_to_revenue": item.get("time_to_revenue", "3-14 days"),
        "pros": item.get("pros", []),
        "cons": item.get("cons", []),
        "risks": item.get("risk", item.get("risks", [])),
        "recommended_first_step": item.get("next_action", "Review and decide"),
        "nexus_handoff_request": "Create an implementation plan with work orders, schedule, dependencies, and approval gates.",
        "source_context": topic,
        "source_item_score": item.get("score", 0),
        "approval_required": True,
        "created_at": now.isoformat(),
        "status": "draft",
    }

    # Save to disk
    brief_dir = "reports/advisor_idea_briefs"
    import os
    os.makedirs(brief_dir, exist_ok=True)
    brief_path = os.path.join(brief_dir, f"advisor_idea_brief_{ts}.json")
    with open(brief_path, "w") as f:
        import json
        json.dump(brief, f, indent=2)

    return brief, brief_path


def create_command_plan(brief, topic="Advisor idea"):
    """
    Create a Nexus Command implementation plan from an Advisor Idea Brief.
    Returns the plan dict and saves to disk.
    """
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%dT%H%M%SZ")

    idea_title = brief.get("idea_title", topic)

    plan = {
        "type": "command_implementation_plan",
        "created_by": "nexus_command",
        "status": "draft",
        "source": "advisor_idea_brief",
        "source_brief_title": idea_title,
        "goal": f"Implement: {idea_title}",
        "internal_assets_needed": [
            "Offer/page or PDF",
            "Outreach script",
            "Payment/invoice method",
            "Lead tracking workflow",
            "Work order queue",
            "Approval gates",
        ],
        "work_orders_recommended": [
            {"step": 1, "title": "Finalize offer language", "status": "pending"},
            {"step": 2, "title": "Draft outreach script", "status": "pending"},
            {"step": 3, "title": "Confirm payment method", "status": "pending"},
            {"step": 4, "title": "Create lead tracking workflow", "status": "pending"},
            {"step": 5, "title": "Prepare checklist/call funnel", "status": "pending"},
            {"step": 6, "title": "Schedule 30-day review report", "status": "pending"},
        ],
        "approvals_required": [
            "Offer language",
            "Outreach script",
            "Payment method",
            "Publishing/sending",
        ],
        "estimated_cost": brief.get("estimated_cost", "$0-$100"),
        "time_to_test": brief.get("time_to_test", "1-7 days"),
        "created_at": now.isoformat(),
        "status": "draft",
    }

    # Save to disk
    plan_dir = "reports/command_plans"
    import os
    os.makedirs(plan_dir, exist_ok=True)
    plan_path = os.path.join(plan_dir, f"command_plan_{ts}.json")
    with open(plan_path, "w") as f:
        import json
        json.dump(plan, f, indent=2)

    return plan, plan_path


def format_idea_brief_response(brief, brief_path):
    """Format the Telegram response for an Idea Brief creation."""
    lines = [
        "Advisor Idea Brief Created",
        "",
        f"Title: {brief['idea_title']}",
        f"Category: {brief['category']}",
        f"Estimated cost: {brief['estimated_cost']}",
        f"Time to test: {brief['time_to_test']}",
        f"Recommended first step: {brief['recommended_first_step']}",
        f"Path: {brief_path}",
        "",
        'Say "command create a Nexus plan from this idea" to map it into work orders.',
    ]
    return "\n".join(lines)


def format_command_plan_response(plan, plan_path):
    """Format the Telegram response for a Command plan creation."""
    lines = [
        "Nexus Command — Implementation Plan Draft",
        "",
        "Source: Advisor Idea Brief",
        "",
        f"Goal: {plan['goal']}",
        "",
        "Internal Nexus assets needed:",
    ]
    for i, asset in enumerate(plan["internal_assets_needed"], 1):
        lines.append(f"  {i}. {asset}")

    lines.append("")
    lines.append("Work orders recommended:")
    for wo in plan["work_orders_recommended"]:
        lines.append(f"  {wo['step']}. {wo['title']}")

    lines.append("")
    lines.append("Approvals required:")
    for a in plan["approvals_required"]:
        lines.append(f"  - {a}")

    lines.append("")
    lines.append(f"Estimated cost: {plan['estimated_cost']}")
    lines.append(f"Time to test: {plan['time_to_test']}")
    lines.append(f"Path: {plan_path}")
    lines.append("")
    lines.append('Say "create work order for number 1" or "approve plan draft."')

    return "\n".join(lines)


def format_command_refusal():
    """Format the Command closed-world refusal for outside questions."""
    return (
        "Nexus Command — Internal Scope\n\n"
        "That information does not exist in Nexus internal records.\n\n"
        "Nexus Command only uses Nexus reports, work orders, approvals, "
        "system status, schedules, logs, database context, and approved plans.\n\n"
        "I can help with:\n"
        "1. Review Nexus reports\n"
        "2. Check current work orders\n"
        "3. Create an implementation plan\n"
        "4. Map an Advisor idea into Nexus tasks\n"
        "5. Check system status\n\n"
        "For a general or outside answer, ask Hermes Advisor.\n\n"
        "Do not save this as active context."
    )


def format_advisor_general_answer(topic):
    """Format a general open-world Advisor answer."""
    return (
        f"Hermes Advisor — Explanation\n\n"
        f"Regarding: {topic}\n\n"
        f"This is an open-world Advisor question. I can answer from general knowledge, "
        f"Nexus context, or web research.\n\n"
        f"For operational Nexus questions, ask Command directly."
    )
