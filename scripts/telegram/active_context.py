#!/usr/bin/env python3
"""
Active Context Module — Shared follow-up context for Nexus Telegram.

Saves/loads the most recent actionable context so follow-up questions
("number 2", "why is that scored that way", "turn this into a work order")
route to the right source instead of generic fallback.
"""

import re
import os
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

CONTEXT_PATH = "data/runtime/telegram_active_context.json"
WORK_ORDER_DRAFT_DIR = "reports/work_orders/drafts"
WORK_ORDER_DRAFT_LATEST = "data/runtime/work_order_draft_latest.json"

# --- Save / Load ---

def save_active_context(context):
    """Save active context to disk."""
    os.makedirs(os.path.dirname(CONTEXT_PATH), exist_ok=True)
    context["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(CONTEXT_PATH, "w") as f:
        json.dump(context, f, indent=2)
    return context


def load_active_context():
    """Load active context from disk. Returns None if not found."""
    try:
        with open(CONTEXT_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def is_context_fresh(context, now=None):
    """Check if context is within expiration window."""
    if not context:
        return False
    if now is None:
        now = datetime.now(timezone.utc)
    updated = context.get("updated_at")
    if not updated:
        return False
    try:
        updated_dt = datetime.fromisoformat(updated)
        if updated_dt.tzinfo is None:
            updated_dt = updated_dt.replace(tzinfo=timezone.utc)
        expiry = context.get("expires_after_minutes", 180)
        return (now - updated_dt) < timedelta(minutes=expiry)
    except Exception:
        return False


def _clean_html(text):
    """Remove HTML tags from text."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", str(text)).strip()


# --- Selection Detection ---

def select_context_item(context, text):
    """
    Detect which item the user is referring to.
    Returns the item dict or None.
    """
    if not context or not context.get("items"):
        return None

    text_lower = text.lower().strip()
    items = context["items"]
    last_selected = context.get("last_selected_index")

    # Direct number reference: "number 2", "option 2", "item 2", "2"
    num_match = re.search(r"(?:number|option|item|#)\s*(\d+)|^(\d+)$", text_lower)
    if num_match:
        idx = int(num_match.group(1) or num_match.group(2))
        for item in items:
            if item["index"] == idx:
                context["last_selected_index"] = idx
                save_active_context(context)
                return item
        return None

    # Ordinal reference: "first one", "second one", "third one"
    ordinals = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
                "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5}
    for word, num in ordinals.items():
        if re.search(rf"\b{word}\b", text_lower):
            for item in items:
                if item["index"] == num:
                    context["last_selected_index"] = num
                    save_active_context(context)
                    return item
            return None

    # "the best option", "top one", "best one", "highest scored"
    if re.search(r"(the\s+)?(best|top|highest|first)\s+(option|one|result|item|pick)?", text_lower):
        top = context.get("top_index", 1)
        for item in items:
            if item["index"] == top:
                context["last_selected_index"] = top
                save_active_context(context)
                return item
        return items[0] if items else None

    # "this", "that", "it" — use last selected or top
    if re.match(r"^(this|that|it|the\s+one|this\s+one|that\s+one)$", text_lower):
        if last_selected:
            for item in items:
                if item["index"] == last_selected:
                    return item
        top = context.get("top_index", 1)
        for item in items:
            if item["index"] == top:
                return item

    # "this option", "that option"
    if re.match(r"^(this|that)\s+option$", text_lower):
        if last_selected:
            for item in items:
                if item["index"] == last_selected:
                    return item
        top = context.get("top_index", 1)
        for item in items:
            if item["index"] == top:
                return item

    return None


# --- Follow-up Intent Detection ---

def detect_followup_intent(text):
    """
    Detect follow-up intent from text.
    Returns dict with intent, selected_index, confidence.
    """
    text_lower = text.lower().strip()
    context = load_active_context()

    # --- Explain score ---
    if re.search(r"why\s+is\s+(number|option|item|#)?\s*\d+\s*(scored|rated|ranked)", text_lower):
        num_match = re.search(r"\d+", text_lower)
        idx = int(num_match.group()) if num_match else None
        return {"intent": "explain_score", "selected_index": idx, "confidence": 0.95}

    if re.search(r"why\s+is\s+(this|that|it)\s*(scored|rated|ranked|so\s+high|so\s+low)", text_lower):
        item = select_context_item(context, "this") if context else None
        idx = item["index"] if item else context.get("top_index", 1) if context else 1
        return {"intent": "explain_score", "selected_index": idx, "confidence": 0.9}

    # --- Explain best ---
    if re.search(r"why\s+is\s+(this|that|it)\s+the\s+(best|top|right)", text_lower):
        item = select_context_item(context, "this") if context else None
        idx = item["index"] if item else context.get("top_index", 1) if context else 1
        return {"intent": "explain_best", "selected_index": idx, "confidence": 0.9}

    if re.search(r"why\s+(is|was)\s+(that|this)\s+the\s+best", text_lower):
        item = select_context_item(context, "that") if context else None
        idx = item["index"] if item else context.get("top_index", 1) if context else 1
        return {"intent": "explain_best", "selected_index": idx, "confidence": 0.9}

    if re.search(r"(what|why)\s+(makes?|is)\s+(this|that|it)\s+(the\s+)?(best|top|better)", text_lower):
        return {"intent": "explain_best", "selected_index": None, "confidence": 0.85}

    # --- Research deeper ---
    if re.search(r"(research|look|go)\s+(deeper|more|further|into|additional)", text_lower):
        return {"intent": "research_deeper", "selected_index": None, "confidence": 0.9}

    if re.search(r"(get|find|show)\s+(more|additional|further)\s+(details|info|information|evidence)", text_lower):
        return {"intent": "research_deeper", "selected_index": None, "confidence": 0.85}

    # --- Create work order ---
    if re.search(r"turn\s+(this|that|it)\s+into\s+a\s+work\s+order", text_lower):
        item = select_context_item(context, "this") if context else None
        idx = item["index"] if item else context.get("top_index", 1) if context else 1
        return {"intent": "create_work_order", "selected_index": idx, "confidence": 0.9}

    if re.search(r"(turn|make)\s+(?:number\s+)?(\d+)\s+into\s+a\s+work\s+order", text_lower):
        num_match = re.search(r"\d+", text_lower)
        idx = int(num_match.group()) if num_match else None
        return {"intent": "create_work_order", "selected_index": idx, "confidence": 0.95}

    if re.search(r"(create|make)\s+(a\s+)?work\s+order", text_lower):
        return {"intent": "create_work_order", "selected_index": None, "confidence": 0.8}

    # --- Schedule ---
    if re.search(r"schedule\s+(this|that|it)", text_lower):
        item = select_context_item(context, "this") if context else None
        return {"intent": "schedule", "selected_index": item["index"] if item else None, "confidence": 0.85}

    # --- Send to agent ---
    if re.search(r"send\s+(that|this|it)\s+to\s+hermes", text_lower):
        return {"intent": "send_to_hermes", "selected_index": None, "confidence": 0.9}

    if re.search(r"send\s+(that|this|it)\s+to\s+alpha", text_lower):
        return {"intent": "send_to_alpha", "selected_index": None, "confidence": 0.9}

    # --- Compare ---
    if re.search(r"compare\s+(number\s+)?(\d+)\s*(and|&|vs|versus)\s*(number\s+)?(\d+)", text_lower):
        nums = re.findall(r"\d+", text_lower)
        return {"intent": "compare", "selected_indices": [int(n) for n in nums], "confidence": 0.9}

    # --- Generic selection without explicit intent: "number 2", "option 2" ---
    num_match = re.search(r"(?:number|option|item|#)\s*(\d+)|^(\d+)$", text_lower)
    if num_match and context:
        idx = int(num_match.group(1) or num_match.group(2))
        item = select_context_item(context, text_lower)
        if item:
            # Just selected an item — explain it
            return {"intent": "explain_score", "selected_index": idx, "confidence": 0.7}

    # --- "this", "that", "it" — select the last or top item ---
    if re.match(r"^(this|that|it|the\s+one|this\s+one|that\s+one|this\s+option|that\s+option)$", text_lower):
        if context and context.get("items"):
            item = select_context_item(context, text_lower)
            if item:
                return {"intent": "explain_score", "selected_index": item["index"], "confidence": 0.7}

    return {"intent": None, "selected_index": None, "confidence": 0.0}


# --- Formatting Functions ---

def format_score_explanation(context, item):
    """Format a score explanation for an item."""
    if not item:
        return "I could not find that item in the current context."

    lines = [
        f"**{item.get('title', 'Item')}**",
        "",
        f"Score: {item.get('score', '?')}/10",
    ]

    if item.get("summary"):
        lines.append(f"Summary: {item['summary'][:200]}")

    if item.get("evidence"):
        lines.append("")
        lines.append("Positive factors:")
        for e in item["evidence"][:3]:
            lines.append(f"  - {e}")

    if item.get("risk"):
        lines.append("")
        lines.append("Risks/caveats:")
        for r in item["risk"][:2]:
            lines.append(f"  - {r}")

    # Score breakdown reasoning
    score = item.get("score", 5)
    lines.append("")
    if score >= 7:
        lines.append("Why it scored well: Strong fit, good evidence, reasonable cost/risk.")
    elif score >= 5:
        lines.append("Why it scored moderate: Decent potential but some gaps in evidence or fit.")
    else:
        lines.append("Why it scored lower: Weak fit, high cost, or limited evidence.")

    if score < 8:
        lines.append(f"What would raise the score: More proof, lower cost, or faster time to value.")

    if item.get("next_action"):
        lines.append(f"\nNext step: {item['next_action']}")

    return "\n".join(lines)


def format_best_option_explanation(context, item=None):
    """Explain why an item is the best option."""
    if not context or not context.get("items"):
        return "No active context to explain."

    if item is None:
        top_idx = context.get("top_index", 1)
        item = next((i for i in context["items"] if i["index"] == top_idx), context["items"][0])

    lines = [
        f"**Why {item.get('title', 'this')} is the top recommendation:**",
        "",
    ]

    score = item.get("score", 0)
    lines.append(f"It scored {score}/10, the highest among {len(context.get('items', []))} options.")

    if item.get("evidence"):
        lines.append("")
        lines.append("Key strengths:")
        for e in item["evidence"][:3]:
            lines.append(f"  - {e}")

    if item.get("risk"):
        lines.append("")
        lines.append("Known risks (accepted):")
        for r in item["risk"][:2]:
            lines.append(f"  - {r}")

    # Compare to others
    others = [i for i in context.get("items", []) if i["index"] != item["index"]]
    if others:
        avg_other = sum(i.get("score", 5) for i in others) / len(others)
        lines.append("")
        lines.append(f"Average score of other options: {avg_other:.1f}/10")
        lines.append(f"This option is {score - avg_other:.1f} points higher than average.")

    if item.get("next_action"):
        lines.append(f"\nRecommended action: {item['next_action']}")

    return "\n".join(lines)


def format_deeper_research(context):
    """Format a deeper research prompt based on context."""
    if not context:
        return "No active context to research deeper."

    topic = context.get("topic", context.get("query", "the topic"))
    context_type = context.get("context_type", "unknown")
    provider = context.get("provider")

    lines = [
        f"Deeper research on: {topic}",
        f"Source: {context_type} ({provider or 'internal'})",
        "",
    ]

    if context_type == "web_search" and provider:
        lines.append(f"I can search deeper using {provider.title()} for more results on this topic.")
        lines.append("Say 'confirm deeper research' to proceed, or specify what angle to explore.")
    elif context_type == "alpha_research":
        lines.append("I can expand the Alpha research brief.")
        if provider:
            lines.append(f"Live web enrichment via {provider.title()} is available.")
        lines.append("Say 'confirm deeper research' to proceed.")
    else:
        lines.append("I can investigate this further using available context.")
        lines.append("Say 'confirm deeper research' to proceed.")

    return "\n".join(lines)


def format_work_order_draft(context, item=None):
    """Create a work order draft from context."""
    if not context:
        return "No active context for work order."

    if item is None:
        last_idx = context.get("last_selected_index")
        if last_idx:
            item = next((i for i in context["items"] if i["index"] == last_idx), None)
        if not item:
            top_idx = context.get("top_index", 1)
            item = next((i for i in context["items"] if i["index"] == top_idx), context["items"][0])

    title = item.get("title", context.get("topic", "unspecified task"))
    topic = context.get("topic", "")
    score = item.get("score", "?")
    provider = context.get("provider", "internal")
    now = datetime.now(timezone.utc)

    draft = {
        "title": f"Hermes: {title[:80]}",
        "source_context": context.get("context_type", "unknown"),
        "source_topic": topic,
        "selected_item": {
            "index": item.get("index"),
            "title": item.get("title"),
            "score": item.get("score"),
        },
        "why_it_matters": item.get("summary", "")[:200],
        "score": score,
        "next_steps": item.get("next_action", "Review and approve"),
        "approval_needed": True,
        "suggested_owner": "Nexus",
        "suggested_reviewer": "Ray",
        "risk_controls": ["No external actions without Ray approval", "No spending without approval"],
        "source_provider": provider,
        "source_receipt": context.get("receipt_path"),
        "created_at": now.isoformat(),
        "status": "draft",
    }

    # Save draft
    os.makedirs(WORK_ORDER_DRAFT_DIR, exist_ok=True)
    ts = now.strftime("%Y%m%dT%H%M%SZ")
    draft_path = os.path.join(WORK_ORDER_DRAFT_DIR, f"work_order_{ts}.json")
    with open(draft_path, "w") as f:
        json.dump(draft, f, indent=2)

    # Save latest
    os.makedirs(os.path.dirname(WORK_ORDER_DRAFT_LATEST), exist_ok=True)
    with open(WORK_ORDER_DRAFT_LATEST, "w") as f:
        json.dump(draft, f, indent=2)

    # Format response
    lines = [
        "Work Order Draft Created",
        "",
        f"Title: {title[:80]}",
        f"Source: {context.get('context_type', 'unknown')} ({provider})",
        f"Focus: {item.get('title', 'top item')[:60]}",
        f"Score: {score}/10",
        f"Approval: Needed before outreach, signup, publishing, or spending.",
        f"Path: {draft_path}",
        "",
        'Say "approve work order" or "revise work order: ..."',
    ]
    return "\n".join(lines)
