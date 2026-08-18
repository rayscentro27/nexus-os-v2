"""Conversational Front Brain for Nexus Hermes.

Layer 1 of the two-layer agent architecture:
  - Understands meaning, context, references, and intent
  - Classifies mode: conversation | advisory | operational_read | governed_action
  - Selects certified capabilities when operational access is needed
  - Never executes tools directly — only interprets and classifies

Layer 2 (existing governed engine) handles:
  - Certified capability execution
  - Authorization, confirmation, idempotency
  - Deterministic validation
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

# ─── Model Configuration ──────────────────────────────────

HERMES_MODEL = os.getenv("HERMES_MODEL", "openai/gpt-4o-mini")
MODEL_TEMPERATURE = 0.3
MODEL_MAX_TOKENS = 512
MODEL_TIMEOUT = 30

# ─── Certified Capability Catalog ─────────────────────────
# Maps natural language to certified capabilities.
# The LLM selects from this catalog; deterministic code validates.

CERTIFIED_READS = {
    "get_client_count": {
        "description": "How many clients GoClear has, active/onboarding/inactive counts",
        "positive_examples": [
            "How many clients do we have?",
            "Client count",
            "How many active clients?",
            "What's our client total?",
        ],
        "negative_examples": [
            "How can we get more clients?",
            "Client acquisition plan",
        ],
    },
    "get_system_status": {
        "description": "Current running processes, system health, what's active on Nexus",
        "positive_examples": [
            "What's running on Nexus?",
            "System status report",
            "What processes are active?",
            "What is the current health of Nexus?",
        ],
        "negative_examples": [
            "What failed today?",
            "Process failures",
        ],
    },
    "get_failure_report": {
        "description": "Recent failures, errors, broken processes",
        "positive_examples": [
            "What failed today?",
            "Are there any recent system failures?",
            "What's broken?",
            "Recent errors",
        ],
        "negative_examples": [
            "System status",
            "What's running?",
        ],
    },
    "get_alpha_status": {
        "description": "Alpha agent's current status and activity",
        "positive_examples": [
            "What is Alpha's status?",
            "What is Alpha doing?",
            "Alpha research status",
        ],
        "negative_examples": [
            "Trading status",
            "System status",
        ],
    },
    "process_status": {
        "description": "Process definitions, runs, scheduling status from Supabase",
        "positive_examples": [
            "Show me process status",
            "What processes are defined?",
            "Process run history",
        ],
        "negative_examples": [
            "What's running on the system?",
            "System health",
        ],
    },
    "process_failures": {
        "description": "Failed process runs from Supabase (FAILED, BLOCKED, TIMED_OUT)",
        "positive_examples": [
            "What processes failed recently?",
            "Process failure report",
            "Blocked processes",
        ],
        "negative_examples": [
            "System failures",
            "What's broken?",
        ],
    },
    "research_history": {
        "description": "Recent research runs and results from Supabase",
        "positive_examples": [
            "Show me the latest research activity",
            "What research has been done?",
            "Research runs",
        ],
        "negative_examples": [
            "Alpha status",
            "Research strategy",
        ],
    },
    "opportunities": {
        "description": "Business opportunities from Supabase",
        "positive_examples": [
            "What opportunities do we have?",
            "Show me business opportunities",
            "Current opportunities",
        ],
        "negative_examples": [
            "How to find clients",
            "Revenue plan",
        ],
    },
    "trading_status": {
        "description": "Oanda practice trading engine status",
        "positive_examples": [
            "What is the current trading-system status?",
            "Trading status",
            "Oanda status",
        ],
        "negative_examples": [
            "Alpha status",
            "System status",
        ],
    },
    "pending_approvals": {
        "description": "Items in Ray's review queue awaiting approval",
        "positive_examples": [
            "What approvals are waiting for me?",
            "Pending approvals",
            "What needs my review?",
        ],
        "negative_examples": [
            "Approved items",
            "Review history",
        ],
    },
    "BUSINESS_LOOP_STATUS": {"description": "Current certified business-loop state, last run, verifier, and next action", "positive_examples": ["What is the status of my business loops?"], "negative_examples": []},
    "BUSINESS_OPPORTUNITIES": {"description": "Current business opportunities classified as ACCEPT, WATCH, or REJECT", "positive_examples": ["Which opportunities are ACCEPT or WATCH?"], "negative_examples": []},
    "RESEARCH_HISTORY": {"description": "Most recent bounded Alpha research session and query history", "positive_examples": ["What research ran most recently?"], "negative_examples": []},
    "AI_COST_SUMMARY": {"description": "Current deterministic versus AI execution, tokens, and provider cost", "positive_examples": ["What is the current AI cost?"], "negative_examples": []},
    "PAYMENT_GATE": {"description": "Current Stripe/payment readiness gate and safety status", "positive_examples": ["What is the current payment gate?", "What is the status of Stripe?"], "negative_examples": []},
    "CLIENT_JOURNEY_GATE": {"description": "Current client journey and CRJ handoff gate", "positive_examples": ["What is the current client journey gate?"], "negative_examples": []},
    "WORKFORCE_STATUS": {"description": "Current coding-worker availability and authentication classifications", "positive_examples": ["Is Codex currently available?", "What is OpenCode status?"], "negative_examples": []},
    "EVIDENCE_LOOKUP": {"description": "Evidence references supporting a prior operational answer", "positive_examples": ["Show me the evidence you used for that answer."], "negative_examples": []},
    "DAILY_BRIEF": {"description": "Current operator daily brief, priorities, blockers, and next actions", "positive_examples": ["What is the highest-value next action?", "What is the plan for today?"], "negative_examples": []},
}

CERTIFIED_ACTIONS = {
    "send_approved_email": {
        "description": "Send an approved email to a recipient via Resend",
        "requires_confirmation": True,
        "positive_examples": [
            "Email this to me",
            "Send a report via email",
            "Email Ray about the status",
        ],
    },
    "schedule_report": {
        "description": "Schedule a report to run at a specific time",
        "requires_confirmation": True,
        "positive_examples": [
            "Run this report tomorrow",
            "Schedule this in five minutes",
            "Run this same report daily",
        ],
    },
    "create_work_order": {
        "description": "Create a work order in Supabase",
        "requires_confirmation": True,
        "positive_examples": [
            "Turn this into a work order",
            "Create a work order for this",
            "Make a task for this",
        ],
    },
}

ALL_CAPABILITIES = {**CERTIFIED_READS, **CERTIFIED_ACTIONS}

# ─── Front Brain Classification Schema ────────────────────

_CLASSIFICATION_SCHEMA = """You are the front brain of Nexus Hermes, an operational AI chief-of-staff.

