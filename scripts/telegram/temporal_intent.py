#!/usr/bin/env python3
"""
Temporal Intent Parser — Time/date/scheduling language understanding for Nexus Telegram.

Handles: current time, current date, relative dates, schedule requests, timeframe recaps.
Runs before generic fallback. Does not hijack Alpha opinion or trigger web search.
"""

import re
import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Try to get local timezone, fallback to America/Phoenix (Arizona, no DST)
try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("America/Phoenix")
except ImportError:
    try:
        import tzlocal
        LOCAL_TZ = tzlocal.get_localzone()
    except Exception:
        LOCAL_TZ = timezone(timedelta(hours=-7))  # America/Phoenix UTC-7

SCHEDULE_DRAFT_DIR = "reports/scheduler/drafts"
SCHEDULE_DRAFT_PATH = "data/runtime/schedule_draft.json"

# --- Time keyword mappings ---
TIME_OF_DAY = {
    "morning": 8,
    "afternoon": 15,
    "evening": 19,
    "tonight": 19,
    "night": 20,
    "midday": 12,
    "noon": 12,
    "midnight": 0,
}

DAY_NAMES = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}
DAY_ABBREV = {k[:3]: v for k, v in DAY_NAMES.items()}


def _now():
    """Get current datetime in local timezone."""
    return datetime.now(LOCAL_TZ)


def _parse_time_string(time_str):
    """Parse '8 AM', '3:30pm', '15:00', etc. Returns hour, minute or None."""
    time_str = time_str.strip().lower()
    # Match "8 AM", "8am", "8:30 AM", "3:30pm", etc.
    m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", time_str)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    meridian = m.group(3)
    if meridian == "am":
        if hour == 12:
            hour = 0
    elif meridian == "pm":
        if hour != 12:
            hour += 12
    elif hour < 7:  # no meridian and hour is small — assume PM for 1-6
        hour += 12
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return (hour, minute)
    return None


def _next_weekday(target_dow, from_date):
    """Get next occurrence of a weekday (0=Monday)."""
    days_ahead = target_dow - from_date.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return from_date + timedelta(days=days_ahead)


