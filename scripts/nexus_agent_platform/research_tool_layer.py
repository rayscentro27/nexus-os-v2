"""Governed Research tool registry, strategy planner, and Hermes executor."""
from __future__ import annotations

import hashlib
import json
import re
import ssl
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
RUNS_PATH = ROOT / "data/governed/research_tool_layer_runs.jsonl"
PRIMARY_AUTONOMOUS_ENGINE = "HERMES_TOOL_LAYER"

try:
    import certifi
    _URL_SSL = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _URL_SSL = ssl.create_default_context()


TOOL_REGISTRY: tuple[dict[str, Any], ...] = (
    {"tool_id": "you-search", "capability": "GENERAL_SEARCH", "source_class": "WEB_SEARCH",
     "auth_state": "KEYLESS_FREE_PROFILE", "cost_class": "FREE_LIMITED_100_QUERIES_DAILY",
     "allowed_use": "Discover candidate sources and current web/news pages.",
     "limitations": "Search results are candidate URLs, not evidence; free profile has a daily limit."},
    {"tool_id": "you-discover", "capability": "MCP_AGENT_DISCOVERY", "source_class": "TOOL_DISCOVERY",
     "auth_state": "KEYLESS_FREE_PROFILE", "cost_class": "FREE_LIMITED_100_QUERIES_DAILY",
     "allowed_use": "Discover agents, MCP servers, and skills when needed for a task.",
     "limitations": "Not a customer/market web-search tool."},
    {"tool_id": "public_web_retrieval", "capability": "DEEP_EXTRACT", "source_class": "URL_CONTENT",
     "auth_state": "NO_AUTH_PUBLIC_HTTP", "cost_class": "NO_PROVIDER_FEE",
     "allowed_use": "Fetch a known public URL and extract readable page text.",
     "limitations": "Public HTTP only; access controls, paywalls, and anti-bot restrictions are respected."},
    {"tool_id": "youtube_channel_registry", "capability": "SPECIALIZED_MONITORING", "source_class": "YOUTUBE",
     "auth_state": "GOVERNED_DESIGNATED_REGISTRY", "cost_class": "EXISTING_RUNTIME",
     "allowed_use": "Check only designated enabled channels and process eligible videos.",
     "limitations": "Not a general YouTube search replacement."},
    {"tool_id": "tradingview_public_source", "capability": "SPECIALIZED_DISCOVERY", "source_class": "TRADINGVIEW",
     "auth_state": "PUBLIC_SOURCE", "cost_class": "EXISTING_RUNTIME",
     "allowed_use": "Inspect public scripts through the existing bounded adapter.",
     "limitations": "Claims are leads only; independent Nexus testing remains required."},
    {"tool_id": "github_repository_search", "capability": "SPECIALIZED_DISCOVERY", "source_class": "GITHUB",
     "auth_state": "PUBLIC_SOURCE", "cost_class": "EXISTING_RUNTIME",
     "allowed_use": "Discover public repositories for a concrete Nexus capability question.",
     "limitations": "Repository presence does not establish quality or fitness."},
    {"tool_id": "affiliate_directory_search", "capability": "SPECIALIZED_DISCOVERY", "source_class": "AFFILIATE",
     "auth_state": "PUBLIC_DISCOVERY_ONLY", "cost_class": "EXISTING_RUNTIME",
     "allowed_use": "Discover Affiliate.Watch and PartnerStack listings via current approved search.",
     "limitations": "Program terms and payouts require official-source verification."},
    {"tool_id": "funding_official_sources", "capability": "SPECIALIZED_DISCOVERY", "source_class": "FUNDING_GRANTS",
     "auth_state": "PUBLIC_SOURCE", "cost_class": "EXISTING_RUNTIME",
     "allowed_use": "Find and verify public government, SBA, state, and local programs.",
     "limitations": "Eligibility and terms must be verified on the official program page."},
)