Your job: understand the user's message and classify it into exactly ONE mode.

MODES:
- "conversation": General chat, greetings, opinions, explanations, brainstorming, writing help.
  No live data needed. No tools needed. Just talk.

- "advisory": Strategy, priorities, planning, analysis, recommendations, business advice.
  May need supporting data from certified reads. You give judgment.

- "operational_read": The user wants CURRENT data from Nexus systems.
  Must map to exactly one certified capability. Do NOT guess — use the catalog.

- "governed_action": The user wants to DO something — send email, schedule, create work order.
  Must map to exactly one certified action. These require confirmation.

RULES:
1. If the message is just chatting → conversation
2. If the message asks for judgment/advice → advisory
3. If the message wants CURRENT data from a specific system → operational_read
4. If the message wants to execute an action → governed_action
5. If unsure between advisory and operational_read, prefer advisory (safer)
6. NEVER select a capability not in the catalog below
7. For operational_read, you MUST select a capability from the READ catalog
8. For governed_action, you MUST select a capability from the ACTION catalog
9. For conversation and advisory, set capability to null

CAPABILITY CATALOG:
{catalog}

CONTEXT:
{context}

OUTPUT EXACTLY THIS JSON (no other text):
{{
  "mode": "conversation" | "advisory" | "operational_read" | "governed_action",
  "capability": "capability_name" | null,
  "confidence": 0.0 to 1.0,
  "reason": "one sentence explanation"
}}"""

# ─── Conversation Mode Prompt ──────────────────────────────

_CONVERSATION_SYSTEM = """You are Nexus Hermes — Ray's operational chief-of-staff.

You are having a natural conversation. Be helpful, direct, and honest.

IDENTITY:
- You are Nexus Hermes, an operational AI chief-of-staff
- You have governed access to GoClear systems through certified capabilities
- You do NOT have unrestricted database or system access
- Some answers come from your model knowledge (training data)
- Some come from live operational reads through certified capabilities
- Some come from user-provided information
- Always identify the source category accurately when asked

CAPABILITIES:
- You can query live data through certified read capabilities (e.g., get_client_count)
- You can execute governed actions with confirmation (e.g., send_approved_email)
- Certified capabilities are approved, audited, and have access boundaries
- You are NOT a general-purpose database client

GUIDELINES:
- Answer the actual question asked
- Be concise unless the user asks for detail
- Don't pretend to have feelings or human experiences
- If you don't know, say so honestly
- When asked about your data source, be specific about which capability or knowledge you used
- Never claim "I have no access to systems" when you just used a certified capability
- Never claim training-cutoff dates when you have live data

{context_block}"""

# ─── Advisory Mode Prompt ──────────────────────────────────

_ADVISORY_SYSTEM = """You are Nexus Hermes — Ray's operational chief-of-staff providing strategic advice.

You are giving business advice, strategy, or prioritization guidance.

Guidelines:
- Give a DIRECT conclusion, not a hedged list of options
- State important assumptions
- Distinguish known facts from inference
- Quantify when possible (costs, timelines, probabilities)
- Identify the fastest realistic action
- Identify the primary risk
- Recommend a clear next step
- Avoid vague "it depends" answers

Supporting data from certified reads:
{supporting_data}

