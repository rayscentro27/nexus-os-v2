"""Turn-scoped resource and evidence contracts for the Hermes Nova shadow.

This is deliberately not a question router.  It records explicit resource
requirements and evidence quality so the model can continue reasoning with an
honest view of what was actually executed.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List
from urllib.parse import urlparse


def turn_requirements(prompt: str) -> Dict[str, Any]:
    """Describe explicit resource obligations without assigning question ownership."""
    text = (prompt or "").lower()
    resources: List[str] = []
    if re.search(r"\b(nexus|using nexus|check nexus)\b", text):
        resources.append("NEXUS")
    volatile_subject_request = bool(re.search(
        r"\b(?:what|how)\s+(?:is|are)\s+[a-z][\w.-]*(?:\s+[a-z][\w.-]*){0,3}\s+"
        r"(?:doing|up to|changing|happening)\s+right now\b",
        text,
    ))
    # Decision urgency is not automatically a request for external research.
    # Explicit web/current/latest/this-week language remains a resource
    # obligation; “right now” and “today” can simply express advice urgency.
    if re.search(r"\b(web|internet|online|outside information|current|latest|this week)\b", text) or volatile_subject_request:
        resources.append("PUBLIC_WEB")
    alpha_request = re.search(r"\b(research|researcher|alpha)\b", text)
    reuse_alpha = re.search(r"\bwhat did research find\b|\bresearch findings?\b", text) and not re.search(r"\b(challenge|research this|independently)\b", text)
    if alpha_request and not reuse_alpha:
        resources.append("ALPHA")
    current = bool(re.search(r"\b(current|latest|this week)\b", text) or volatile_subject_request)
    comparison = re.search(r"\bcompare\s+(.+?)(?:[.?]|$)", text, re.I)
    candidate_set: List[str] = []
    if comparison:
        candidate_text = comparison.group(1)
        candidate_text = re.sub(r"\s+and\s+", ",", candidate_text, flags=re.I)
        candidate_set = [item.strip(" ,") for item in candidate_text.split(",") if item.strip(" ,")]
    return {
        "objective": (prompt or "")[:1000],
        "turn_objective": (prompt or "")[:2000],
        "required_resources": list(dict.fromkeys(resources)),
        "fresh_execution_required": current or bool(resources),
        "reuse_only": bool(reuse_alpha),
        "candidate_set": candidate_set,
        # No named resource obligation means the native model reasons first;
        # optional research remains available when the model finds it material.
        "reasoning_first": bool(not resources),
    }


def executed_resources(tool_messages: Iterable[Dict[str, Any]]) -> List[str]:
    result: List[str] = []
    for message in tool_messages:
        name = str(message.get("name") or message.get("tool_name") or "")
        resource = {
            "nexus_read_shadow": "NEXUS",
            "public_web_search_shadow": "PUBLIC_WEB",
            "public_web_retrieval_shadow": "PUBLIC_WEB_RETRIEVAL",
            "alpha_challenge_shadow": "ALPHA",
        }.get(name)
        if name.startswith("mcp__nexus_mcp__nexus_get_"):
            resource = "NEXUS"
        if resource and resource not in result:
            result.append(resource)
    return result


def source_quality(url: str) -> str:
    host = (urlparse(url or "").hostname or "").lower()
    if host.endswith(".gov") or host.endswith(".gov.uk") or host.endswith(".edu"):
        return "PRIMARY"
    if host.startswith("www.") and host.count(".") <= 2:
        return "AUTHORITATIVE_SECONDARY"
    if host in {"reuters.com", "apnews.com", "bbc.com", "ft.com", "wsj.com", "nytimes.com"}:
        return "REPUTABLE_SECONDARY"
    return "UNKNOWN"


def currentness(source_date: str | None, retrieved_at: str | None, *, required: bool) -> str:
    if not source_date:
        return "UNKNOWN" if required else "UNDATED"
    try:
        date = datetime.fromisoformat(source_date.replace("Z", "+00:00"))
        retrieved = datetime.fromisoformat((retrieved_at or datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00"))
        age_days = max(0, (retrieved - date).days)
    except ValueError:
        return "UNKNOWN"
    return "CURRENT" if age_days <= 14 else "RECENT_BUT_NOT_CURRENT"


def evidence_state(prompt: str, tool_messages: Iterable[Dict[str, Any]], prior_records: Iterable[Dict[str, Any]] = ()) -> Dict[str, Any]:
    messages = list(tool_messages)
    requirements = turn_requirements(prompt)
    executed = executed_resources(messages)
    supported: List[Dict[str, Any]] = []
    partial: List[Dict[str, Any]] = []
    for message in messages:
        payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}
        name = str(message.get("name") or message.get("tool_name") or "")
        if name == "public_web_search_shadow":
            for row in payload.get("results", []) if isinstance(payload.get("results"), list) else []:
                supported.append({"claim": row.get("title", "candidate source"), "support": "DISCOVERY_ONLY", "url": row.get("url"), "source_quality": source_quality(row.get("url", ""))})
        elif name == "public_web_retrieval_shadow":
            url = payload.get("url") or payload.get("requested_url")
            item = {"claim": "retrieved page content", "url": url, "support": "DIRECT_PAGE_CONTENT" if payload.get("content_length", 0) else "UNKNOWN", "source_quality": source_quality(url or ""), "retrieved_at": payload.get("retrieved_at"), "source_date": payload.get("source_date"), "currentness": payload.get("currentness") or "UNKNOWN"}
            (supported if item["support"] == "DIRECT_PAGE_CONTENT" else partial).append(item)
        elif name in {"nexus_read_shadow", "alpha_challenge_shadow"} or name.startswith("mcp__nexus_mcp__nexus_get_"):
            status = payload.get("status")
            item = {"claim": name, "support": "DIRECT_RESULT" if status else "UNKNOWN", "result_id": payload.get("result_id")}
            if name == "alpha_challenge_shadow":
                item["supported_findings"] = payload.get("supported_findings") or payload.get("supported_claims") or []
            (supported if status in {"success", "ok", "SUCCESS", "COMPLETE"} else partial).append(item)
    missing = [r for r in requirements["required_resources"] if r not in executed and not (r == "PUBLIC_WEB" and "PUBLIC_WEB_RETRIEVAL" in executed)]
    # Current or explicitly multi-source work needs page-level evidence when
    # the search result is only discovery metadata.
    if "PUBLIC_WEB" in requirements["required_resources"] and "PUBLIC_WEB" in executed and "PUBLIC_WEB_RETRIEVAL" not in executed:
        missing.append("PUBLIC_WEB_RETRIEVAL")
    return {
        "objective": requirements["objective"],
        "required_resources": requirements["required_resources"],
        "executed_resources": executed,
        "missing_resources": missing,
        "supported_claims": supported,
        "partial_claims": partial,
        "source_quality": sorted({x.get("source_quality") for x in supported if x.get("source_quality")}),
        "currentness": "UNKNOWN" if requirements["fresh_execution_required"] and not supported else "AVAILABLE",
        # Any explicitly multi-resource objective needs a final synthesis pass;
        # Alpha is optional and must not be the condition that activates this
        # contract.
        "synthesis_required": len(requirements["required_resources"]) > 1,
        "reused_evidence": [
            {k: row.get(k) for k in ("source_turn_id", "resource", "capability", "request_id", "result_id", "artifact_id", "retrieved_at", "currentness", "relevance", "valid_for_current_turn")}
            for row in prior_records if row.get("valid_for_current_turn")
        ],
    }


def continuation_guidance(state: Dict[str, Any]) -> str:
    missing = state.get("missing_resources") or []
    if not missing:
        return ""
    names = ", ".join(missing)
    return (
        "\n\n[CURRENT TURN EVIDENCE CONTRACT]\n"
        f"The current objective explicitly requires these resources: {names}. "
        "Your prior draft did not execute all of them. Continue this same turn "
        "by calling the missing native tools now. Do not claim current, verified, "
        "Nexus, web, or research evidence until the corresponding result returns. "
        "Then synthesize with clearly qualified confidence.\n"
    )


def claim_feedback(prompt: str, response: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Identify material evidence gaps without rejecting the answer outright."""
    text = (response or "").lower()
    objective = (prompt or "").lower()
    unsupported: List[str] = []
    retrieved = [x for x in state.get("supported_claims", []) if x.get("support") == "DIRECT_PAGE_CONTENT"]
    # Validate currentness asserted by the draft itself, not only currentness
    # requested by the user. A no-tool recommendation may use model judgment,
    # but cannot upgrade it to current or verified without direct evidence or
    # an explicitly linked current result.
    current_assertion = bool(re.search(
        r"\b(?:currently|latest|verified|confirmed|evidence (?:shows|indicates)|"
        r"current\s+(?:trends?|market|conditions?|demand|data|evidence)|"
        r"(?:surging|growing demand|increasing demand|market demand|"
        r"significant interest|ideal time|market is on the rise|market access|"
        r"market potential|revenue acceleration|growth potential|gaining traction|"
        r"increasing preference|rising demand|growing market|growing consumer interest|"
        r"proven interest|favorable environment))\b",
        text,
    ))
    qualification = re.search(
        r"not (?:proven|verified|confirmed)|hasn't been verified|has not been verified|unknown|unavailable|insufficient evidence|"
        r"currentness_not_proven|status remains unverified|no results|timeout|timed out|"
        r"limited(?:\s+(?:results|evidence))?|partial (?:evidence|verification)|"
        r"lacks? (?:strong|current|direct) (?:verification|evidence)|not strongly current|not current enough|"
        r"(?:evidence|data|support|verification|findings?|research|sources?|signal|results?).{0,80}"
        r"(?:limited|weak|uncertain|not enough|unavailable|inconclusive)|"
        r"(?:limited|weak|uncertain|not enough|unavailable|inconclusive).{0,80}"
        r"(?:evidence|data|support|verification|findings?|research|sources?|signal|results?)|"
        r"need(?:s)? to verify|cannot confirm|not definitive|no reliable",
        text,
    )
    linked_current = any(
        str(row.get("currentness", "")).upper() == "CURRENT"
        and row.get("valid_for_current_turn")
        for row in state.get("reused_evidence", [])
        if isinstance(row, dict)
    )
    # Governed Nexus/Alpha results are direct current-turn execution evidence
    # even though they are not public web pages. Do not confuse the absence of
    # a page retrieval with the absence of evidence for a current capability
    # read.
    direct_current_resource = bool(
        any(resource in state.get("executed_resources", []) for resource in ("NEXUS", "ALPHA"))
        and any(resource in state.get("required_resources", []) for resource in ("NEXUS", "ALPHA"))
    )
    if current_assertion and not qualification and not retrieved and not linked_current and not direct_current_resource:
        unsupported.append("currentness_not_proven")
    no_current_evidence = not retrieved and not linked_current and not direct_current_resource
    no_tool_business_assertion = bool(re.search(
        r"(?:revenue\s+(?:potential|stream|generation|growth)|earning\s+potential|"
        r"market\s+demand|currently\s+growing|recent\s+growth|financial\s+benefit)", text
    ))
    explicit_judgment = bool(re.search(
        r"\b(?:i think|i believe|my (?:take|view|judgment)|i(?:'d| would)\s+use|"
        r"my preference|in my judgment|generally|could|might|hypothesis|target|goal)\b", text
    ))
    if no_current_evidence and no_tool_business_assertion and not explicit_judgment:
        unsupported.append("no_tool_evidence_attribution")
    if re.search(r"\baffiliate|referral|partner program", objective) and re.search(r"affiliate program|referral program", text):
        page_text = " ".join(str(x.get("content", "")) for x in state.get("page_payloads", []))
        qualified_unknown = re.search(r"no (?:definitive|specific|confirmed)|unverified|not (?:proven|verified|confirmed)|remains unknown|insufficient evidence|status remains unverified|limited(?:\s+(?:results|evidence))?|partial (?:evidence|verification)|lacks? (?:strong|current|direct) (?:verification|evidence)|not strongly current", text)
        if not qualified_unknown and not re.search(r"affiliate|referral|partner program", page_text, re.I):
            unsupported.append("affiliate_program_status")
    if re.search(r"\$\s*1,?000\s*(?:/|per\s+)week|1,?000\s+weekly", text):
        exact_target_supported = any(
            re.search(r"\$\s*1,?000\s*(?:/|per\s+)week|1,?000\s+weekly", str(item.get("claim", "")), re.I)
            and item.get("support") in {"DIRECT_PAGE_CONTENT", "DIRECT_RESULT"}
            for item in state.get("supported_claims", [])
        )
        target_framing = re.search(r"(?:initial|test|validation)\s+(?:target|goal)|(?:target|goal)\s+for\s+(?:a\s+)?test|my\s+(?:target|goal)|i(?:'d| would)\s+use", text)
        if not exact_target_supported and (not target_framing or re.search(r"(?:potential|consistent\s+income|revenue\s+stream|can\s+create|could\s+generate|reach(?:ing)?\s+the\s+target)", text)):
            unsupported.append("aspirational_target_attribution")
    alpha_items = [item for item in state.get("supported_claims", []) if item.get("claim") == "alpha_challenge_shadow"]
    alpha_has_findings = any(bool(item.get("supported_findings")) for item in alpha_items)
    if "ALPHA" in set(state.get("executed_resources", [])) and not alpha_has_findings and re.search(
        r"research (?:found|showed|revealed|established|confirmed)|alpha (?:found|showed|revealed|confirmed)", text
    ):
        unsupported.append("unsupported_alpha_finding")
    formal_request = bool(re.search(r"\b(?:report|audit|certification|formal|detailed evidence review|status report)\b", objective))
    if not formal_request and re.search(r"\b(?:would you like|if you(?:'re| are) ready|let me know if|i can assist|next step|moving forward)\b", text):
        unsupported.append("unnecessary_next_action_prompt")
    # A current-data request requires validation only when the answer itself
    # makes a currentness assertion. Brand names such as “Current” and a
    # qualified recommendation are not claims of current external evidence.
    if current_assertion and re.search(r"\b(current|latest)\b", objective) and not retrieved:
        if not qualification:
            unsupported.append("current_external_evidence")
    elif current_assertion and re.search(r"\b(current|latest)\b", objective):
        if not any(x.get("currentness") == "CURRENT" for x in state.get("page_payloads", [])) and not qualification:
            unsupported.append("currentness_not_proven")
    executed = set(state.get("executed_resources", []))
    if "PUBLIC_WEB_RETRIEVAL" in executed and re.search(
        r"\b(?:need|needs|required|have)\s+(?:to\s+)?(?:retrieve|review|inspect)|"
        r"\b(?:url|page|source)s?\b.{0,120}\b(?:need|needs|required)\b.{0,40}\bretriev",
        text,
    ):
        unsupported.append("retrieval_state_mismatch")
    if "PUBLIC_WEB_RETRIEVAL" not in executed and re.search(
        r"\b(?:i|we)\s+(?:retrieved|reviewed|inspected|verified)\s+(?:the\s+)?(?:page|pages|source|sources)\b",
        text,
    ):
        unsupported.append("retrieval_state_mismatch")
    return {"valid": not unsupported, "unsupported_claims": list(dict.fromkeys(unsupported))}


