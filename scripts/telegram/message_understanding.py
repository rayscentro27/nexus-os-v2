#!/usr/bin/env python3
"""
Structured Message Understanding — Production routing layer.

Classifies incoming messages into structured intent families with role detection,
follow-up detection, and evidence requirements.
"""

import re
from datetime import datetime


def understand_message(text, active_context=None, pending_action=None):
    """
    Produce a structured understanding of the user's message.
    Returns a dict with normalized fields for routing.
    """
    raw = text.strip()
    normalized = raw.lower().strip()

    # --- Explicit role detection ---
    explicit_role = None
    stripped = normalized
    # Handle: "Alpha,", "Alpha:", "Alpha -", "@alpha", "ALPHA", with any trailing punctuation
    role_match = re.match(r"^(?:@)?(alpha|hermes|nexus)\s*[,:\-]?\s*", normalized)
    if role_match:
        explicit_role = role_match.group(1)
        stripped = normalized[role_match.end():]

    # --- Pending action check (highest priority) ---
    if _is_confirm(normalized):
        if pending_action:
            return {
                "raw_text": raw,
                "normalized_text": normalized,
                "explicit_role": explicit_role,
                "intent_family": "pending_action",
                "is_followup": True,
                "followup_type": "confirm",
                "needs_external_evidence": False,
                "time_sensitive": False,
                "risk_level": "low",
                "confidence": 0.95,
            }
        else:
            # Confirm without pending action — still route as pending_action
            # so the router can give a context-aware "no pending action" message
            return {
                "raw_text": raw,
                "normalized_text": normalized,
                "explicit_role": explicit_role,
                "intent_family": "pending_action",
                "is_followup": True,
                "followup_type": "confirm",
                "needs_external_evidence": False,
                "time_sensitive": False,
                "risk_level": "low",
                "confidence": 0.95,
            }

    # --- Deterministic slash commands ---
    if normalized.startswith("/"):
        return {
            "raw_text": raw,
            "normalized_text": normalized,
            "explicit_role": explicit_role,
            "intent_family": "deterministic_command",
            "is_followup": False,
            "followup_type": "none",
            "needs_external_evidence": False,
            "time_sensitive": False,
            "risk_level": "low",
            "confidence": 1.0,
        }

    # --- Active context follow-ups ---
    followup = _detect_followup(normalized, active_context)
    if followup:
        return {
            "raw_text": raw,
            "normalized_text": normalized,
            "explicit_role": explicit_role,
            "intent_family": "active_context_followup",
            "is_followup": True,
            "followup_type": followup,
            "needs_external_evidence": False,
            "time_sensitive": False,
            "risk_level": "low",
            "confidence": 0.9,
        }

    # --- Temporal intelligence ---
    if _is_temporal(normalized):
        return {
            "raw_text": raw,
            "normalized_text": normalized,
            "explicit_role": explicit_role,
            "intent_family": "temporal",
            "is_followup": False,
            "followup_type": "none",
            "needs_external_evidence": False,
            "time_sensitive": True,
            "risk_level": "low",
            "confidence": 0.9,
        }

    # --- Intent family classification ---
    # Classify on stripped text (without role prefix) so "Alpha, make money" → money_plan
    intent = _classify_intent_family(stripped, explicit_role)
    needs_web = _needs_external_evidence(stripped, intent)

    return {
        "raw_text": raw,
        "normalized_text": normalized,
        "explicit_role": explicit_role,
        "intent_family": intent,
        "is_followup": False,
        "followup_type": "none",
        "needs_external_evidence": needs_web,
        "time_sensitive": False,
        "risk_level": _assess_risk(normalized),
        "confidence": 0.8,
    }


# --- Internal helpers ---

def _is_confirm(text):
    """Check if text is a confirm/yes pattern."""
    t = text.strip()
    # Only match if it's JUST a confirm word, not part of a longer sentence
    if re.match(r"^(confirm|yes|go\s*ahead|proceed|do\s*it|ok|yeah|yep|y)$", t):
        return True
    return False