{context_block}"""

# ─── Reference Resolution ──────────────────────────────────

def resolve_references(text: str, active_context: Dict[str, Any]) -> str:
    """Resolve pronouns and references like 'that idea', 'number two', 'this report'."""
    lower = text.lower()
    resolved = text

    # "that idea" / "that plan" / "this idea"
    if re.search(r'\b(that|this)\s+(idea|plan|proposal|concept|approach)\b', lower):
        last_topic = active_context.get("last_topic", "")
        if last_topic:
            resolved = f"{resolved} [referring to: {last_topic}]"

    # "number two" / "the second one" / "option 2" / "number three"
    num_match = re.search(
        r'\b(?:number|option|#)\s*(\d+|one|two|three|four|five|six|seven|eight|nine|ten)'
        r'|(?:the\s+)?(second|third|first|2nd|3rd|1st|one|two|three|four|five)\b',
        lower,
    )
    if num_match:
        num_word = num_match.group(1) or num_match.group(2)
        word_to_num = {
            "first": "1", "second": "2", "third": "3",
            "1st": "1", "2nd": "2", "3rd": "3",
            "one": "1", "two": "2", "three": "3",
            "four": "4", "five": "5", "six": "6",
            "seven": "7", "eight": "8", "nine": "9", "ten": "10",
        }
        num = word_to_num.get(num_word, num_word)
        numbered = active_context.get("numbered_options", {})
        if num in numbered:
            resolved = f"{resolved} [referring to: {numbered[num]}]"

    # "this report" / "the same report"
    if re.search(r'\b(this|the\s+same|that)\s+report\b', lower):
        last_report = active_context.get("last_report", {})
        if last_report:
            report_id = last_report.get("report_definition_id", "unknown")
            resolved = f"{resolved} [referring to report: {report_id}]"

    # "do it tomorrow" / "run it in five minutes"
    if re.search(r'\b(do|run|schedule|execute)\s+(it|that|this)\b', lower):
        last_report = active_context.get("last_report", {})
        if last_report:
            resolved = f"{resolved} [referring to: {last_report.get('report_definition_id', 'last report')}]"

    return resolved


def extract_numbered_options(text: str) -> Optional[Dict[str, str]]:
    """Extract numbered list items from a response for later reference."""
    options = {}
    for match in re.finditer(r'(?:^|\n)\s*(\d+)[\.\)]\s*(.+?)(?=\n\s*\d+[\.\)]|\Z)', text, re.DOTALL):
        num = match.group(1)
        content = match.group(2).strip()
        if content:
            options[num] = content
    return options if options else None


def update_active_context_for_hermes(
    active_context: Dict[str, Any],
    user_message: str,
    response: str,
    mode: str,
    capability: Optional[str] = None,
    result_data: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Update the active context after processing a message."""
    ctx = dict(active_context)

    # Track last topic from user message
    ctx["last_topic"] = user_message[:200]

    # Track last mode and capability
    ctx["last_mode"] = mode
    ctx["last_capability"] = capability

    # Track numbered options if present in response
    options = extract_numbered_options(response)
    if options:
        ctx["numbered_options"] = options

    # Track report context if operational read
    if mode == "operational_read" and capability and result_data:
        ctx["last_report"] = {
            "report_definition_id": capability,
            "normalized_result": result_data,
            "rendered_format": response[:500],
        }

    # Track advisory context
    if mode == "advisory":
        ctx["last_advisory_response"] = response[:500]
        ctx["last_topic"] = user_message[:200]

    # Track pending confirmation for governed actions
    if mode == "governed_action" and capability:
        ctx["pending_action"] = {
            "capability": capability,
            "user_request": user_message[:200],
        }

    return ctx


# ─── LLM Classification ───────────────────────────────────

def _build_catalog_string() -> str:
    """Build a human-readable catalog of certified capabilities."""
    lines = ["CERTIFIED READS:"]
    for name, info in CERTIFIED_READS.items():
        examples = ", ".join(f'"{e}"' for e in info["positive_examples"][:2])
        lines.append(f"  {name}: {info['description']}")
        lines.append(f"    Examples: {examples}")
    lines.append("")
    lines.append("CERTIFIED ACTIONS (require confirmation):")
    for name, info in CERTIFIED_ACTIONS.items():
        examples = ", ".join(f'"{e}"' for e in info["positive_examples"][:2])
        lines.append(f"  {name}: {info['description']}")
        lines.append(f"    Examples: {examples}")
    return "\n".join(lines)


def _build_context_block(active_context: Dict[str, Any]) -> str:
    """Build a context block for the LLM prompts."""
    parts = []
    if active_context.get("last_topic"):
        parts.append(f"Previous topic: {active_context['last_topic']}")
    if active_context.get("last_report"):
        report = active_context["last_report"]
        parts.append(f"Last report: {report.get('report_definition_id', 'unknown')}")
    if active_context.get("numbered_options"):
        opts = active_context["numbered_options"]
        parts.append(f"Numbered options from last response: {json.dumps(opts)}")
    if active_context.get("last_mode"):
        parts.append(f"Last interaction mode: {active_context['last_mode']}")
    if active_context.get("last_capability"):
        parts.append(f"Last capability used: {active_context['last_capability']}")
    if active_context.get("last_capability_result"):
        pcr = active_context["last_capability_result"]
        parts.append(
            f"Last capability result: capability={pcr.get('capability')}, "
            f"source={pcr.get('source')}, freshness={pcr.get('freshness')}, "
            f"retrieved_at={pcr.get('retrieved_at')}"
        )
    return "\n".join(parts) if parts else "No prior context."


# ─── Provenance Follow-Up Detection ───────────────────────

_PROVENANCE_PATTERNS = [
    r"where\s+(did\s+)?(you\s+)?get\s+(that|this|the)\s+(info|information|data|number|count|result)",
    r"did\s+(that|this|it)\s+come\s+from\s+(supabase|the\s+database|a\s+live|the\s+system)",
    r"is\s+that\s+(live|real[\s-]time|current|up[\s-]to[\s-]date|fresh|current)",
    r"when\s+(was\s+)?(that|it|this)\s+(retrieved|fetched|pulled|obtained|queried|updated|last)",
    r"how\s+(current|fresh|old|recent)\s+is\s+(that|this|it)",
    r"which\s+(capability|tool|system|source)\s+(did\s+)?(you\s+)?use",
    r"did\s+you\s+(look\s+that\s+up|query|check|search|fetch|get\s+that|remember)",
    r"are\s+you\s+sure\s+about\s+(that|this|the\s+number|those)",
    r"what\s+(source|system|database|capability)\s+(did\s+)?(you\s+)?use",
    r"how\s+did\s+you\s+(know|get|find|determine|calculate)",
    r"where\s+did\s+that\s+(number|count|data|info|result)\s+come\s+from",
    r"is\s+that\s+from\s+(supabase|the\s+database|live|model|training)",
]