def detect_temporal_intent(text):
    """
    Detect temporal intent from message text.
    Returns dict with intent, matched status, resolved times, confidence.
    """
    text_lower = text.lower().strip()
    now = _now()

    # --- CURRENT_TIME ---
    if re.match(r"^(what\s+)?(time|current\s+time|time\s+is\s+it)", text_lower):
        return {
            "intent": "CURRENT_TIME",
            "matched": True,
            "resolved_start": now.isoformat(),
            "resolved_end": None,
            "timezone": str(LOCAL_TZ),
            "confidence": 1.0,
            "needs_clarification": False,
            "clarification_question": None,
        }

    # --- CURRENT_DATE ---
    if re.match(r"^(what\s+)?(day|date|today|the\s+date)", text_lower):
        return {
            "intent": "CURRENT_DATE",
            "matched": True,
            "resolved_start": now.isoformat(),
            "resolved_end": None,
            "timezone": str(LOCAL_TZ),
            "confidence": 1.0,
            "needs_clarification": False,
            "clarification_question": None,
        }

    # --- SCHEDULE_REQUEST ---
    schedule_match = re.search(
        r"(schedule|remind\s+me|put\s+(this|it)\s+on|follow\s+up|set\s+a?\s*reminder|make\s+(this|it)\s+due)",
        text_lower,
    )
    if schedule_match:
        # Extract time reference
        time_ref = re.search(
            r"(today|tomorrow|yesterday|next\s+week|last\s+week|this\s+week|"
            r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
            r"morning|afternoon|evening|tonight|midday|noon|"
            r"\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
            text_lower,
        )
        resolved = _resolve_time_reference(time_ref.group(1) if time_ref else None, now)

        # Try to identify what "this" refers to
        task_ref = _identify_task_reference(text_lower)

        if not task_ref:
            return {
                "intent": "SCHEDULE_REQUEST",
                "matched": True,
                "resolved_start": resolved["start"].isoformat() if resolved["start"] else None,
                "resolved_end": None,
                "timezone": str(LOCAL_TZ),
                "confidence": 0.8,
                "needs_clarification": True,
                "clarification_question": "What should I schedule for " + (resolved["label"] or "that time") + "?",
                "task_reference": None,
            }

        return {
            "intent": "SCHEDULE_REQUEST",
            "matched": True,
            "resolved_start": resolved["start"].isoformat() if resolved["start"] else None,
            "resolved_end": None,
            "timezone": str(LOCAL_TZ),
            "confidence": 0.9,
            "needs_clarification": False,
            "clarification_question": None,
            "task_reference": task_ref,
        }

    # --- DEADLINE_OR_DUE_DATE ---
    deadline_match = re.search(
        r"(make\s+(this|it)\s+due|set\s+deadline|due\s+(date\s+)?(is\s+)?|deadline\s+(is\s+)?|needs?\s+to\s+be\s+done)",
        text_lower,
    )
    if deadline_match:
        time_ref = re.search(
            r"(today|tomorrow|yesterday|next\s+week|last\s+week|this\s+week|"
            r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
            r"morning|afternoon|evening|tonight|"
            r"\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
            text_lower,
        )
        resolved = _resolve_time_reference(time_ref.group(1) if time_ref else None, now)
        task_ref = _identify_task_reference(text_lower)
        return {
            "intent": "DEADLINE",
            "matched": True,
            "resolved_start": resolved["start"].isoformat() if resolved["start"] else None,
            "resolved_end": None,
            "timezone": str(LOCAL_TZ),
            "confidence": 0.85,
            "needs_clarification": not bool(task_ref),
            "clarification_question": "What should the deadline apply to?" if not task_ref else None,
            "task_reference": task_ref,
        }

    # --- RECAP_BY_TIMEFRAME ---
    recap_match = re.search(
        r"(what\s+(happened|changed|did|was|went)\s+(today|yesterday|tomorrow|this\s+week|last\s+week|this\s+morning|tonight|this\s+month|last\s+month))"
        r"|"
        r"(what\s+(happened|changed|did)\s+(today|yesterday|this\s+week|last\s+week))"
        r"|"
        r"(summarize|recap|overview)\s+(today|yesterday|this\s+week|last\s+week)",
        text_lower,
    )
    if recap_match:
        # Find the first non-None group that is a timeframe
        timeframe = "today"
        for g in [3, 6, 8]:
            try:
                val = recap_match.group(g)
                if val and val not in (None, "happened", "changed", "did", "was", "went", "summarize", "recap", "overview"):
                    timeframe = val
                    break
            except (IndexError, TypeError):
                pass
        resolved = _resolve_time_reference(timeframe, now)
        return {
            "intent": "RECAP",
            "matched": True,
            "resolved_start": resolved["start"].isoformat() if resolved["start"] else now.isoformat(),
            "resolved_end": resolved["end"].isoformat() if resolved.get("end") else now.isoformat(),
            "timezone": str(LOCAL_TZ),
            "confidence": 0.85,
            "needs_clarification": False,
            "clarification_question": None,
            "timeframe": timeframe,
        }

    # --- RELATIVE_DATE_CONTEXT (standalone: "yesterday", "tomorrow", etc.) ---
    # Must check before PLAN to avoid "what is tomorrow" matching PLAN
    relative_match = re.match(
        r"^(what\s+(is|'?s)\s+)?(yesterday|tomorrow|next\s+week|last\s+week|this\s+week|"
        r"this\s+morning|tonight|later\s+today|next\s+month|last\s+month|today)$",
        text_lower,
    )
    if relative_match:
        timeframe = relative_match.group(3) or relative_match.group(1) or text_lower
        resolved = _resolve_time_reference(timeframe, now)
        return {
            "intent": "RELATIVE_DATE",
            "matched": True,
            "resolved_start": resolved["start"].isoformat() if resolved["start"] else now.isoformat(),
            "resolved_end": resolved["end"].isoformat() if resolved.get("end") else None,
            "timezone": str(LOCAL_TZ),
            "confidence": 0.95,
            "needs_clarification": False,
            "clarification_question": None,
            "timeframe": timeframe,
        }

    # --- PLAN_BY_TIMEFRAME ---
    plan_match = re.search(
        r"(what\s+(should|do|is|can|would)|plan|focus|agenda|priorities|schedule)\s*"
        r"(today|tomorrow|yesterday|this\s+week|next\s+week|this\s+morning|tonight|this\s+afternoon)?",
        text_lower,
    )
    if plan_match:
        timeframe = plan_match.group(2) or "today"
        resolved = _resolve_time_reference(timeframe, now)
        return {
            "intent": "PLAN",
            "matched": True,
            "resolved_start": resolved["start"].isoformat() if resolved["start"] else now.isoformat(),
            "resolved_end": resolved["end"].isoformat() if resolved.get("end") else None,
            "timezone": str(LOCAL_TZ),
            "confidence": 0.8,
            "needs_clarification": False,
            "clarification_question": None,
            "timeframe": timeframe,
        }

    # No temporal intent matched
    return {
        "intent": None,
        "matched": False,
        "resolved_start": None,
        "resolved_end": None,
        "timezone": str(LOCAL_TZ),
        "confidence": 0.0,
        "needs_clarification": False,
        "clarification_question": None,
    }


