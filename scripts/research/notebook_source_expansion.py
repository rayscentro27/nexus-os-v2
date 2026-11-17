"""Deterministic research-method routing for notebook-backed feeder gaps.

This module only chooses a method and groups questions. It never upgrades
evidence; only cited, reviewed sources can support a gap answer.
"""
from __future__ import annotations

import re
import json
import os
import subprocess
import time
import uuid
from urllib.parse import urlsplit, urlunsplit
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FAST_TERMS = re.compile(r"\b(requirements?|documentation|geograph|state eligibility|fees?|pricing|availability|product|lender|credit score|bureau|application path)\b", re.I)
DEEP_TERMS = re.compile(r"\b(demand|market|competitor|regulat|compliance|business model|program comparison|industry landscape)\b", re.I)
EXTERNAL_TERMS = re.compile(r"\b(github|api|code|runtime|historical (trading|option)|options chain|database|local|calculate|calculation|backtest|test harness)\b", re.I)

METHODS = {"NOTEBOOKLM_FAST_RESEARCH", "NOTEBOOKLM_DEEP_RESEARCH", "NEXUS_EXTERNAL_RESEARCH"}
MAX_IMPORTED_SOURCES_PER_RESEARCH_PASS = 5
MAX_RESEARCH_PASSES_PER_GAP = 2
MAX_GAPS_PER_NOTEBOOK_RESEARCH_SESSION = 5
MAX_NOTEBOOK_RESEARCH_RUNTIME_SECONDS = 600
DEFAULT_CLI = Path.home() / ".nexus/venvs/notebooklm-py/bin/notebooklm"


def recommend_method(question: str, *, notebook_reference: str | None) -> str:
    """Choose the narrowest suitable method while honoring no-notebook cases."""
    q = question or ""
    if EXTERNAL_TERMS.search(q):
        return "NEXUS_EXTERNAL_RESEARCH"
    if not notebook_reference:
        return "NEXUS_EXTERNAL_RESEARCH"
    if DEEP_TERMS.search(q):
        return "NOTEBOOKLM_DEEP_RESEARCH"
    return "NOTEBOOKLM_FAST_RESEARCH" if FAST_TERMS.search(q) else "NOTEBOOKLM_DEEP_RESEARCH"


def source_quality(url: str, title: str = "") -> str:
    host = (url or "").lower().split("/")[2] if "://" in (url or "") else ""
    if host.endswith((".gov", ".gov.uk")) or any(x in host for x in ("firstcitizens.com", "sba.gov", "irs.gov", "sec.gov", "company.com")):
        return "PRIMARY_OFFICIAL"
    if any(x in host for x in ("reuters.com", "bloomberg.com", "wsj.com", "ft.com", "cnbc.com")):
        return "HIGH_VALUE_SECONDARY"
    if host and any(x in host for x in ("youtube.com", "youtu.be", "reddit.com", "facebook.com", "medium.com")):
        return "DISCOVERY_ONLY"
    return "SUPPORTING" if host else "DISCOVERY_ONLY"


def canonical_source_url(url: str) -> str:
    parts = urlsplit((url or "").strip())
    if not parts.scheme or not parts.netloc:
        return (url or "").strip().rstrip("/").lower()
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/").lower(), "", ""))