def plan_source_strategy(question: str, evidence_needed: str | None = None) -> dict[str, Any]:
    """Build a question/evidence-first *candidate* plan; the agent may adapt it."""
    q = " ".join(str(question or "").split()).strip()
    low = q.casefold()
    classes: list[str] = []
    tools: list[str] = ["you-search"]
    why: list[str] = []
    if any(x in low for x in ("reporting", "complaint", "problem", "unresolved", "customer", "owner")):
        classes.extend(["CUSTOMER_DISCUSSIONS", "PRODUCT_REVIEWS"])
        why.append("Firsthand discussion/review pages can show reported friction and unmet needs.")
    if any(x in low for x in ("funding", "grant", "loan", "eligib")):
        classes.append("OFFICIAL_SOURCE")
        why.append("Official program/lender documentation can verify current alternatives and constraints.")
    if any(x in low for x in ("opportunity", "demand", "market", "product", "service", "affiliate")):
        classes.extend(["MARKETPLACE", "AFFILIATE"])
        why.append("Public product/partner pages can establish available alternatives, not sales or payout claims.")
    if any(x in low for x in ("youtube", "video", "creator", "social", "trend")):
        classes.append("YOUTUBE")
        tools.append("youtube_channel_registry")
        why.append("The designated YouTube monitor is preferred when video evidence is pertinent.")
    if any(x in low for x in ("strategy", "indicator", "trading", "market data")):
        classes.append("TRADINGVIEW")
        tools.append("tradingview_public_source")
        why.append("The existing public TradingView adapter provides the specialized script source.")
    if any(x in low for x in ("github", "software", "technology", "nexus workflow", "automation")):
        classes.append("GITHUB")
        tools.append("github_repository_search")
        why.append("Repository evidence is relevant to a concrete software/workflow question.")
    if not classes:
        classes.append("WEB_SEARCH")
        why.append("General search discovers candidate sources for this question.")
    tools.append("public_web_retrieval")
    return {
        "research_question": q,
        "evidence_needed": evidence_needed or "Evidence that directly answers the question, with source date, provenance, and corroboration when material.",
        "firsthand_evidence_preferred": any(x in classes for x in ("CUSTOMER_DISCUSSIONS", "PRODUCT_REVIEWS")),
        "source_classes_planned": list(dict.fromkeys(classes)),
        "tools_planned": list(dict.fromkeys(tools)),
        "cross_check_required": len(classes) > 1,
        "why_these_sources": why,
        "stop_condition": "Create a finding only when extracted evidence is relevant and sufficiently corroborated; otherwise change strategy or report RESEARCH_INCONCLUSIVE.",
    }


def classify_source(url: str, title: str = "", text: str = "") -> dict[str, str]:
    """Conservative page-type labels; firsthand status is never guessed."""
    host = (urlsplit(url).hostname or "").lower()
    content = f"{title} {text[:1500]}".casefold()
    if host.endswith(".gov") or ".gov." in host or host in {"tio.com.au", "fedsmallbusiness.org", "federalreserve.gov"}:
        kind = "OFFICIAL_SOURCE"
    elif any(d in host for d in ("reddit.com", "quora.com", "forums.", "community.")):
        kind = "DISCUSSION"
    elif any(d in host for d in ("trustpilot.", "g2.com", "capterra.", "bbb.org", "amazon.")):
        kind = "REVIEW"
    elif "/opinion/" in url.casefold() or "/forum-" in url.casefold():
        kind = "OPINION_LETTER"
    elif any(d in host for d in ("bloomberg.", "forbes.", "reuters.", "apnews.com", "bbc.")):
        kind = "NEWS"
    elif any(x in content for x in ("sponsored", "affiliate link", "our partners", "get started today")):
        kind = "VENDOR_MARKETING"
    elif any(x in content for x in ("ultimate guide", "best tools", "top 10", "what you need to know")):
        kind = "SEO_CONTENT"
    elif any(d in host for d in ("youtube.com", "youtu.be")):
        kind = "DISCUSSION"
    else:
        kind = "UNKNOWN"
    return {"source_class": kind, "firsthand_or_secondary": "UNKNOWN",
            "source_host": host, "evidence_rule": "Page content must be read; snippets alone are candidate leads."}


def full_source_evidence_guard(record: dict[str, Any]) -> bool:
    """Reject a search snippet as source evidence; require extracted page text."""
    status = str(record.get("extraction_status") or "").upper()
    text = str(record.get("extracted_evidence") or record.get("extracted_text") or "").strip()
    return status in {"EXTRACTED", "READ"} and len(text) >= 120