def _resolve_time_reference(ref, now):
    """Resolve a time reference string to concrete start/end datetimes."""
    if not ref:
        return {"start": now, "end": None, "label": "now"}

    ref = ref.lower().strip()

    # Today
    if ref == "today":
        return {"start": now, "end": now.replace(hour=23, minute=59), "label": "today"}

    # Tomorrow
    if ref == "tomorrow":
        day = now + timedelta(days=1)
        return {"start": day.replace(hour=8, minute=0, second=0, microsecond=0),
                "end": day.replace(hour=23, minute=59),
                "label": "tomorrow"}

    # Yesterday
    if ref == "yesterday":
        day = now - timedelta(days=1)
        return {"start": day.replace(hour=0, minute=0, second=0, microsecond=0),
                "end": day.replace(hour=23, minute=59),
                "label": "yesterday"}

    # This week
    if ref == "this week":
        start = now - timedelta(days=now.weekday())
        end = start + timedelta(days=6, hours=23, minutes=59)
        return {"start": start.replace(hour=0, minute=0, second=0, microsecond=0),
                "end": end,
                "label": "this week"}

    # Next week
    if ref == "next week":
        start = now + timedelta(days=7 - now.weekday())
        end = start + timedelta(days=6, hours=23, minutes=59)
        return {"start": start.replace(hour=8, minute=0, second=0, microsecond=0),
                "end": end,
                "label": "next week"}

    # Last week
    if ref == "last week":
        start = now - timedelta(days=now.weekday() + 7)
        end = start + timedelta(days=6, hours=23, minutes=59)
        return {"start": start.replace(hour=0, minute=0, second=0, microsecond=0),
                "end": end,
                "label": "last week"}

    # This morning / tonight / later today
    if ref in ("this morning", "tonight", "later today"):
        hour = TIME_OF_DAY.get(ref, 8)
        return {"start": now.replace(hour=hour, minute=0, second=0, microsecond=0),
                "end": now.replace(hour=hour + 4, minute=59) if hour + 4 <= 23 else now.replace(hour=23, minute=59),
                "label": ref}

    # Next month / last month
    if ref == "next month":
        if now.month == 12:
            start = now.replace(year=now.year + 1, month=1, day=1, hour=8, minute=0, second=0, microsecond=0)
        else:
            start = now.replace(month=now.month + 1, day=1, hour=8, minute=0, second=0, microsecond=0)
        return {"start": start, "end": None, "label": "next month"}

    if ref == "last month":
        if now.month == 1:
            start = now.replace(year=now.year - 1, month=12, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start = now.replace(month=now.month - 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return {"start": start, "end": None, "label": "last month"}

    # Named weekday
    dow = DAY_NAMES.get(ref) or DAY_ABBREV.get(ref)
    if dow is not None:
        target = _next_weekday(dow, now)
        return {"start": target.replace(hour=8, minute=0, second=0, microsecond=0),
                "end": target.replace(hour=23, minute=59),
                "label": ref}

    # Time of day
    if ref in TIME_OF_DAY:
        hour = TIME_OF_DAY[ref]
        return {"start": now.replace(hour=hour, minute=0, second=0, microsecond=0),
                "end": now.replace(hour=min(hour + 4, 23), minute=59),
                "label": ref}

    # Explicit time string like "8 AM", "3:30pm"
    parsed_time = _parse_time_string(ref)
    if parsed_time:
        hour, minute = parsed_time
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return {"start": target,
                "end": target + timedelta(hours=1),
                "label": ref}

    return {"start": now, "end": None, "label": ref}


def _identify_task_reference(text_lower):
    """Try to identify what 'this' refers to in a schedule request."""
    # Check conversation context for last topic/recommendation
    ctx_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "runtime", "telegram_conversation_context.json")
    try:
        with open(ctx_path) as f:
            ctx = json.load(f)
        chat_ctx = ctx.get("1288928049", {})

        # Check if there's a clear topic reference in the text
        if "that" in text_lower or "this" in text_lower:
            # Use last alpha recommendation
            recs = chat_ctx.get("last_alpha_recommendations", [])
            if recs:
                return f"last recommendation: {recs[0]['title'][:60]}"

            # Use last topic
            last_topic = chat_ctx.get("last_topic")
            if last_topic:
                return f"last topic: {last_topic[:60]}"

            # Use last work order
            wo = chat_ctx.get("last_work_order_path")
            if wo:
                return f"last work order: {wo}"

    except Exception:
        pass

    return None


def format_time_response(intent_result):
    """Format a time/date intent result for Telegram display."""
    now = _now()
    intent = intent_result.get("intent")

    if intent == "CURRENT_TIME":
        time_str = now.strftime("%-I:%M %p")
        tz_name = str(LOCAL_TZ).split("/")[-1].replace("_", " ") if "/" in str(LOCAL_TZ) else str(LOCAL_TZ)
        return f"Ray, it is {time_str} in {tz_name}. Nexus is running."

    elif intent == "CURRENT_DATE":
        date_str = now.strftime("%A, %B %-d, %Y")
        return f"Today is {date_str}."

    elif intent == "RELATIVE_DATE":
        resolved = intent_result.get("resolved_start")
        timeframe = intent_result.get("timeframe", "that day")
        if resolved:
            dt = datetime.fromisoformat(resolved)
            date_str = dt.strftime("%A, %B %-d, %Y")
            return f"{timeframe.title()} is {date_str}."
        return f"I resolved {timeframe} but could not format the date."

    elif intent == "RECAP":
        timeframe = intent_result.get("timeframe", "today")
        start = intent_result.get("resolved_start")
        end = intent_result.get("resolved_end")
        return _build_recap(timeframe, start, end)

    elif intent == "PLAN":
        timeframe = intent_result.get("timeframe", "today")
        return _build_plan(timeframe, intent_result)

    elif intent == "SCHEDULE_REQUEST":
        return _build_schedule_response(intent_result)

    elif intent == "DEADLINE":
        return _build_deadline_response(intent_result)

    return "I understand the timeframe but need more context."


def _build_recap(timeframe, start_str, end_str):
    """Build a recap from local reports/receipts."""
    lines = [f"Recap for {timeframe}:", ""]

    # Check recent receipts
    receipt_dir = "reports/telegram/receipts"
    recent_files = []
    try:
        if os.path.exists(receipt_dir):
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            for root, dirs, files in os.walk(receipt_dir):
                for f in files:
                    if f.endswith(".json"):
                        fp = os.path.join(root, f)
                        try:
                            mtime = datetime.fromtimestamp(os.path.getmtime(fp), tz=timezone.utc)
                            if mtime > cutoff:
                                recent_files.append(fp)
                        except Exception:
                            pass
    except Exception:
        pass

    if recent_files:
        lines.append(f"Recent activity ({len(recent_files)} receipts in last 24h):")
        for fp in sorted(recent_files)[-5:]:
            fname = os.path.basename(fp)
            lines.append(f"  - {fname[:50]}")
    else:
        lines.append("No recent receipts found in last 24 hours.")

    # Check recent commits
    try:
        import subprocess
        result = subprocess.run(
            ["git", "log", "--oneline", "-5", "--since=24 hours ago"],
            capture_output=True, text=True, timeout=5,
            cwd=os.path.join(os.path.dirname(__file__), "..", "..")
        )
        if result.stdout.strip():
            lines.append("")
            lines.append("Recent commits:")
            for line in result.stdout.strip().split("\n")[:3]:
                lines.append(f"  - {line[:60]}")
    except Exception:
        pass

    # Check current state
    try:
        with open("reports/runtime/nexus_anytime_operator_report_latest.json") as f:
            r = json.load(f)
        score = r.get("system_status", {}).get("active_os_score", "?")
        approvals = r.get("approval_queue", {}).get("count", 0)
        lines.append(f"\nSystem: {score}/100, {approvals} approvals pending")
    except Exception:
        pass

    lines.append("\nNo web search used — this is from local Nexus context.")
    return "\n".join(lines)


def _build_plan(timeframe, intent_result):
    """Build a plan/priorities list for the timeframe."""
    lines = [f"Plan for {timeframe}:", ""]

    # Get current priorities from context
    try:
        with open("reports/runtime/nexus_anytime_operator_report_latest.json") as f:
            r = json.load(f)
        approvals = r.get("approval_queue", {}).get("count", 0)
    except Exception:
        approvals = 0

    priorities = []
    if approvals > 0:
        priorities.append(f"Review {approvals} pending approval(s)")

    # Check shared recommendations
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "recommendations"))
        from recommendation_engine import get_top_recommendations
        recs = get_top_recommendations(n=3)
        for r in recs:
            priorities.append(f"{r['title'][:50]} (score: {r['composite_score']})")
    except Exception:
        pass

    if not priorities:
        priorities.append("Ask Hermes for priorities: 'hermes what should we do next?'")

    for i, p in enumerate(priorities[:5], 1):
        lines.append(f"  {i}. {p}")

    return "\n".join(lines)