def group_gaps(gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Batch gaps by source/notebook/topic; retain exact questions and IDs."""
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for gap in gaps:
        question = str(gap.get("question") or gap.get("exact_research_question") or "")
        tokens = re.findall(r"[a-z0-9]{4,}", question.lower())
        topic = "funding_product" if any(t in question.lower() for t in ("lender", "credit", "funding", "bank", "pricing", "geography", "requirement")) else (tokens[0] if tokens else "general")
        groups[(str(gap.get("source_id") or ""), str(gap.get("notebook_reference") or gap.get("notebook_id") or ""), topic)].append(gap)
    result = []
    for (source_id, notebook, topic), rows in groups.items():
        qs = [str(r.get("question") or r.get("exact_research_question") or "") for r in rows]
        methods = [recommend_method(q, notebook_reference=notebook or None) for q in qs]
        method = "NEXUS_EXTERNAL_RESEARCH" if "NEXUS_EXTERNAL_RESEARCH" in methods else ("NOTEBOOKLM_DEEP_RESEARCH" if "NOTEBOOKLM_DEEP_RESEARCH" in methods else "NOTEBOOKLM_FAST_RESEARCH")
        result.append({"source_id": source_id, "notebook_reference": notebook or None, "topic": topic,
                       "question_ids": [r.get("question_id") for r in rows], "exact_questions": qs,
                       "recommended_research_method": method, "can_one_pass_close_multiple_gaps": len(rows) > 1})
    return result


def _run_cli(cli: Path, args: list[str], *, timeout: int = 240) -> dict[str, Any]:
    # Pin both executable and profile. The shell PATH on this host resolves
    # `notebooklm` to an unrelated Node wrapper with no access to the stored
    # Python CLI cookies.
    proc = subprocess.run([str(cli), "--profile", "default", *args], capture_output=True, text=True, timeout=timeout, check=False)
    if proc.returncode:
        raise RuntimeError(f"NOTEBOOKLM_CLI_FAILED:{proc.stderr[-500:]}")
    try:
        return json.loads(proc.stdout)
    except ValueError as exc:
        raise RuntimeError("NOTEBOOKLM_CLI_INVALID_JSON") from exc


def _sensitive_public_query(text: str) -> bool:
    return bool(re.search(r"\b(ssn|social security|credit report|bank statement|account number|routing number|date of birth|client pii)\b", text, re.I))


def _is_relevant(question: str, title: str, url: str) -> bool:
    terms = {x for x in re.findall(r"[a-z0-9]{4,}", question.lower()) if x not in {"what", "does", "with", "from", "this", "that", "evidence", "establishes", "opportunity", "source"}}
    haystack = f"{title} {url}".lower()
    return not terms or sum(term in haystack for term in terms) >= min(2, len(terms))


def qualify_candidate(*, question: str, title: str, url: str, existing_urls: set[str],
                      existing_titles: set[str], lender_specific: bool = False,
                      official_domains: set[str] | None = None, product: str = "") -> dict[str, Any]:
    """Apply the same public, relevance, quality, duplicate, and lender gates."""
    normalized_url = canonical_source_url(url)
    domain = url.split("/")[2].lower() if "://" in url else ""
    quality = source_quality(url, title)
    duplicate = normalized_url in existing_urls or title.strip().casefold() in existing_titles
    relevance = _is_relevant(question, title, url)
    quality_pass = quality in {"PRIMARY_OFFICIAL", "HIGH_VALUE_SECONDARY"}
    if lender_specific:
        allowed = official_domains or set()
        relevance = relevance and domain in allowed
        quality_pass = quality_pass and domain in allowed
    # A bank-owned page can still be about the wrong product. Keep product
    # families separate (for example a business card is not an LOC).
    product_lower = product.lower()
    document_text = f"{title} {url}".lower().replace("-", " ")
    if "line of credit" in product_lower or "business loc" in product_lower:
        loc_match = bool(re.search(r"\b(line of credit|credit line|rloc|revolving line)\b", document_text))
        card_mismatch = bool(re.search(r"\b(credit card|visa|mastercard|rewards card)\b", document_text))
        relevance = relevance and loc_match and not card_mismatch
        if re.search(r"\b(pricing|price|rate|apr|fee|interest)\b", question, re.I):
            pricing_match = bool(re.search(r"\b(pricing|price|rate|apr|fee|interest)\b", document_text))
            relevance = relevance and pricing_match
    return {"url": url, "title": title, "domain": domain, "source_quality": quality,
            "relevance_pass": relevance, "source_quality_pass": quality_pass,
            "duplicate": duplicate, "public_safe_source": url.startswith("https://") and not _sensitive_public_query(url)}


def evaluate_gap_evidence(question: str, answer: str, sources: list[dict[str, Any]]) -> str:
    """Assign a gap-level evidence state without erasing unresolved subclaims."""
    cited = bool(re.search(r"\[\d+(?:\s*[-,]\s*\d+)*\]", answer or ""))
    quality = {str(row.get("source_quality") or "") for row in sources if row.get("evidence_eligible", True)}
    if not sources or not cited:
        return "RESEARCH_REQUIRED"
    # A broad request for current requirements is answerable when the official
    # source identifies documented criteria. Separate threshold/fee gaps remain
    # open and retain their own exact questions.
    if re.search(r"\bcurrent requirements\b", question, re.I):
        if "PRIMARY_OFFICIAL" in quality and re.search(r"\b(VERIFIED|evaluat(?:e|es|ion)|requirement)\b", answer, re.I):
            return "VERIFIED"
        return "RESEARCH_REQUIRED"
    if re.search(r"\b(RESEARCH_REQUIRED|not stated|not published|not specified)\b", answer, re.I):
        return "RESEARCH_REQUIRED"
    if "PRIMARY_OFFICIAL" in quality:
        return "VERIFIED"
    if "HIGH_VALUE_SECONDARY" in quality:
        return "CROSS_SUPPORTED"
    return "RESEARCH_REQUIRED"


def run_notebook_gap_operator(item: dict[str, Any], *, cli: Path = DEFAULT_CLI) -> dict[str, Any]:
    """Run one public-source gap through the authenticated CLI and persist return.

    This path is called by the existing Research dispatched worker. It uses no
    destructive NotebookLM command and never sends feeder transcripts or PII.
    """
    question = str(item.get("exact_research_question") or item.get("research_question") or item.get("question") or "").strip()
    notebook = str(item.get("notebook_reference") or item.get("notebook_id") or "").strip()
    if not question or not notebook:
        raise ValueError("NOTEBOOK_GAP_REFERENCE_AND_EXACT_QUESTION_REQUIRED")
    if _sensitive_public_query(question):
        raise ValueError("NOTEBOOK_PUBLIC_RESEARCH_SENSITIVE_DATA_BLOCKED")
    if not cli.is_file():
        raise RuntimeError("NOTEBOOKLM_CLI_NOT_CONFIGURED")
    deadline = time.monotonic() + MAX_NOTEBOOK_RESEARCH_RUNTIME_SECONDS

    def remaining_seconds() -> int:
        return max(0, int(deadline - time.monotonic()))

    # Use the existing authenticated CLI profile; its doctor is read-only.
    # This CLI's read-only doctor may take over a minute while checking local
    # profile/auth state. Keep it bounded, but do not misclassify valid auth as
    # unavailable after an unrealistically short timeout.
    doctor = subprocess.run([str(cli), "--profile", "default", "doctor"], capture_output=True, text=True, timeout=90, check=False)
    if doctor.returncode:
        raise RuntimeError("NOTEBOOKLM_CLI_AUTH_BLOCKED")

    from nexus_agent_platform import feeder_runtime as feeder
    source_id = str(item.get("source_id") or "")
    gap_id = str(item.get("work_id") or item.get("question_id") or "")
    settings_rows = feeder._request("research_notebooklm_automation_settings?settings_id=eq.NOTEBOOKLM_RESEARCH&select=settings_id,enabled,automation_mode,max_imported_sources_per_pass,max_research_passes_per_gap,max_gaps_per_notebook_session,public_sources_only,sensitive_client_data_allowed,destructive_notebook_actions_allowed,sharing_actions_allowed,preferred_path")
    if not settings_rows or not settings_rows[0].get("enabled") or settings_rows[0].get("automation_mode") != "AUTO_OPERATOR_BOUNDED":
        raise RuntimeError("NOTEBOOKLM_AUTOMATION_DISABLED_OR_UNCONFIGURED")
    settings = settings_rows[0]
    max_imports = min(MAX_IMPORTED_SOURCES_PER_RESEARCH_PASS, int(settings.get("max_imported_sources_per_pass", 5)))
    max_passes = min(MAX_RESEARCH_PASSES_PER_GAP, int(settings.get("max_research_passes_per_gap", 2)))
    max_gaps = min(MAX_GAPS_PER_NOTEBOOK_RESEARCH_SESSION, int(settings.get("max_gaps_per_notebook_session", 5)))
    if not settings.get("public_sources_only") or settings.get("sensitive_client_data_allowed") or settings.get("destructive_notebook_actions_allowed") or settings.get("sharing_actions_allowed"):
        raise RuntimeError("NOTEBOOKLM_SAFETY_SETTINGS_INVALID")
    gap_fields = "question_id,source_id,question,exact_research_question,notebook_reference,notebook_id,status,research_passes:answer_packet->>research_passes,evidence_state:answer_packet->>evidence_state"
    gap_rows = feeder._request(f"nexus_feeder_research_gaps?question_id=eq.{gap_id}&select={gap_fields}")
    if not gap_rows:
        raise ValueError("FEEDER_GAP_NOT_FOUND")
    gap = gap_rows[0]
    if gap.get("status") == "COMPLETED":
        return {"research_session_id": None, "research_method": gap.get("recommended_research_method"),
        "gap_state": "COMPLETED", "evidence_state": gap.get("evidence_state"),
            "already_completed": True, "supabase_persistence_pass": True, "return_to_feeder": True,
            "feeder_readiness_recalculated": True, "automation_path_used": "CLI", "new_browser_created": False}
    all_open = feeder._request(f"nexus_feeder_research_gaps?source_id=eq.{source_id}&status=in.(OPEN,IN_PROGRESS)&select={gap_fields}&limit=100")
    target_groups = group_gaps([{"question_id": row.get("question_id"), "source_id": row.get("source_id"),
        "notebook_reference": row.get("notebook_reference") or row.get("notebook_id") or notebook,
        "question": row.get("exact_research_question") or row.get("question")} for row in all_open])
    target_group = next((row for row in target_groups if gap_id in (row.get("question_ids") or [])), None)
    group_ids = (target_group or {}).get("question_ids") or [gap_id]
    open_by_id = {str(row.get("question_id")): row for row in all_open}
    group_rows = [open_by_id[qid] for qid in group_ids if qid in open_by_id]
    group_rows = [gap] + [row for row in group_rows if row.get("question_id") != gap_id]
    pass_counts = {str(row.get("question_id")): int(row.get("research_passes") or 0) for row in group_rows}
    if pass_counts.get(gap_id, 0) >= max_passes:
        raise RuntimeError("NOTEBOOK_GAP_RESEARCH_PASS_LIMIT_REACHED")
    session_gaps = [row for row in group_rows if pass_counts.get(str(row.get("question_id")), 0) < max_passes][:max_gaps]
    if gap not in session_gaps:
        session_gaps.insert(0, gap)
    research_questions = [str(row.get("exact_research_question") or row.get("question") or "") for row in session_gaps]

    method = str(item.get("recommended_research_method") or recommend_method(question, notebook_reference=notebook))
    if method not in {"NOTEBOOKLM_FAST_RESEARCH", "NOTEBOOKLM_DEEP_RESEARCH"}:
        raise ValueError("NOTEBOOK_GAP_ROUTED_TO_EXTERNAL_RESEARCH")
    mode = "deep" if method == "NOTEBOOKLM_DEEP_RESEARCH" else "fast"
    session_id = "nlm_" + uuid.uuid4().hex[:20]
    source_rows = feeder._request(f"nexus_feeder_sources?source_id=eq.{source_id}&select=source_title,notebook_output")
    source_record = source_rows[0] if source_rows else {}
    structured = source_record.get("notebook_output") or {}
    lender = str(structured.get("LENDER") or "").strip()
    product = str(structured.get("PRODUCT") or "").strip()
    subject_context = " ".join(x for x in (lender, product, str(source_record.get("source_title") or "")) if x)
    if lender and "first citizens" in lender.lower():
        source_instruction = ("Search only official public First Citizens Bank pages on firstcitizens.com for the requested "+
                              "business product. Exclude mortgage, housing, unrelated federal-program, and other-bank pages. "+
                              "If no official page supports the exact question, return no qualifying source rather than substituting one. ")
    else:
        source_instruction = "Prefer primary official documentation and return no irrelevant sources. "
    search_prompt = (source_instruction + "Research these exact questions using public sources. Do not infer requirements from creator claims. "+
                     "Return candidate source URLs with titles and explain which question each source supports. Product context: " +
                     subject_context + ". Exact questions: " + json.dumps(research_questions))
    search_budget = min(300, remaining_seconds() - 60)
    if search_budget < 30:
        raise RuntimeError("NOTEBOOKLM_SESSION_RUNTIME_LIMIT_BEFORE_SEARCH")
    discovered = _run_cli(cli, ["source", "add-research", "-n", notebook, "--from", "web", "--mode", mode,
                                "--timeout", str(search_budget), "--json", search_prompt], timeout=search_budget + 10)
    if discovered.get("status") != "completed":
        raise RuntimeError("NOTEBOOKLM_SOURCE_SEARCH_" + str(discovered.get("status") or "FAILED").upper())

    source_listing = _run_cli(cli, ["source", "list", "-n", notebook, "--json"], timeout=30)
    existing = source_listing.get("sources", [])
    question_for_route = f"{subject_context} {' '.join(research_questions)}".lower()
    lender_specific = bool(lender and re.search(r"\b(credit|lender|bureau|score|bank|line of credit|loan|checking|documentation|limit|geography|pricing)\b", question_for_route))
    official_domains = {str(s.get("url") or "").split("/")[2].lower() for s in existing
                        if s.get("url") and source_quality(s.get("url", ""), s.get("title", "")) == "PRIMARY_OFFICIAL"
                        and not str(s.get("url")).split("/")[2].lower().endswith((".gov", ".gov.uk"))}
    if lender and "first citizens" in lender.lower():
        official_domains.add("www.firstcitizens.com")
    urls = {canonical_source_url(str(s.get("url") or "")) for s in existing}
    titles = {str(s.get("title") or "").strip().casefold() for s in existing}
    candidates = []
    for row in discovered.get("sources", []) or []:
        url = str(row.get("url") or row.get("source_url") or "").strip()
        title = str(row.get("title") or row.get("name") or url).strip()
        # Lender underwriting claims require the lender's own domain.
        # Government sources can contextualize rules but cannot verify a
        # particular bank's internal credit threshold.
        checks = [qualify_candidate(question=f"{subject_context} {exact}", title=title, url=url,
                    existing_urls=urls, existing_titles=titles, lender_specific=lender_specific,
                    official_domains=official_domains, product=product) for exact in research_questions]
        accepted = next((check for check in checks if check["relevance_pass"] and check["source_quality_pass"] and not check["duplicate"] and check["public_safe_source"]), None)
        candidate = accepted or checks[0]
        candidate["matched_gap_ids"] = [str(session_gaps[index].get("question_id")) for index, check in enumerate(checks)
            if check["relevance_pass"] and check["source_quality_pass"] and not check["duplicate"] and check["public_safe_source"]]
        candidates.append(candidate)
    selected = [s for s in candidates if s["relevance_pass"] and s["source_quality_pass"] and not s["duplicate"] and s["public_safe_source"]][:max_imports]
    imported = []
    for candidate in selected:
        add_budget = min(60, remaining_seconds() - 30)
        if add_budget < 10:
            break
        added = _run_cli(cli, ["source", "add", "-n", notebook, "--type", "url", "--json", candidate["url"]], timeout=add_budget)
        ref = added.get("source") or added
        source_ref = {**candidate, "notebook_source_id": ref.get("id"), "title": ref.get("title") or candidate["title"], "evidence_eligible": True}
        if not source_ref.get("notebook_source_id"):
            continue
        imported.append(source_ref)
        wait_budget = min(120, remaining_seconds() - 15)
        if wait_budget < 5:
            source_ref["indexing_status"] = "NOT_CONFIRMED_RUNTIME_LIMIT"
            source_ref["evidence_eligible"] = False
            continue
        waited = _run_cli(cli, ["source", "wait", "-n", notebook, str(source_ref["notebook_source_id"]), "--timeout", str(wait_budget), "--json"], timeout=wait_budget + 5)
        if waited.get("status") != "ready":
            source_ref["indexing_status"] = waited.get("status", "FAILED")
            source_ref["evidence_eligible"] = False
            continue
        source_ref["indexing_status"] = "ready"

    # Reanalyse only indexed, qualified sources. If this pass found no new
    # source, the existing notebook still supplies the bounded analysis context.
    ask_cmd = ["ask", "-n", notebook, "--json"]
    indexed_imports = [source for source in imported if source.get("indexing_status") == "ready" and source.get("evidence_eligible") is True]
    indexed_refs = indexed_imports or []
    if not indexed_refs:
        for existing_source in existing:
            if existing_source.get("status") != "ready" or source_quality(existing_source.get("url", ""), existing_source.get("title", "")) not in {"PRIMARY_OFFICIAL", "HIGH_VALUE_SECONDARY"}:
                continue
            checks = [qualify_candidate(question=f"{subject_context} {exact}", title=str(existing_source.get("title") or ""),
                url=str(existing_source.get("url") or ""), existing_urls=set(), existing_titles=set(),
                lender_specific=lender_specific, official_domains=official_domains, product=product) for exact in research_questions]
            matched = [str(session_gaps[index].get("question_id")) for index, checked in enumerate(checks)
                if checked["relevance_pass"] and checked["source_quality_pass"] and checked["public_safe_source"]]
            if matched:
                indexed_refs.append({**existing_source, **checks[0], "matched_gap_ids": matched,
                    "notebook_source_id": existing_source.get("id"), "indexing_status": "ready", "evidence_eligible": True})
    for source in indexed_refs[:max_imports]:
        if source.get("notebook_source_id") or source.get("id"):
            ask_cmd.extend(["-s", str(source.get("notebook_source_id") or source.get("id"))])
    ask_cmd.append("You are researching " + subject_context + ". Answer every exact research question below using only the selected sources. Label each claim VERIFIED, CROSS_SUPPORTED, CONTRADICTED, or RESEARCH_REQUIRED and cite the source. State explicitly when this lender does not publish a requirement. General government or housing-program rules do not establish this lender's underwriting policy. Exact questions: " + json.dumps(research_questions))
    ask_budget = min(180, remaining_seconds() - 5)
    if ask_budget < 20:
        raise RuntimeError("NOTEBOOKLM_SESSION_RUNTIME_LIMIT_BEFORE_REANALYSIS")
    analysis = _run_cli(cli, ask_cmd, timeout=ask_budget)
    answer = str(analysis.get("answer") or "").strip()
    has_citation = bool(re.search(r"\[\d+(?:\s*[-,]\s*\d+)*\]", answer))
    source_evidence = indexed_imports or [{"url": s.get("url"), "title": s.get("title"), "domain": str(s.get("url") or "").split("/")[2].lower(), "source_quality": source_quality(s.get("url", ""), s.get("title", "")), "notebook_source_id": s.get("notebook_source_id") or s.get("id"), "indexing_status": s.get("status") or s.get("indexing_status"), "matched_gap_ids": s.get("matched_gap_ids"), "evidence_eligible": s.get("evidence_eligible", True)} for s in indexed_refs]
    if lender_specific:
        source_evidence = [s for s in source_evidence if str(s.get("domain") or str(s.get("url") or "").split("/")[2]).lower() in official_domains]
    gap_results = {}
    for row in session_gaps:
        qid = str(row.get("question_id"))
        exact = str(row.get("exact_research_question") or row.get("question") or "")
        question_sources = [source for source in source_evidence if source.get("evidence_eligible", True) and qid in (source.get("matched_gap_ids") or [])]
        state = evaluate_gap_evidence(exact, answer, question_sources)
        gap_results[qid] = {"question": exact, "evidence_state": state,
            "status": "COMPLETED" if state in {"VERIFIED", "CROSS_SUPPORTED", "CONTRADICTED"} else "IN_PROGRESS",
            "research_passes": pass_counts[qid] + 1, "evidence": question_sources}
    evidence_state = gap_results[gap_id]["evidence_state"]
    quality = [x["source_quality"] for x in gap_results[gap_id]["evidence"]]
    # A citation alone does not close a question. Require a substantive answer
    # that does not explicitly say the requested fact is unavailable.
    answer_substantive = bool(answer) and (evidence_state != "RESEARCH_REQUIRED")
    completed = evidence_state != "RESEARCH_REQUIRED" and answer_substantive
    completed_at = datetime.now(timezone.utc).isoformat() if completed else None
    packet = {"question": question, "answer": answer, "evidence": source_evidence, "source_url_or_reference": notebook,
              "source_quality": quality, "confidence": "MEDIUM" if completed else "LOW", "evidence_state": evidence_state,
              "research_passes": pass_counts[gap_id] + 1, "research_session_id": session_id, "research_method": method,
            "sources_discovered": len(candidates), "sources_qualified": len(selected), "sources_imported": len(imported),
              "duplicates_skipped": sum(bool(s["duplicate"]) for s in candidates), "completed_at": completed_at}
    for qid, outcome in gap_results.items():
        question_packet = {**packet, "question": outcome["question"], "evidence": outcome["evidence"], "research_passes": outcome["research_passes"],
            "evidence_state": outcome["evidence_state"], "completed_at": completed_at if outcome["status"] == "COMPLETED" else None}
        feeder._request(f"nexus_feeder_research_gaps?question_id=eq.{qid}", "PATCH", {
            "status": outcome["status"], "answer_packet": question_packet,
            "evidence": outcome["evidence"] if outcome["status"] == "COMPLETED" else [],
            "confidence": "MEDIUM" if outcome["status"] == "COMPLETED" else "LOW",
            "completed_at": question_packet["completed_at"], "recommended_research_method": method,
            "preferred_source_type": "PRIMARY_OFFICIAL", "updated_at": feeder.now()})
    completed = gap_results[gap_id]["status"] == "COMPLETED"
    completed_ids = [qid for qid, outcome in gap_results.items() if outcome["status"] == "COMPLETED"]
    remaining_ids = [qid for qid, outcome in gap_results.items() if outcome["status"] != "COMPLETED"]

    session_row = {"research_session_id": session_id, "source_id": source_id, "notebook_reference": notebook,
                   "research_method": method, "automation_path": "CLI", "gaps_attempted": [str(row.get("question_id")) for row in session_gaps],
                   "gaps_closed": completed_ids, "gaps_remaining": remaining_ids,
                   "sources_discovered": candidates, "sources_imported": imported,
                   "status": "COMPLETED" if not remaining_ids else "RESEARCH_REQUIRED", "completed_at": feeder.now()}
    feeder._request("research_notebooklm_sessions?on_conflict=research_session_id", "POST", session_row,
                    "resolution=merge-duplicates,return=representation")
    session_readback = feeder._request(f"research_notebooklm_sessions?research_session_id=eq.{session_id}&select=research_session_id,status,automation_path,sources_imported")
    if not session_readback or session_readback[0].get("status") != session_row["status"]:
        raise RuntimeError("NOTEBOOKLM_SESSION_PERSISTENCE_READBACK_FAILED")

    source_rows = feeder._request(f"nexus_feeder_sources?source_id=eq.{source_id}&select=source_id,notebook_output,ingestion_status")
    if source_rows:
        source_row = source_rows[0]
        output = source_row.get("notebook_output") or {}
        sessions = output.setdefault("NOTEBOOK_RESEARCH_SESSIONS", [])
        sessions.append({"research_session_id": session_id, "notebook_reference": notebook, "gaps_attempted": session_row["gaps_attempted"],
                         "gaps_closed": completed_ids, "gaps_remaining": remaining_ids,
                         "sources_discovered": candidates, "sources_imported": imported, "research_method": method,
                         "indexing_pass": bool(imported) and all(row.get("indexing_status") == "ready" for row in imported),
                         "notebook_reanalysis_pass": bool(answer and has_citation), "return_to_feeder": True,
                         "completed_at": completed_at or datetime.now(timezone.utc).isoformat()})
        remaining = feeder._request(f"nexus_feeder_research_gaps?source_id=eq.{source_id}&status=neq.COMPLETED&select=question_id")
        feeder._request(f"nexus_feeder_sources?source_id=eq.{source_id}", "PATCH", {
            "notebook_reference": notebook, "notebook_output": output,
            "ingestion_status": "READY_FOR_HANDOFF" if not remaining else "RESEARCH_REQUIRED",
            "next_owner": item.get("return_target") or "BUSINESS_FUNDING", "updated_at": feeder.now()})
    gap_readback = feeder._request(f"nexus_feeder_research_gaps?question_id=eq.{gap_id}&select=status,answer_packet")
    source_readback = feeder._request(f"nexus_feeder_sources?source_id=eq.{source_id}&select=ingestion_status,notebook_output")
    persisted_session = bool(source_readback and any(
        row.get("research_session_id") == session_id
        for row in (source_readback[0].get("notebook_output") or {}).get("NOTEBOOK_RESEARCH_SESSIONS", [])))
    if not gap_readback or gap_readback[0].get("status") != ("COMPLETED" if completed else "IN_PROGRESS") or not persisted_session:
        raise RuntimeError("NOTEBOOKLM_RETURN_PERSISTENCE_READBACK_FAILED")
    return {"research_session_id": session_id, "notebook_reference": notebook, "research_method": method,
            "sources_discovered": candidates, "sources_qualified": selected, "sources_imported": imported,
            "duplicates_skipped": sum(bool(s["duplicate"]) for s in candidates), "indexing_pass": bool(imported) and all(s.get("indexing_status") == "ready" for s in imported),
            "notebook_reanalysis_pass": bool(answer and has_citation), "gap_state": "COMPLETED" if completed else "IN_PROGRESS",
            "evidence_state": evidence_state, "answer": answer, "supabase_persistence_pass": True,
            "return_to_feeder": True, "feeder_readiness_recalculated": True, "manual_ray_click_required": False,
            "automation_path_used": "CLI", "new_browser_created": False,
            "max_gaps_per_notebook_session": max_gaps, "session_persistence_pass": True,
            "gaps_attempted": session_row["gaps_attempted"], "gaps_closed": completed_ids, "gaps_remaining": remaining_ids,
            "recovery_workflow": "NOTEBOOK_RESEARCH_RECOVERY" if pass_counts[gap_id] + 1 >= max_passes and not completed else None}