_PROVENANCE_RE = re.compile(
    "|".join(_PROVENANCE_PATTERNS), re.IGNORECASE
)


def detect_provenance_followup(user_message: str) -> bool:
    """Detect if the user message is asking about data provenance."""
    return bool(_PROVENANCE_RE.search(user_message))


def _format_phoenix_time(iso_timestamp: str) -> str:
    """Convert an ISO-8601 UTC timestamp to human-friendly America/Phoenix time."""
    if not iso_timestamp:
        return "unknown time"
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        # Parse ISO timestamp (handle Z and +00:00)
        ts = iso_timestamp.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        phoenix = dt.astimezone(ZoneInfo("America/Phoenix"))
        return phoenix.strftime("%-I:%M %p Phoenix time on %B %-d, %Y")
    except Exception:
        return iso_timestamp


def generate_provenance_response(
    user_message: str,
    last_capability_result: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Generate a deterministic provenance response from persisted context.

    Correctly distinguishes SOURCE (where data came from) from
    ACCESS BOUNDARY (how Hermes was permitted to retrieve it).

    Returns None if no relevant capability result exists.
    """
    if not last_capability_result:
        return None

    cap = last_capability_result.get("capability", "unknown")
    source = last_capability_result.get("source", "unknown")
    source_type = last_capability_result.get("source_type", "unknown")
    freshness = last_capability_result.get("freshness", "unknown")
    retrieved_at = last_capability_result.get("retrieved_at", "")
    status = last_capability_result.get("status", "unknown")
    access_boundary = last_capability_result.get("access_boundary", "certified capability only")
    safe_summary = last_capability_result.get("safe_summary", {})

    # Accept both "success" and "ok" as valid statuses
    if status not in ("success", "ok"):
        return (
            f"The last {cap.replace('_', ' ')} query did not complete successfully "
            f"(status: {status}). I cannot provide verified data from that query."
        )

    cap_desc = cap.replace("_", " ")
    msg_lower = user_message.lower()
    phoenix_time = _format_phoenix_time(retrieved_at)

    # ── Direct source confirmation ──────────────────────────
    # "Did that come directly from Supabase?" / "So you queried Supabase?"
    is_direct_source_question = (
        ("directly" in msg_lower or "direct" in msg_lower or "itself" in msg_lower
         or "so you" in msg_lower or "actually" in msg_lower)
        and ("supabase" in msg_lower or "source" in msg_lower or "database" in msg_lower)
    )
    if is_direct_source_question:
        if source_type in ("live_governed_read", "cached_governed_read") and source != "unknown":
            return (
                f"Yes. The {cap_desc} capability queried the approved "
                f"{source} source directly during your request. I accessed it "
                f"through a governed capability, not unrestricted database access."
            )
        else:
            return (
                f"No. The data did not come directly from {source}. "
                f"It came from {source_type}."
            )

    # ── Source identification ───────────────────────────────
    # "Where did you get that?" / "What source?" / "Which capability?"
    if "where" in msg_lower or "source" in msg_lower or "how did" in msg_lower:
        return (
            f"From the {cap_desc} capability, which queried the approved "
            f"{source} source during your request. Access was through a "
            f"governed capability — I do not have unrestricted database access."
        )

    # ── Live/cached question ────────────────────────────────
    if "live" in msg_lower or "real-time" in msg_lower or "current" in msg_lower or "fresh" in msg_lower:
        if freshness == "live":
            return (
                f"Yes, that data is live. It was retrieved through a "
                f"governed {source} query at {phoenix_time}."
            )
        elif freshness == "cached":
            return (
                f"That data is cached, not live. It was last retrieved "
                f"at {phoenix_time}."
            )
        else:
            return (
                f"That data is {freshness}. It was last retrieved "
                f"at {phoenix_time}."
            )

    # ── When/timestamp question ─────────────────────────────
    if "when" in msg_lower or "timestamp" in msg_lower or "retrieved" in msg_lower:
        return (
            f"It was retrieved at {phoenix_time} through a "
            f"{freshness} governed {source} query."
        )

    # ── Cached question ─────────────────────────────────────
    if "cached" in msg_lower or "cache" in msg_lower:
        if freshness == "live":
            return (
                f"No, that was not cached. It was a live governed "
                f"{source} query at {phoenix_time}."
            )
        elif freshness == "cached":
            return (
                f"Yes, that was a cached result, originally from "
                f"{source}."
            )
        else:
            return (
                f"The freshness was {freshness}."
            )

    # ── Capability identification (concise) ─────────────────
    if "capability" in msg_lower or "tool" in msg_lower:
        return f"I used {cap_desc}."

    # ── Confidence question ─────────────────────────────────
    if "sure" in msg_lower:
        summary_parts = []
        for k, v in safe_summary.items():
            label = k.replace("_", " ").title()
            summary_parts.append(f"  {label}: {v}")
        summary_str = "\n".join(summary_parts) if summary_parts else "  (no summary available)"
        return (
            f"Yes, I'm confident. It came from a verified {freshness} "
            f"{source} query through the {cap_desc} capability "
            f"at {phoenix_time}.\n\n{summary_str}"
        )

    # ── Lookup/query question ───────────────────────────────
    if "look that up" in msg_lower or "query" in msg_lower or "fetch" in msg_lower:
        return (
            f"Yes, I looked that up in real-time through the {cap_desc} "
            f"capability, which queried the approved {source} source."
        )

    # ── Default: concise provenance ─────────────────────────
    return (
        f"From the {cap_desc} capability, querying the approved "
        f"{source} source. It was a {freshness} read."
    )


async def _call_llm(system_prompt: str, user_message: str) -> str:
    """Call the LLM via LlmGatewayAdapter."""
    from nexus_agent_platform.workflows.litellm_adapter import LlmGatewayAdapter

    adapter = LlmGatewayAdapter(agent_id="hermes")
    result = await adapter.completion(
        model=HERMES_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=MODEL_TEMPERATURE,
        max_tokens=MODEL_MAX_TOKENS,
    )
    return result.get("content", "")


def classify_message(
    user_message: str,
    active_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Classify a user message into a mode and optional capability.

    Returns a dict with: mode, capability, confidence, reason.
    Falls back to conversation mode on any error.
    """
    deterministic = _deterministic_operational_intent(user_message)
    if deterministic:
        return deterministic

    ctx = active_context or {}
    catalog = _build_catalog_string()
    context_block = _build_context_block(ctx)

    # Resolve references before classification
    resolved_message = resolve_references(user_message, ctx)

    system_prompt = _CLASSIFICATION_SCHEMA.format(
        catalog=catalog,
        context=context_block,
    )

    try:
        raw = asyncio.run(_call_llm(system_prompt, resolved_message))
        # Extract JSON from response (model may wrap in markdown)
        json_match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
        if json_match:
            decision = json.loads(json_match.group(0))
        else:
            decision = json.loads(raw)

        # Validate mode
        valid_modes = {"conversation", "advisory", "operational_read", "governed_action"}
        mode = decision.get("mode", "conversation")
        if mode not in valid_modes:
            mode = "conversation"

        # Validate capability
        capability = decision.get("capability")
        if mode == "operational_read":
            if capability not in CERTIFIED_READS:
                # Try fuzzy match
                capability = _fuzzy_match_capability(capability, CERTIFIED_READS)
        elif mode == "governed_action":
            if capability not in CERTIFIED_ACTIONS:
                capability = _fuzzy_match_capability(capability, CERTIFIED_ACTIONS)
        else:
            capability = None  # conversation and advisory don't use capabilities

        return {
            "mode": mode,
            "capability": capability,
            "confidence": min(1.0, max(0.0, float(decision.get("confidence", 0.5)))),
            "reason": decision.get("reason", ""),
        }

    except Exception as exc:
        log.warning("Front brain classification failed: %s — defaulting to conversation", exc)
        return {
            "mode": "conversation",
            "capability": None,
            "confidence": 0.0,
            "reason": f"classification_error: {exc}",
        }


def _deterministic_operational_intent(user_message: str) -> Optional[Dict[str, Any]]:
    """Protect high-value operator questions from model routing drift."""
    lower = user_message.lower().strip()
    checks = (
        (("evidence" in lower and ("show" in lower or "used" in lower)), "EVIDENCE_LOOKUP"),
        (("how many clients" in lower or "production client count" in lower or "client count" in lower or "number of clients" in lower), "CLIENT_COUNT"),
        (("current nexus os status" in lower or "nexus os status" in lower or "system status" in lower or "current system status" in lower), "SYSTEM_HEALTH"),
        (("alpha" in lower and ("latest" in lower or "most recent" in lower or "find" in lower)), "ALPHA_LATEST"),
        (("blocker" in lower or "blocked" in lower or "needs attention" in lower), "BLOCKERS"),
        (("pending approval" in lower or "pending approvals" in lower or "approvals are pending" in lower or "what requires ray" in lower), "APPROVAL_QUEUE"),
        (("business loop" in lower or "business loops" in lower or "opportunity loop" in lower or "loop last run" in lower), "BUSINESS_LOOP_STATUS"),
        (("accept" in lower and "watch" in lower and "opportun" in lower), "BUSINESS_OPPORTUNITIES"),
        (("research ran" in lower or "most recently" in lower and "research" in lower), "RESEARCH_HISTORY"),
        (("payment gate" in lower or "status of stripe" in lower or "stripe status" in lower), "PAYMENT_GATE"),
        (("client journey gate" in lower or "journey gate" in lower), "CLIENT_JOURNEY_GATE"),
        ((("codex" in lower or "opencode" in lower or "mimo" in lower or "kilo" in lower or "coding worker" in lower or "coding workers" in lower or "worker pool" in lower) and ("available" in lower or "status" in lower)), "WORKFORCE_STATUS"),
        (("ai cost" in lower or "ai operations cost" in lower or "token cost" in lower or "provider cost" in lower), "AI_COST_SUMMARY"),
        (("highest-value next action" in lower or "highest value next action" in lower or "plan for today" in lower or "money today" in lower or "daily brief" in lower), "DAILY_BRIEF"),
        (("governed access" in lower or "certified capabilities" in lower) and ("nexus os data" in lower or "supabase" in lower), "get_runtime_capabilities"),
    )
    for matched, capability in checks:
        if matched:
            return {"mode": "operational_read", "capability": capability, "confidence": 1.0, "reason": "deterministic operator-question contract"}
    return None

def _fuzzy_match_capability(
    name: Optional[str], catalog: Dict[str, Any]
) -> Optional[str]:
    """Try to match a capability name loosely."""
    if not name:
        return None
    lower = name.lower().strip()
    # Exact match
    if lower in catalog:
        return lower
    # Substring match
    for key in catalog:
        if lower in key or key in lower:
            return key
    # Word overlap
    for key in catalog:
        key_words = set(key.split("_"))
        name_words = set(lower.split())
        if key_words & name_words:
            return key
    return None


# ─── Conversation Response Generation ─────────────────────

def generate_conversation_response(
    user_message: str,
    active_context: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a natural conversation response."""
    ctx = active_context or {}
    context_block = _build_context_block(ctx)
    system_prompt = _CONVERSATION_SYSTEM.format(context_block=context_block)

    resolved = resolve_references(user_message, ctx)

    try:
        response = asyncio.run(_call_llm(system_prompt, resolved))
        return response or "I'm not sure how to respond to that. Could you try again?"
    except Exception as exc:
        log.warning("Conversation generation failed: %s", exc)
        return "I had trouble generating a response. Could you try again?"


# ─── Advisory Response Generation ─────────────────────────

def generate_advisory_response(
    user_message: str,
    supporting_data: Optional[Dict[str, Any]] = None,
    active_context: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate an advisory response with optional supporting data."""
    ctx = active_context or {}
    data_str = json.dumps(supporting_data, indent=2) if supporting_data else "No supporting data available."
    context_block = _build_context_block(ctx)
    system_prompt = _ADVISORY_SYSTEM.format(
        supporting_data=data_str,
        context_block=context_block,
    )

    resolved = resolve_references(user_message, ctx)

    try:
        response = asyncio.run(_call_llm(system_prompt, resolved))
        return response or "I need more context to give you a solid recommendation. Could you tell me more?"
    except Exception as exc:
        log.warning("Advisory generation failed: %s", exc)
        return "I had trouble generating advice. Could you try again?"


# ─── Operational Read Execution ────────────────────────────

_READ_HANDLER_MAP: Dict[str, str] = {
    "get_client_count": "nexus_agent_platform.agents.hermes:_get_client_count",
    "get_system_status": "nexus_agent_platform.agents.hermes:_get_system_status",
    "get_failure_report": "nexus_agent_platform.agents.hermes:_get_failure_report",
    "get_alpha_status": "nexus_agent_platform.agents.hermes:_get_alpha_status",
    "process_status": "nexus_agent_platform.agents.hermes:_get_process_status",
    "process_failures": "nexus_agent_platform.agents.hermes:_get_failure_report",
    "research_history": "nexus_agent_platform.agents.hermes:_get_research_history",
    "opportunities": "nexus_agent_platform.agents.hermes:_get_opportunities",
    "trading_status": "nexus_agent_platform.agents.hermes:_get_trading_status",
    "pending_approvals": "nexus_agent_platform.agents.hermes:_get_pending_approvals",
}

_CANONICAL_SHARED_READS = {
    "SYSTEM_HEALTH", "PROCESS_STATUS", "BUSINESS_LOOP_STATUS", "BUSINESS_OPPORTUNITIES",
    "RESEARCH_HISTORY", "ALPHA_LATEST", "AI_COST_SUMMARY", "PAYMENT_GATE",
    "CLIENT_JOURNEY_GATE", "APPROVAL_QUEUE", "BLOCKERS", "CLIENT_COUNT",
    "WORKFORCE_STATUS", "EVIDENCE_LOOKUP", "DAILY_BRIEF",
}

_PROVENANCE_SOURCES = {
    "get_client_count": "supabase",
}


def _import_handler(handler_path: str):
    """Lazy import a handler function by module:function path."""
    module_path, _, func_name = handler_path.rpartition(":")
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, func_name)


def execute_operational_read(
    capability: str,
    user_message: str,
    authenticated_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a certified read capability by calling its handler directly.

    Bypasses the dispatcher import chain to avoid pulling in optional
    dependencies (temporalio) that read-only capabilities do not need.
    Returns the raw capability result dict with provenance metadata.
    """
    from datetime import datetime, timezone
    query_start = datetime.now(timezone.utc)
    trace_id = f"front_brain_{capability}_{query_start.strftime('%Y%m%d%H%M%S')}"

    if capability not in _READ_HANDLER_MAP:
        if capability in _CANONICAL_SHARED_READS:
            from nexus_agent_platform.capabilities.shared import execute_shared_capability
            result = execute_shared_capability("nexus_hermes", capability, {}, trace_id=trace_id)
            result.setdefault("capability", capability)
            return result
        return {"status": "unavailable", "error": f"Unknown capability: {capability}"}

    handler_path = _READ_HANDLER_MAP[capability]
    try:
        handler = _import_handler(handler_path)
    except Exception as exc:
        log.error("Failed to import handler for %s: %s", capability, exc)
        return {"status": "unavailable", "error": f"Handler import failed: {exc}"}

    try:
        raw_result = handler()
    except Exception as exc:
        log.error("Operational read failed for %s: %s", capability, exc)
        return {
            "status": "unavailable",
            "capability": capability,
            "error": str(exc),
            "provenance": {
                "capability": capability,
                "status": "error",
                "source": "unknown",
                "source_type": "unknown",
                "retrieved_at": query_start.isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
                "error": str(exc),
            },
        }

    query_end = datetime.now(timezone.utc)

    # Normalize handler result into standard shape
    if isinstance(raw_result, dict):
        status = raw_result.pop("status", "ok") if "status" in raw_result else "ok"
        data = raw_result
    elif isinstance(raw_result, str):
        status = "ok"
        data = {"detail": raw_result}
    else:
        status = "ok"
        data = {"result": raw_result}

    source_type = _PROVENANCE_SOURCES.get(capability, "local")
    provenance = {
        "capability": capability,
        "status": status,
        "source": source_type,
        "source_type": "live_governed_read" if source_type == "supabase" else "local_read",
        "retrieved_at": query_end.isoformat(),
        "query_start": query_start.isoformat(),
        "query_end": query_end.isoformat(),
        "freshness": "live" if source_type == "supabase" else "static",
        "trace_id": trace_id,
        "handler": handler_path,
    }

    # Carry any existing provenance from the handler (e.g. from _get_client_count)
    if isinstance(raw_result, dict) and "provenance" in raw_result:
        provenance.update(raw_result.pop("provenance"))

    return {
        "status": status,
        "capability": capability,
        "data": data,
        "error": data.get("error"),
        "provenance": provenance,
    }


# ─── Capability Result Synthesis ──────────────────────────

def synthesize_operational_response(
    capability: str,
    result: Dict[str, Any],
    user_message: str,
) -> str:
    """Synthesize a natural language response from a capability result."""
    status = result.get("status", "unknown")
    data = result.get("data", {})
    error = result.get("error")

    if status == "OK":
        return _synthesize_canonical_operational_response(capability, result)

    if status == "unavailable":
        return f"I couldn't retrieve {capability.replace('_', ' ')}: {error or 'source unavailable'}"

    if status == "forbidden":
        return f"I don't have permission to access {capability.replace('_', ' ')}."

    if status == "empty":
        return f"No records found for {capability.replace('_', ' ')}."

    if status != "ok":
        return f"Unexpected status for {capability.replace('_', ' ')}: {status}"

    # Synthesize based on capability type
    try:
        if capability == "get_client_count":
            return _synthesize_client_count(data)
        elif capability == "get_system_status":
            return _synthesize_system_status(data)
        elif capability == "get_failure_report":
            return _synthesize_failure_report(data)
        elif capability == "get_alpha_status":
            return _synthesize_alpha_status(data)
        elif capability == "pending_approvals":
            return _synthesize_pending_approvals(data)
        elif capability == "trading_status":
            return _synthesize_trading_status(data)
        elif capability == "research_history":
            return _synthesize_research_history(data)
        elif capability == "opportunities":
            return _synthesize_opportunities(data)
        elif capability == "process_status":
            return _synthesize_process_status(data)
        elif capability == "process_failures":
            return _synthesize_process_failures(data)
        else:
            return json.dumps(data, indent=2) if data else f"{capability} data retrieved successfully."
    except Exception as exc:
        log.warning("Synthesis failed for %s: %s", capability, exc)
        return json.dumps(data, indent=2) if data else f"{capability} data retrieved."


def _synthesize_canonical_operational_response(capability: str, result: Dict[str, Any]) -> str:
    data = result.get("data", {})
    prov = result.get("provenance", {})
    source = prov.get("source_path", result.get("source_path", "UNKNOWN"))
    freshness = result.get("freshness", "UNKNOWN")
    if capability == "BUSINESS_LOOP_STATUS":
        loops = data.get("loops", {})
        lines = [f"Business loops: {len(loops)} current certified loops (source: {source}, freshness: {freshness})."]
        for loop_id, item in loops.items():
            lines.append(f"- {loop_id}: {item.get('delta_status', item.get('status', 'UNKNOWN'))}; last run {item.get('completed_at', item.get('last_run', 'UNKNOWN'))}; verifier {item.get('verifier', 'UNKNOWN')}; next {item.get('next_action', 'UNKNOWN')}")
        return "\n".join(lines)
    if capability == "BUSINESS_OPPORTUNITIES":
        counts = data.get("by_decision", {})
        return f"Business opportunities: ACCEPT {counts.get('ACCEPT', 0)}, WATCH {counts.get('WATCH', 0)}, REJECT {counts.get('REJECT', 0)}. Process actions and registry entries are excluded. Source: {source}."
    if capability == "RESEARCH_HISTORY":
        return f"Most recent research session: {data.get('state', 'UNKNOWN')} completed {data.get('completed_at', 'UNKNOWN')}; {data.get('sources_ok', 'UNKNOWN')} sources OK, {data.get('sources_failed', 'UNKNOWN')} failed. Source: {source}."
    if capability == "PAYMENT_GATE":
        return f"Payment gate: {data.get('gate', 'UNKNOWN')}. Stripe mode: {data.get('stripe_mode', 'UNKNOWN')}; live keys present: {data.get('live_key_present', 'UNKNOWN')}; no live revenue recorded: {data.get('no_live_revenue_recorded', 'UNKNOWN')}. Next: {data.get('next_action', 'UNKNOWN')}"
    if capability == "CLIENT_JOURNEY_GATE":
        journey = data.get('journey', {})
        return f"Client journey gate: {data.get('gate', 'UNKNOWN')}. Current stage: {journey.get('current_stage', 'UNKNOWN')}; Ray approval required: {data.get('crj_bridge', {}).get('requires_ray_approval', 'UNKNOWN')}."
    if capability == "WORKFORCE_STATUS":
        workers = data.get('worker_pool', [])
        return "Worker status: " + "; ".join(f"{w.get('worker_id', 'UNKNOWN')}={w.get('status', 'UNKNOWN')}" for w in workers)
    if capability == "AI_COST_SUMMARY":
        cost = data.get('cost_summary', {})
        return f"AI cost: provider ${cost.get('provider_cost_usd', 'UNKNOWN')}; input tokens {cost.get('input_tokens', 'UNKNOWN')}; output tokens {cost.get('output_tokens', 'UNKNOWN')}; deterministic share {cost.get('deterministic_execution_share', 'UNKNOWN')}."
    if capability == "DAILY_BRIEF":
        return f"Daily Brief next action: {data.get('highest_value_next_action', 'UNKNOWN')}\nTop priority: {data.get('top_priority', 'UNKNOWN')}\nSource: {source}."
    if capability == "EVIDENCE_LOOKUP":
        return "Evidence references:\n" + "\n".join(f"- {ref}" for ref in data.get('refs', []))
    return json.dumps(data, indent=2, default=str)


def _synthesize_client_count(data: Dict[str, Any]) -> str:
    total = data.get("production_total", 0)
    if total == 0:
        return "No production client profiles found in the GoClear tenant."
    parts = [f"GoClear currently has {total} production client profiles."]
    active = data.get("active", 0)
    onboarding = data.get("onboarding", 0)
    inactive = data.get("inactive", 0)
    parts.append(f"\n- {active} active")
    parts.append(f"- {onboarding} onboarding")
    if inactive > 0:
        parts.append(f"- {inactive} inactive")
    tester = data.get("tester_or_certification", 0)
    if tester > 0:
        parts.append(f"\nThere are also {tester} demo or certification profiles, excluded from the production total.")
    return "\n".join(parts)


def _synthesize_system_status(data: Dict[str, Any]) -> str:
    if isinstance(data, dict):
        working = data.get("working", "")
        detail = data.get("detail", "")
        parts = [f"**System Status:** {working}"]
        if detail:
            parts.append(f"\n{detail}")
        return "\n".join(parts)
    return json.dumps(data, indent=2)


def _synthesize_failure_report(data: Dict[str, Any]) -> str:
    if isinstance(data, dict):
        working = data.get("working", "No failures")
        attention = data.get("needs_attention", "")
        parts = [f"**Failures:** {working}"]
        if attention:
            parts.append(f"\n{attention}")
        return "\n".join(parts)
    return json.dumps(data, indent=2)


def _synthesize_alpha_status(data: Dict[str, Any]) -> str:
    if isinstance(data, str):
        return data
    return json.dumps(data, indent=2)


def _synthesize_pending_approvals(data: Dict[str, Any]) -> str:
    count = data.get("pending_count", 0)
    if count == 0:
        return "No items currently awaiting your approval."
    items = data.get("items", [])
    parts = [f"You have {count} items awaiting approval:"]
    for item in items[:5]:
        parts.append(f"- {item.get('type', 'item')}: {item.get('title', 'untitled')}")
    if count > 5:
        parts.append(f"\n...and {count - 5} more.")
    return "\n".join(parts)


def _synthesize_trading_status(data: Dict[str, Any]) -> str:
    state = data.get("engine_state", "unknown")
    mode = data.get("mode", "unknown")
    kill = data.get("kill_switch", False)
    parts = [f"Trading engine: {state} ({mode} mode)"]
    if kill:
        parts.append("Kill switch: ACTIVE")
    return "\n".join(parts)


def _synthesize_research_history(data: Dict[str, Any]) -> str:
    runs = data.get("runs", {})
    total = runs.get("total", 0)
    completed = runs.get("completed", 0)
    parts = [f"Research: {total} runs ({completed} completed)"]
    items = runs.get("items", [])
    for item in items[:3]:
        parts.append(f"- {item.get('query', 'unnamed')} ({item.get('status', 'unknown')})")
    return "\n".join(parts)


def _synthesize_opportunities(data: Dict[str, Any]) -> str:
    total = data.get("total", 0)
    by_state = data.get("by_state", {})
    parts = [f"Business opportunities: {total} total"]
    for state, count in by_state.items():
        if count > 0:
            parts.append(f"- {state}: {count}")
    items = data.get("opportunities", [])
    for item in items[:3]:
        parts.append(f"- {item.get('title', 'untitled')} ({item.get('action_state', 'unknown')})")
    return "\n".join(parts)


def _synthesize_process_status(data: Dict[str, Any]) -> str:
    defs = data.get("definitions", {})
    runs = data.get("runs", {})
    parts = [
        f"Process definitions: {defs.get('total', 0)} total ({defs.get('enabled', 0)} enabled)",
        f"Recent runs: {runs.get('total', 0)} total ({runs.get('running', 0)} running, {runs.get('failed', 0)} failed)",
    ]
    return "\n".join(parts)


def _synthesize_process_failures(data: Dict[str, Any]) -> str:
    total = data.get("total", 0)
    by_status = data.get("by_status", {})
    if total == 0:
        return "No process failures in the last 24 hours."
    parts = [f"Process failures (last 24h): {total}"]
    for status, count in by_status.items():
        parts.append(f"- {status}: {count}")
    failures = data.get("failures", [])
    for f in failures[:3]:
        parts.append(f"- {f.get('definition_id', 'unknown')}: {f.get('error', 'no error message')}")
    return "\n".join(parts)