def _build_schedule_response(intent_result):
    """Build a schedule draft response."""
    resolved = intent_result.get("resolved_start")
    task_ref = intent_result.get("task_reference")
    needs_clarification = intent_result.get("needs_clarification", False)

    if needs_clarification:
        question = intent_result.get("clarification_question", "What should I schedule?")
        return question

    if not resolved:
        return "I could not resolve the time. Try 'schedule this for 8 AM' or 'remind me tomorrow'."

    dt = datetime.fromisoformat(resolved)
    when_str = dt.strftime("%A, %B %-d at %-I:%M %p")

    # Create schedule draft
    draft = {
        "task": task_ref or "unspecified task",
        "when": resolved,
        "when_display": when_str,
        "created_at": _now().isoformat(),
        "status": "draft",
        "source": "telegram_schedule_request",
    }

    # Save draft
    os.makedirs(SCHEDULE_DRAFT_DIR, exist_ok=True)
    ts = _now().strftime("%Y%m%dT%H%M%SZ")
    draft_path = os.path.join(SCHEDULE_DRAFT_DIR, f"draft_{ts}.json")
    try:
        with open(draft_path, "w") as f:
            json.dump(draft, f, indent=2)
    except Exception:
        pass

    # Also save to runtime
    try:
        os.makedirs(os.path.dirname(SCHEDULE_DRAFT_PATH), exist_ok=True)
        with open(SCHEDULE_DRAFT_PATH, "w") as f:
            json.dump(draft, f, indent=2)
    except Exception:
        pass

    lines = [
        "Schedule Draft",
        "",
        f"Task: {task_ref or 'unspecified task'}",
        f"When: {when_str}",
        f"Source: last recommendation / conversation context",
        f"Approval: Needed before external action",
        "",
        'Say "confirm schedule" to save it.',
    ]
    return "\n".join(lines)


def _build_deadline_response(intent_result):
    """Build a deadline draft response."""
    resolved = intent_result.get("resolved_start")
    task_ref = intent_result.get("task_reference")
    needs_clarification = intent_result.get("needs_clarification", False)

    if needs_clarification:
        return intent_result.get("clarification_question", "What should the deadline apply to?")

    if not resolved:
        return "I could not resolve the deadline date."

    dt = datetime.fromisoformat(resolved)
    when_str = dt.strftime("%A, B %-d")

    lines = [
        "Deadline Draft",
        "",
        f"Task: {task_ref}",
        f"Due: {when_str}",
        "Approval: Needed before external action",
    ]
    return "\n".join(lines)