def _extract_json(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text or ""):
        try:
            value, _ = decoder.raw_decode(text[match.start():])
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue
    return None


def _persist_run(row: dict[str, Any]) -> None:
    RUNS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RUNS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")


def single_primary_engine_guard(engine: str, fallback_used: bool = False,
                                fallback_reason: str | None = None) -> bool:
    """Only Hermes is the live primary; local HTML is legal with a recorded cause."""
    if engine == PRIMARY_AUTONOMOUS_ENGINE:
        return not fallback_used
    return engine == "LOCAL_HTML_FALLBACK" and fallback_used and fallback_reason in {
        "HERMES_UNAVAILABLE", "PROVIDER_TIMEOUT", "MCP_UNAVAILABLE",
        "SEARCH_PROVIDER_FAILURE", "EXTRACTION_PROVIDER_FAILURE",
        "HERMES_REPORTED_PROVIDER_FAILURE", "HERMES_UNVERIFIED_SOURCE_OUTPUT",
        "HERMES_STRUCTURED_RESPONSE_INVALID", "oracle_timeout", "ssh_key_missing",
        "empty_oracle_response",
    }


def _verify_source_url(url: str) -> tuple[bool, str]:
    """Reject obvious placeholders and verify the reported public URL resolves.

    This is a provenance sanity check; page reading still comes from Hermes
    web_extract. Inaccessible URLs are not treated as evidence.
    """
    host = (urlsplit(url).hostname or "").lower()
    if host in {"example.com", "www.example.com", "example.org", "www.example.org", "example.net", "www.example.net"} or host.endswith((".test", ".invalid", ".localhost")):
        return False, "PLACEHOLDER_DOMAIN"
    if urlsplit(url).scheme not in {"http", "https"} or not host:
        return False, "INVALID_PUBLIC_URL"
    request = urllib.request.Request(url, headers={"User-Agent": "Nexus-Research-Source-Verification/1.0"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=7, context=_URL_SSL) as response:
            response.read(512)
            return 200 <= response.status < 400, f"HTTP_{response.status}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP_{exc.code}"
    except Exception as exc:
        return False, "UNVERIFIED_URL:" + type(exc).__name__


def _bounded_case_context(case: dict[str, Any]) -> dict[str, Any]:
    """Carry useful objective lineage without serializing an ever-growing case."""
    def clip(value: Any, limit: int = 900) -> str:
        if isinstance(value, str):
            text = value
        else:
            try:
                text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
            except (TypeError, ValueError):
                text = str(value)
        return text[:limit]

    def project(rows: Any, fields: tuple[str, ...], *, count: int = 8,
                field_limit: int = 900) -> list[dict[str, Any]]:
        output = []
        for row in list(rows or [])[-count:]:
            if not isinstance(row, dict):
                output.append({"text": clip(row, field_limit)})
                continue
            output.append({key: clip(row.get(key), field_limit) for key in fields if row.get(key) is not None})
        return output

    results = []
    for row in list(case.get("department_results") or [])[-5:]:
        if not isinstance(row, dict):
            continue
        result_value = row.get("result")
        metrics: Any = None
        if isinstance(result_value, str):
            try:
                decoded = json.loads(result_value)
                metrics = decoded.get("result") or decoded.get("metrics") if isinstance(decoded, dict) else None
            except (TypeError, ValueError):
                pass
        results.append({key: clip(row.get(key), 1800 if key in {"what_was_done", "what_was_learned"} else 700)
            for key in ("result_id", "department", "result_type", "what_was_done", "what_was_learned",
                        "next_recommended_action", "new_questions") if row.get(key) is not None})
        if metrics is not None:
            results[-1]["metrics"] = metrics
    context = {
        "case_id": case.get("case_id"),
        "objective": clip(case.get("objective") or case.get("parent_objective"), 1800),
        "business_or_nexus_goal": clip(case.get("business_or_nexus_goal"), 800),
        "owner_department": case.get("current_owner") or case.get("owner_department"),
        "primary_question": clip(case.get("primary_question"), 1200),
        "open_questions": project(case.get("open_questions"),
            ("question_id", "question", "why_it_matters", "answer_status"), count=12, field_limit=700),
        "answered_questions": project(case.get("answered_questions"),
            ("question_id", "question", "answer", "confidence"), count=6, field_limit=700),
        "findings": project(case.get("findings"),
            ("finding_id", "evidence_type", "summary", "key_findings", "recommendation", "next_action"),
            count=12, field_limit=900),
        "hypotheses": project(case.get("hypotheses"),
            ("hypothesis_id", "hypothesis", "status", "evidence_for", "evidence_against"), count=8, field_limit=700),
        "missing_information": project(case.get("missing_information"),
            ("question", "item", "why_it_matters", "status"), count=12, field_limit=600),
        "recommendations": project(case.get("recommendations"),
            ("recommendation_id", "kind", "reason", "supporting_evidence", "status"), count=8, field_limit=700),
        "department_requests": project(case.get("department_requests"),
            ("request_id", "department", "status", "requested_work", "why_this_department", "expected_output",
             "result_id"), count=8, field_limit=700),
        "latest_department_results": results,
        "next_research_action": clip(case.get("next_research_action") or case.get("next_action"), 1600),
    }
    # Keep a hard ceiling even if a future field is added above.
    serialized = json.dumps(context, ensure_ascii=False, sort_keys=True, default=str)
    if len(serialized) > 36_000:
        context["findings"] = context["findings"][-6:]
        context["answered_questions"] = context["answered_questions"][-3:]
        context["department_requests"] = context["department_requests"][-4:]
    return context


def _research_prompt(question: str, objective_family: str, strategy: dict[str, Any],
                     research_case_id: str | None, originating_goal_id: str | None,
                     mode: str, max_searches: int, max_pages: int) -> str:
    case_context: dict[str, Any] | None = None
    if research_case_id:
        try:
            from research.research_case_engine import get_case
            case = get_case(research_case_id)
            if case:
                case_context = _bounded_case_context(case)
        except Exception:
            case_context = None
    contract = {
        "research_question": question, "objective_family": objective_family,
        "source_strategy": strategy, "research_case_id": research_case_id,
        "originating_goal_id": originating_goal_id, "mode": mode, "existing_case_context": case_context,
        "bounds": {"max_searches": max_searches, "max_pages_to_extract": max_pages},
    }
    return """You are the Nexus Research agent executing one bounded production research question.
Use available governed tools through Hermes. Select tools based on the question: native web_search,
You.com you-search/you-discover when relevant, web_extract for candidate URLs, and existing specialized
tools only when available and pertinent. In this Hermes profile the You.com tool names are namespaced:
you-search is mcp__you_com__you_search and you-discover is mcp__you_com__you_discover. Treat those as
the actual invocable tools; report canonical registry IDs (you-search/you-discover) in tools_selected.
The explicit Hermes execution allowlist includes the you-com MCP server and native web toolset. Do not
mark You.com unavailable unless the actual namespaced tool invocation fails. Do not force a particular
provider. Search results/snippets are
candidate leads, never evidence. Extract/read promising public pages; respect access controls and report
provider failures. Do not invent sources, dates, firsthand status, metrics, or findings. Every source URL/title and
every extracted statement must come from actual tool output in this turn. Never use example.com,
placeholder domains, invented article titles, or memory. If tools return no verifiable sources, return
an empty sources array and a truthful RESEARCH_INCONCLUSIVE conclusion. A weak result is
not proof that a hypothesis is false. Adapt source strategy at least once if source fit/evidence is weak
and budget allows. When a research_case_id is supplied, set question_resolution.directly_answers_current_question
to true only if accepted extracted content directly answers the exact current question; cite the exact accepted
source URLs, give the answer, and list unanswered parts. Related/general evidence does not answer the case
question. Return ONLY one JSON object matching this schema:
{
 "execution_status":"PASS|PARTIAL|PROVIDER_FAILURE",
 "research_question":"...", "evidence_needed":"...",
 "firsthand_evidence_preferred":true,
 "source_classes_planned":[], "tools_planned":[], "cross_check_required":true,
 "stop_condition":"...", "tools_considered":[],
 "tools_selected":[{"tool":"...","provider":"...","status":"USED|UNAVAILABLE|NOT_SELECTED","calls":0,"why_selected":"..."}],
 "searches":[{"query":"...","tool":"...","provider":"...","results":[{"title":"...","url":"...","source_date":null,"snippet":"..."}]}],
 "sources":[{"url":"...","title":"...","source_date":null,"source_class":"...","extraction_status":"EXTRACTED|READ|FAILED","extracted_evidence":"actual page text, concise but substantive","evidence_role":"FIRSTHAND|SECONDHAND|SEO_CONTENT|VENDOR_MARKETING|OFFICIAL_SOURCE|REVIEW|DISCUSSION|FORUM|MARKETPLACE|NEWS|UNKNOWN","why_relevant":"..."}],
 "assessment":{"source_fit":"GOOD|PARTIAL|POOR","evidence_quality":"...","source_diversity":[],"firsthand_count":0,"official_count":0,"marketplace_count":0,"decision_usefulness":"..."},
 "question_resolution":{"directly_answers_current_question":true,"answer":"...","evidence_urls":[],"unanswered_parts":[],"confidence":0.0},
 "followup_questions":[{"question":"...","why_it_matters":"...","best_source_classes":[]}],
 "missing_information":[],
 "conclusion":"FINDING_SUPPORTED|RESEARCH_INCONCLUSIVE|HYPOTHESIS_NOT_SUPPORTED",
 "why_concluded":"...","next_research_action":"..."
}
Only use HYPOTHESIS_NOT_SUPPORTED after appropriate source coverage is sufficient; otherwise use
RESEARCH_INCONCLUSIVE. Report actual calls and URLs. Inputs:\n""" + json.dumps(contract, ensure_ascii=False, sort_keys=True)


def execute_research_question(question: str, objective_family: str = "GENERAL_DISCOVERY",
                              source_strategy: dict[str, Any] | None = None,
                              research_case_id: str | None = None,
                              originating_goal_id: str | None = None, mode: str = "autonomous",
                              timeout_seconds: float = 220, max_searches: int = 4,
                              max_pages: int = 6, hermes_runner=None) -> dict[str, Any]:
    """Run the canonical Hermes research interface and persist an auditable receipt.

    Only actual extracted pages pass as records. Transport/tool failures are
    surfaced as PROVIDER_FAILURE so the existing lane can explicitly fall back.
    """
    q = " ".join(str(question or "").split()).strip()
    strategy = source_strategy or plan_source_strategy(q)
    run_id = "rtl_" + uuid.uuid4().hex[:20]
    started = time.monotonic()
    session = "research-" + hashlib.sha256(run_id.encode()).hexdigest()[:24]
    prompt = _research_prompt(q, objective_family, strategy, research_case_id,
                              originating_goal_id, mode, max_searches, max_pages)
    try:
        if hermes_runner is None:
            from nexus_agent_platform.bridge.oracle_hermes_cli import run_oracle_hermes
            hermes_runner = run_oracle_hermes
        response = hermes_runner(prompt, session, timeout_seconds=timeout_seconds,
                                 request_id=run_id, structured_task=True)
    except Exception as exc:
        response = None
        transport_error = type(exc).__name__ + ":" + str(exc)[:180]
    else:
        transport_error = getattr(response, "error", None)
    text = getattr(response, "response", None) if response is not None else None
    parsed = _extract_json(str(text or ""))
    if not text or getattr(response, "status", "UNAVAILABLE") != "SUCCEEDED":
        result = {"execution_status": "PROVIDER_FAILURE", "provider_error": transport_error or "HERMES_UNAVAILABLE"}
    elif parsed is None:
        result = {"execution_status": "PROVIDER_FAILURE", "provider_error": "HERMES_STRUCTURED_RESPONSE_INVALID"}
    else:
        allowed = {"FINDING_SUPPORTED", "RESEARCH_INCONCLUSIVE", "HYPOTHESIS_NOT_SUPPORTED"}
        conclusion = str(parsed.get("conclusion") or "RESEARCH_INCONCLUSIVE").upper()
        if conclusion not in allowed:
            conclusion = "RESEARCH_INCONCLUSIVE"
        records: list[dict[str, Any]] = []
        rejected_sources: list[dict[str, Any]] = []
        for source in parsed.get("sources") or []:
            if not isinstance(source, dict):
                continue
            record = dict(source)
            record["url"] = str(record.get("url") or "")
            record["title"] = str(record.get("title") or "")
            record["extraction_status"] = str(record.get("extraction_status") or "FAILED").upper()
            record["extracted_evidence"] = str(record.get("extracted_evidence") or "")[:12000]
            record["snippet"] = record["extracted_evidence"][:2400]
            record["source_date"] = record.get("source_date")
            record["published_at"] = record.get("source_date")
            record["domain"] = (urlsplit(record["url"]).hostname or "").lower()
            classified = classify_source(record["url"], record["title"], record["extracted_evidence"])
            record["detected_source_class"] = classified["source_class"]
            # Retain explicit source role, but use conservative local classification
            # for the durable canonical class and never infer firsthand locally.
            record["source_class"] = classified["source_class"]
            role = str(record.get("evidence_role") or "UNKNOWN").upper()
            valid_roles = {"FIRSTHAND", "SECONDHAND", "SEO_CONTENT", "VENDOR_MARKETING", "OFFICIAL_SOURCE", "REVIEW", "DISCUSSION", "FORUM", "MARKETPLACE", "NEWS", "UNKNOWN"}
            record["reported_evidence_role"] = role if role in valid_roles else "UNKNOWN"
            first_person = bool(re.search(r"\b(i|i'm|i've|my|me|we|our|ours)\b", record["extracted_evidence"], re.I))
            reportable_customer_source = classified["source_class"] in {"DISCUSSION", "REVIEW"}
            record["firsthand_or_secondary"] = "FIRSTHAND" if first_person and reportable_customer_source else "SECONDHAND" if classified["source_class"] not in {"UNKNOWN"} else "UNKNOWN"
            record["provider"] = "HERMES_TOOL_LAYER"
            url_ok, url_status = _verify_source_url(record["url"])
            record["url_verification"] = url_status
            if full_source_evidence_guard(record) and url_ok:
                records.append(record)
            else:
                rejected_sources.append({**record, "rejection_reason": "SOURCE_URL_NOT_VERIFIED" if not url_ok else "FULL_SOURCE_EVIDENCE_GUARD_FAILED"})
        searches = parsed.get("searches") if isinstance(parsed.get("searches"), list) else []
        agent_strategy = {"research_question": parsed.get("research_question") or q,
                          "evidence_needed": parsed.get("evidence_needed") or strategy.get("evidence_needed"),
                          "firsthand_evidence_preferred": parsed.get("firsthand_evidence_preferred", strategy.get("firsthand_evidence_preferred")),
                          "source_classes_planned": parsed.get("source_classes_planned") or strategy.get("source_classes_planned", []),
                          "tools_planned": parsed.get("tools_planned") or strategy.get("tools_planned", []),
                          "cross_check_required": parsed.get("cross_check_required", strategy.get("cross_check_required", True)),
                          "stop_condition": parsed.get("stop_condition") or strategy.get("stop_condition"),
                          "why_these_sources": parsed.get("why_these_sources") or strategy.get("why_these_sources", [])}
        result = {**parsed, "agent_source_strategy": agent_strategy,
                  "tools_considered": parsed.get("tools_considered") or strategy.get("tools_planned", []),
                  "execution_status": str(parsed.get("execution_status") or "PASS").upper(),
                  "research_conclusion": conclusion, "records": records, "queries": [str(x.get("query") or "") for x in searches if isinstance(x, dict)],
                  "search_results_returned": sum(len((x.get("results") or [])) for x in searches if isinstance(x, dict)),
                  "searches": searches, "search_candidates": [candidate for search in searches if isinstance(search, dict) for candidate in (search.get("results") or []) if isinstance(candidate, dict)],
                  "sources_opened": records, "rejected_sources": rejected_sources,
                  "screened_out_results": rejected_sources,
                  "status": "COMPLETED" if str(parsed.get("execution_status") or "PASS").upper() in {"PASS", "PARTIAL"} else "FAILED_RETRYABLE",
                  "failed_queries": []}
        resolution = parsed.get("question_resolution") if isinstance(parsed.get("question_resolution"), dict) else {}
        cited_urls = {str(value) for value in (resolution.get("evidence_urls") or [])}
        accepted_urls = {str(row.get("url")) for row in records if row.get("url") and
                         len(str(row.get("extracted_evidence") or "").strip()) >= 120}
        directly_answers = bool(resolution.get("directly_answers_current_question"))
        valid_resolution = directly_answers and bool(str(resolution.get("answer") or "").strip()) \
            and bool(cited_urls) and cited_urls.issubset(accepted_urls)
        resolution_validation = "ACCEPTED" if valid_resolution else "NOT_ANSWERED_BY_ACCEPTED_EXTRACTED_EVIDENCE"
        if research_case_id and valid_resolution:
            try:
                from research.research_case_engine import get_case
                case = get_case(research_case_id) or {}
                family = str(case.get("objective_family") or objective_family).upper()
                if family in {"TRADING", "TRADING_INTELLIGENCE"} and any(term in q.casefold() for term in ("indicator", "script", "phase", "reversal")):
                    anchors = {str(row.get("url") or row.get("source_url")) for row in case.get("sources", [])
                               if str(row.get("source_class") or "").upper() == "TRADINGVIEW_PUBLIC_SCRIPTS"
                               and (row.get("url") or row.get("source_url"))}
                    if anchors and not (anchors & cited_urls):
                        valid_resolution = False
                        resolution_validation = "INDICATOR_SPECIFIC_QUESTION_NEEDS_CASE_INDICATOR_SOURCE"
                if family in {"BUSINESS_OPPORTUNITIES", "CUSTOMER_NEEDS", "CUSTOMER_COMPLAINTS"} and any(term in q.casefold() for term in ("customer demand", "customer problem", "unmet", "complaint", "willingness to pay")):
                    firsthand = {str(row.get("url")) for row in records if row.get("url")
                        and str(row.get("firsthand_or_secondary") or "").upper() == "FIRSTHAND"
                        and str(row.get("source_class") or "").upper() in {"DISCUSSION", "FORUM", "REVIEW"}}
                    if not (firsthand & cited_urls):
                        valid_resolution = False
                        resolution_validation = "CUSTOMER_DEMAND_QUESTION_NEEDS_ACCEPTED_FIRSTHAND_EVIDENCE"
            except Exception:
                valid_resolution = False
                resolution_validation = "CASE_ANSWER_SCOPE_VALIDATION_UNAVAILABLE"
        try:
            resolution_confidence = max(0.0, min(1.0, float(resolution.get("confidence") or 0)))
        except (TypeError, ValueError):
            resolution_confidence = 0.0
        result["question_resolution"] = {
            "directly_answers_current_question": valid_resolution,
            "answer": str(resolution.get("answer") or "")[:5000],
            "evidence_urls": sorted(cited_urls & accepted_urls),
            "unanswered_parts": [str(x)[:500] for x in (resolution.get("unanswered_parts") or [])[:10]],
            "confidence": resolution_confidence,
            "validation": resolution_validation}
        if result["execution_status"] == "PROVIDER_FAILURE":
            result["provider_error"] = "HERMES_REPORTED_PROVIDER_FAILURE"
            result["research_conclusion"] = "RESEARCH_INCONCLUSIVE"
            result["why_concluded"] = "Hermes reported a tool/provider failure; no supported research conclusion can be made from this execution."
        elif rejected_sources and not records:
            # Claimed extractions for invalid/placeholder URLs are provider-integrity failures.
            result["execution_status"] = "PROVIDER_FAILURE"
            result["provider_error"] = "HERMES_UNVERIFIED_SOURCE_OUTPUT"
            result["status"] = "FAILED_RETRYABLE"
            result["research_conclusion"] = "RESEARCH_INCONCLUSIVE"
            result["why_concluded"] = "Hermes claimed extracted sources, but every reported URL failed provenance verification; no evidence was accepted."
    receipt = {"run_id": run_id, "created_at": datetime.now(timezone.utc).isoformat(),
               "engine": "HERMES_TOOL_LAYER", "fallback_used": False,
               "objective_family": objective_family, "research_question": q,
               "source_strategy": result.get("agent_source_strategy", strategy),
               "source_strategy_candidate": strategy, "tools_considered": result.get("tools_considered", []),
               "tools_selected": result.get("tools_selected", []),
               "tools_used": result.get("tools_selected", []), "searches": result.get("searches", []),
               "search_count": len(result.get("searches", [])),
               "sources_opened": [{k: row.get(k) for k in ("url", "title", "source_date", "source_class", "extraction_status", "evidence_role")}
                                  for row in result.get("records", [])],
               "rejected_sources": [{"url": row.get("url"), "title": row.get("title"), "reason": row.get("rejection_reason"), "url_verification": row.get("url_verification")}
                                    for row in result.get("rejected_sources", [])],
               "execution_status": result.get("execution_status"), "research_conclusion": result.get("research_conclusion"),
               "question_resolution": result.get("question_resolution"),
               "source_fit": (result.get("assessment") or {}).get("source_fit", "UNASSESSED"),
               "evidence_quality": (result.get("assessment") or {}).get("evidence_quality", "NO_VERIFIED_EXTRACTED_EVIDENCE"),
               "source_classes_observed": sorted({row.get("source_class", "UNKNOWN") for row in result.get("records", [])}),
               "firsthand_source_count": sum(str(row.get("firsthand_or_secondary", "")).upper() == "FIRSTHAND" for row in result.get("records", [])),
               "official_source_count": sum(row.get("source_class") == "OFFICIAL_SOURCE" for row in result.get("records", [])),
               "marketplace_source_count": sum(row.get("source_class") == "MARKETPLACE" for row in result.get("records", [])),
               "candidate_source_urls": [row.get("url") for row in result.get("search_candidates", []) if row.get("url")],
               "why_concluded": result.get("why_concluded"), "next_research_action": result.get("next_research_action"),
               "provider_error": result.get("provider_error"), "latency_ms": round((time.monotonic() - started) * 1000, 1),
               "hermes_latency_ms": getattr(response, "latency_ms", None) if response is not None else None}
    result["tool_layer_receipt"] = receipt
    _persist_run(receipt)
    if research_case_id:
        # Keep source evidence and conclusions on the objective case. A source
        # remains evidence within that case, never the case's identity.
        try:
            from research.research_case_engine import (add_question, add_source, consume_budget,
                map_research_conclusion, record_finding)
            for source in result.get("records", []):
                add_source(research_case_id, {**source, "source_id": source.get("source_id") or source.get("url"),
                                               "research_execution_id": run_id})
            consume_budget(research_case_id, dimension="research_iterations")
            lookup_units = max(1, len(result.get("searches", [])) + len(result.get("records", [])))
            consume_budget(research_case_id, dimension="source_lookups", amount=lookup_units)
            if result.get("research_conclusion") == "FINDING_SUPPORTED" and result.get("records"):
                record_finding(research_case_id, {"finding_id": "rcf_" + run_id,
                    "summary": result.get("why_concluded") or result.get("assessment", {}).get("decision_usefulness"),
                    "evidence_source_ids": [s.get("url") for s in result.get("records", [])],
                    "research_execution_id": run_id, "evidence_quality": result.get("assessment", {}).get("evidence_quality")})
            if result.get("question_resolution", {}).get("directly_answers_current_question"):
                result["case_persistence_question_answer_eligible"] = True
            if result.get("research_conclusion") == "RESEARCH_INCONCLUSIVE":
                map_research_conclusion(research_case_id, "RESEARCH_INCONCLUSIVE", evidence_paths_exhausted=False,
                                        why=str(result.get("why_concluded") or "Current source strategy did not resolve the case question."))
            for followup in (result.get("followup_questions") or [])[:3]:
                if isinstance(followup, dict) and followup.get("question"):
                    add_question(research_case_id, str(followup["question"]),
                                 why_it_matters=str(followup.get("why_it_matters") or "Important unresolved case evidence."),
                                 best_source_classes=followup.get("best_source_classes") or [])
            result["case_persistence"] = {"case_id": research_case_id, "sources_attached": len(result.get("records", [])),
                                          "followup_questions_added": min(3, len(result.get("followup_questions") or [])),
                                          "objective_case_updated": True}
        except Exception as exc:
            result["case_persistence"] = {"case_id": research_case_id, "objective_case_updated": False,
                                          "error": type(exc).__name__}
    return result