def claim_attribution(prompt: str, response: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Retain an auditable claim/evidence index without leaking schema to Telegram."""
    rows: List[Dict[str, Any]] = []
    for item in state.get("supported_claims", []) + state.get("partial_claims", []):
        rows.append({
            "claim": item.get("claim"),
            "classification": "VERIFIED_EXTERNAL_FACT" if item.get("support") == "DIRECT_PAGE_CONTENT" else "UNKNOWN",
            "source_reference": item.get("url") or item.get("result_id"),
            "source_date": item.get("source_date"),
            "retrieval_state": "RETRIEVED" if item.get("support") == "DIRECT_PAGE_CONTENT" else "DISCOVERY_ONLY",
            "currentness": item.get("currentness") or state.get("currentness", "UNKNOWN"),
            "support": item.get("support", "UNKNOWN"),
        })
    lower = (response or "").lower()
    if re.search(r"\$\s*1,?000\s*(?:/|per\s+)week|1,?000\s+weekly", lower):
        rows.append({"claim": "$1,000/week", "classification": "ASPIRATIONAL_TARGET", "source_reference": None,
                     "source_date": None, "retrieval_state": "NO_DIRECT_SUPPORT", "currentness": "UNKNOWN",
                     "support": "MODEL_JUDGMENT"})
    alpha_executed = "ALPHA" in set(state.get("executed_resources", []))
    alpha_has_findings = any(bool(x.get("supported_findings")) for x in state.get("supported_claims", []) if x.get("claim") == "alpha_challenge_shadow")
    if alpha_executed and not alpha_has_findings:
        rows.append({"claim": "Alpha findings", "classification": "UNKNOWN", "source_reference": None,
                     "source_date": None, "retrieval_state": "ALPHA_COMPLETE_ZERO_SUPPORTED_FINDINGS",
                     "currentness": "UNKNOWN", "support": "NO_SUPPORTED_FINDINGS"})
    return {"version": 1, "turn_objective": (prompt or "")[:500], "claims": rows,
            "model_judgment_present": bool(re.search(r"\b(I would|I'd|my take|I think|I recommend)\b", response or "", re.I))}