def _is_temporal(text):
    """Check if text is a time/date/schedule question."""
    t = text.strip()
    # Direct time/date questions
    if re.match(r"^(what\s+time|what\s+day|what\s+date|what\s+day\s+is\s+it|what\s+time\s+is\s+it)", t):
        return True
    if re.match(r"^(today|tomorrow|yesterday|tonight|this\s+morning|this\s+afternoon|this\s+evening)", t):
        return True
    if re.match(r"^(next\s+week|next\s+month|this\s+week|this\s+month)", t):
        return True
    # Schedule commands
    if re.match(r"^(schedule|remind|set\s+a\s+reminder|block\s+off)", t):
        return True
    # Recap/plan
    if re.match(r"^(recap|what\s+happened|what\s+did|plan\s+for|focus\s+for|agenda\s+for|priorities\s+for)", t):
        return True
    # "today" used with time verbs ONLY — not with business verbs
    if "today" in t:
        # If it has business/money verbs, it's NOT temporal
        if re.search(r"(make|get|earn|sell|close|revenue|income|cash|paid|client|customer|money|pricing|monetiz|fund|credit|review|call|dm|outreach|post|plan|strategy|what\s+should|give\s+me|priorities|focus|action)", t):
            return False
        # If it has time verbs, it IS temporal
        if re.search(r"(schedule|remind|what|focus|priorities|agenda|recap|happen|time|day)", t):
            return True
    return False


def _detect_followup(text, active_context):
    """Detect active context follow-up types."""
    t = text.strip()

    # --- Create work order (check BEFORE number selection to avoid "turn number 2" → select_item) ---
    if re.search(r"turn\s+(this|that|it)\s+into\s+a\s+work\s+order", t):
        return "create_work_order"
    if re.search(r"(turn|make)\s+(?:number\s+)?(\d+)\s+into\s+a\s+work\s+order", t):
        return "create_work_order"
    if re.search(r"(create|make)\s+(a\s+)?work\s+order", t):
        return "create_work_order"

    # --- Research deeper (check before number selection) ---
    if re.search(r"(research|look|go)\s+(deeper|more|further|into|additional)", t):
        return "research_deeper"
    if re.search(r"(get|find|show)\s+(more|additional|further)\s+(details|info|information|evidence)", t):
        return "research_deeper"

    # --- Explain score (check before number selection) ---
    if re.search(r"why\s+is\s+(number|option|item)?\s*\d+\s*(scored|rated|ranked)", t):
        return "explain_score"
    if re.search(r"why\s+is\s+(this|that|it)\s*(scored|rated|ranked|so\s+high|so\s+low)", t):
        return "explain_score"

    # --- Explain best ---
    if re.search(r"why\s+is\s+(this|that|it)\s+the\s+(best|top|right)", t):
        return "explain_best"
    if re.search(r"why\s+(is|was)\s+(that|this)\s+the\s+best", t):
        return "explain_best"
    if re.search(r"(what|why)\s+(makes?|is)\s+(this|that|it)\s+(the\s+)?(best|top|better)", t):
        return "explain_best"
    if re.match(r"^(what\s+is\s+the\s+best|best\s+option|top\s+option|best\s+one|top\s+one)", t):
        return "explain_best"

    # --- Challenge / compare to outside (check BEFORE number selection) ---
    if re.search(r"(challenge|critique|improve|better\s+than|what.s\s+better|what.s\s+missing|compare\s+to\s+outside|is\s+there\s+a\s+better|review\s+nexus|add\s+to\s+nexus|what\s+can\s+we\s+add)", t):
        return "challenge"
    if re.search(r"(based\s+on\s+)?(?:nexus\s+)?(?:option|number|#)\s*\d+.*?(better|improve|challenge|compare|outside)", t):
        return "challenge"

    # --- Explicit item selection ( AFTER work order, research deeper, explain, challenge) ---
    num = re.search(r"(?:number|option|item|#)\s*(\d+)|^(\d+)$", t)
    if num:
        return "select_item"

    # Ordinals
    if re.search(r"\b(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th)\s+(one|option|item)?", t):
        return "select_item"

    # --- Schedule ---
    if re.search(r"schedule\s+(this|that|it)", t):
        return "schedule"

    # --- Send to agent ---
    if re.search(r"send\s+(that|this|it)\s+to\s+(hermes|alpha)", t):
        return "send_to_agent"

    # --- Compare ---
    if re.search(r"compare\s+(number\s+)?(\d+)\s*(and|&|vs|versus)\s*(number\s+)?(\d+)", t):
        return "compare"

    # Pronouns referring to context
    if re.match(r"^(this|that|it|the\s+one|this\s+one|that\s+one|this\s+option|that\s+option)$", t):
        if active_context and active_context.get("items"):
            return "select_item"

    return None


def _classify_intent_family(text, explicit_role):
    """Classify the primary intent family."""
    t = text

    # --- Money / revenue ---
    if re.search(r"(make\s+money|get\s+paid|revenue|income|earn|cash\s+today|close\s+a\s+deal|sell|pricing|monetiz)", t):
        if re.search(r"(research|search|find|look\s+up|current|latest|web|internet)", t):
            return "money_research"
        return "money_plan"

    # --- Client acquisition ---
    if re.search(r"(client|customer|lead|acquisition|outreach|prospect|pitch|close|deal|pipeline)", t):
        if re.search(r"(research|search|find|look\s+up|current|latest|web)", t):
            return "client_research"
        return "client_acquisition"

    # --- Business strategy ---
    if re.search(r"(strategy|plan|growth|scale|expand|pivot|direction|roadmap|priority|focus|what\s+should)", t):
        return "business_strategy"

    # --- Implementation ---
    if re.search(r"(implement|build|create|set\s+up|configure|deploy|launch|ship|connect|integrate)", t):
        return "implementation_plan"

    # --- Web research (explicit) ---
    if re.search(r"(search\s+the\s+web|search\s+web|look\s+up\s+current|find\s+current|what\s+are\s+the\s+best|research\s+current|latest\s+info)", t):
        return "web_research"
    if re.search(r"(hermes\s+)?(search|research|look\s+up|find)\s+(the\s+web\s+for|current|latest|best|top)", t):
        return "web_research"
    # Standalone "research [topic]" — not "research deeper" (which is a followup)
    if re.match(r"^research\s+\w", t) and not re.search(r"research\s+(deeper|more|further)", t):
        return "web_research"

    # --- Opinion / advice ---
    if re.search(r"(what\s+do\s+you\s+think|should\s+we|what\s+do\s+you\s+recommend|what\s+should\s+we|advise|suggest|opinion|perspective)", t):
        return "opinion"

    # --- Critique / challenge ---
    if re.search(r"(challenge|critique|criticize|what.s\s+wrong|what.s\s+missing|risk|downside|devil.s\s+advocate|pros?\s+and\s+cons?|gap)", t):
        return "critique"

    # --- Deeper research / investigation (outside perspective) ---
    if re.search(r"(deeper\s+research|do\s+deeper|look\s+deeper|investigate\s+deeper|more\s+research)", t):
        return "opinion"

    # --- Compare ---
    if re.search(r"(compare|versus|vs\.?|better\s+than|difference\s+between|which\s+is)", t):
        return "compare_options"

    # --- Work order ---
    if re.search(r"(create\s+a\s+task|make\s+this\s+a\s+task|work\s+order|assign|add\s+to\s+backlog)", t):
        return "work_order_request"

    # --- Schedule ---
    if re.search(r"(schedule|remind|calendar|block\s+off|set\s+a\s+reminder)", t):
        return "schedule_request"

    # --- System status ---
    if re.search(r"(status|report|what\s+happened|what.s\s+going\s+on|health|heartbeat|score)", t):
        return "system_status"

    # --- Greeting ---
    if re.search(r"^(hi|hello|hey|yo|good\s+(morning|afternoon|evening)|how\s+are\s+you|what.s\s+up)", t):
        return "greeting"

    # --- Help ---
    if re.match(r"^(help|commands|what\s+can\s+you\s+do|menu)", t):
        return "help"

    return "unknown"


def _needs_external_evidence(text, intent_family):
    """Determine if this message needs web search."""
    t = text
    # Explicit web research requests
    if intent_family in ("web_research", "money_research", "client_research"):
        return True
    # Explicit search verbs
    if re.search(r"(search\s+the\s+web|search\s+web|look\s+up\s+current|find\s+current|latest|current\s+info|what\s+are\s+the\s+best)", t):
        return True
    # "alpha research ..." with web intent
    if re.search(r"alpha\s+research\s+", t):
        return True
    return False


def _assess_risk(text):
    """Assess risk level of the message."""
    t = text
    if re.search(r"(delete|remove|destroy|cancel|purge|wipe|shutdown|emergency)", t):
        return "high"
    if re.search(r"(charge|pay|purchase|buy|subscribe|send\s+money|transfer|invest|trade)", t):
        return "medium"
    return "low"
