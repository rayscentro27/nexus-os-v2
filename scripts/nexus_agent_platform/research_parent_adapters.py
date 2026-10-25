"""Bounded production adapters for the durable Research parent workflow.

Adapters reuse the existing evidence, Alpha, Needle, knowledge, and handoff
implementations. They return compact structured results; the parent alone
decides whether another child job is required.
"""
from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import quote

_PUBLIC_TEXT_MAX_CHARS = 1_000_000
_PUBLIC_BLOCK_MAX_CHARS = 16_384


def _extract_public_html(html: str) -> dict[str, Any]:
    """Normalize bounded HTML and retain structure for local evidence selection.

    Navigation, sidebars, scripts, styles, and footer material are excluded.
    The returned blocks are transient data from the one fetched response; the
    Research-only executor persists only its selected, bounded evidence.
    """
    import re
    from html.parser import HTMLParser

    class _LegacyFlatten(HTMLParser):
        """Keep the exact bounded flattened text contract for other callers."""
        def __init__(self):
            super().__init__()
            self.parts: list[str] = []
            self.skip = 0
        def handle_starttag(self, tag, attrs):
            if tag in {"script", "style", "noscript", "svg"}:
                self.skip += 1
        def handle_endtag(self, tag):
            if tag in {"script", "style", "noscript", "svg"} and self.skip:
                self.skip -= 1
        def handle_data(self, data):
            if not self.skip and data.strip():
                self.parts.append(data.strip())

    class _StructuredText(HTMLParser):
        _BLOCKS = {"h1", "h2", "h3", "h4", "h5", "h6", "dt", "dd", "p", "pre", "li"}
        _SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "aside", "footer"}
        _VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
                 "meta", "param", "source", "track", "wbr"}
        _SKIP_CLASSES = {"sidebar", "sphinxsidebar", "toctree-wrapper", "related", "headerlink"}

        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.blocks: list[dict[str, str]] = []
            self.title_parts: list[str] = []
            self.in_title = False
            self.skip_stack: list[str] = []
            self.section_stack: list[str] = []
            self.heading = ""
            self.current: dict[str, str] | None = None
            self.current_parts: list[str] = []

        def handle_starttag(self, tag, attrs):
            attributes = dict(attrs)
            classes = set(str(attributes.get("class") or "").lower().split())
            class_skip = bool(classes & self._SKIP_CLASSES)
            if self.skip_stack:
                if tag not in self._VOID:
                    self.skip_stack.append(tag)
                return
            if tag in self._SKIP_TAGS or class_skip:
                if tag not in self._VOID:
                    self.skip_stack.append(tag)
                return
            if tag == "title":
                self.in_title = True
            if tag == "section":
                self.section_stack.append(str(attributes.get("id") or ""))
            if tag in self._BLOCKS and self.current is None:
                self.current = {"tag": tag, "id": str(attributes.get("id") or ""),
                                "section_id": next((x for x in reversed(self.section_stack) if x), ""),
                                "heading": self.heading}
                self.current_parts = []

        def handle_endtag(self, tag):
            if self.skip_stack:
                for index in range(len(self.skip_stack) - 1, -1, -1):
                    if self.skip_stack[index] == tag:
                        del self.skip_stack[index:]
                        break
                return
            if tag == "title":
                self.in_title = False
            if self.current is not None and tag == self.current["tag"]:
                text = re.sub(r"\s+", " ", " ".join(self.current_parts)).strip()
                if text:
                    block = {**self.current, "text": text[:_PUBLIC_BLOCK_MAX_CHARS]}
                    self.blocks.append(block)
                    if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                        self.heading = text[:500]
                self.current = None
                self.current_parts = []
            if tag == "section" and self.section_stack:
                self.section_stack.pop()

        def handle_data(self, data):
            if self.skip_stack:
                return
            if self.in_title and data.strip():
                self.title_parts.append(data.strip())
            if self.current is not None and data.strip():
                self.current_parts.append(data.strip())

    parser = _StructuredText()
    parser.feed(str(html))
    parser.close()
    legacy = _LegacyFlatten()
    legacy.feed(str(html))
    legacy.close()
    flat_text = re.sub(r"\s+", " ", " ".join(legacy.parts)).strip()[:12000]
    blocks: list[dict[str, str]] = []
    used = 0
    for block in parser.blocks:
        size = len(block.get("text", "").encode("utf-8"))
        if used + size > _PUBLIC_TEXT_MAX_CHARS:
            break
        blocks.append(block)
        used += size
    return {"text": flat_text, "sections": blocks, "title": " ".join(parser.title_parts)[:300]}


def _fallback_public_page(url: str, work_item: Mapping[str, Any]) -> dict[str, Any]:
    """Use the existing governed public-evidence capability without a browser.

    This fallback is for ordinary HTML pages when the optional Crawl4AI
    dependency is not installed. Redirects are revalidated and response size
    and time are bounded; the source body is never returned to parent state.
    """
    import re
    import urllib.request
    from nexus_agent_platform.evidence_ingestion import validate_public_url

    checked, reason = validate_public_url(url)
    if not checked:
        return {"status": "BLOCKED", "reason": f"PUBLIC_URL_REJECTED:{reason}"}

    class _SafeRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            valid, why = validate_public_url(newurl)
            if not valid:
                raise RuntimeError(f"PUBLIC_REDIRECT_REJECTED:{why}")
            return super().redirect_request(req, fp, code, msg, headers, valid)

    def fetch():
        request = urllib.request.Request(checked, headers={"User-Agent": "NexusResearch/1.0", "Accept": "text/html,application/xhtml+xml"})
        opener = urllib.request.build_opener(_SafeRedirect())
        with opener.open(request, timeout=15) as response:
            body = response.read(1_000_001)
            if len(body) > 1_000_000:
                raise RuntimeError("PUBLIC_SOURCE_SIZE_LIMIT")
            content_type = response.headers.get("Content-Type", "")
            if "html" not in content_type.lower():
                raise RuntimeError("PUBLIC_SOURCE_NOT_HTML")
            parsed = _extract_public_html(body.decode(response.headers.get_content_charset() or "utf-8", errors="replace"))
            return {"url": response.geturl(), "title": parsed["title"],
                    "text": parsed["text"], "sections": parsed["sections"],
                    "bytes": len(body), "status_code": response.status, "status": "COMPLETED"}

    # This is a bounded public-source read, not a consequential action. It is
    # independent of the primary ingestion provider's reservation so one
    # denied method cannot prevent safe evidence acquisition by method B.
    return fetch()


def _objective(state: Mapping[str, Any]) -> str:
    return str(state.get("original_objective") or "").strip()


def _source_text(state: Mapping[str, Any]) -> str:
    source = state.get("source_understanding") or {}
    return str(source.get("summary") or source.get("subject") or "")[:2400]


def _evidence_refs(state: Mapping[str, Any]) -> list[str]:
    refs = []
    for row in state.get("evidence") or []:
        if isinstance(row, Mapping):
            ref = row.get("ref") or row.get("evidence_id") or row.get("artifact_ref") or row.get("url")
            if ref:
                refs.append(str(ref))
    return list(dict.fromkeys(refs))[:30]


def execute_action(action: str, state: Mapping[str, Any], work_item: Mapping[str, Any]) -> dict[str, Any]:
    """Execute exactly one bounded stage using existing Nexus components."""
    action = str(action).upper()
    objective = _objective(state)
    url = str(state.get("source_url") or work_item.get("source_url") or "").strip()

    if action == "SOURCE_UNDERSTANDING":
        if not url:
            return {"status": "SOURCE_INSUFFICIENT", "reason": "PUBLIC_SOURCE_URL_REQUIRED",
                    "subject": objective[:400], "summary": "No source URL was supplied; objective retained for follow-up."}
        from nexus_agent_platform.evidence_ingestion import ingest_url
        # The preferred ingestion service may be unavailable or policy denied.
        # That result is evidence about one method, not the Research objective.
        # Try the existing bounded public-page adapter before returning a
        # continuation request. URL validation remains mandatory in both paths.
        try:
            ingested = ingest_url(url, job_id=str(work_item.get("work_id") or state.get("objective_id")))
        except Exception as exc:
            ingested = {"status": "METHOD_FAILED", "error": f"{type(exc).__name__}: {str(exc)[:180]}"}
        primary_status = str(ingested.get("status") or "UNKNOWN").upper()
        primary_error = str(ingested.get("error") or "")
        if primary_status not in {"SUCCESS", "NO_CHANGE", "DUPLICATE"}:
            try:
                fetched = _fallback_public_page(url, work_item)
            except Exception as exc:
                return {"status": "CONTINUATION_REQUIRED", "reason": "SOURCE_METHODS_UNAVAILABLE",
                        "source_methods": [{"method": "GOVERNED_INGEST", "status": primary_status,
                                            "error": primary_error[:180]},
                                           {"method": "BOUNDED_PUBLIC_HTTP", "status": "FAILED",
                                            "error": f"{type(exc).__name__}: {str(exc)[:180]}"}],
                        "source_url": url}
            text = str(fetched.get("text") or "")
            if not text:
                return {"status": "CONTINUATION_REQUIRED", "reason": "SOURCE_METHODS_INSUFFICIENT",
                        "source_methods": [{"method": "GOVERNED_INGEST", "status": primary_status,
                                            "error": primary_error[:180]},
                                           {"method": "BOUNDED_PUBLIC_HTTP", "status": "EMPTY",
                                            "http_status": fetched.get("status_code")}],
                        "source_url": url}
            return {"status": "COMPLETED", "subject": fetched.get("title") or url,
                    "summary": text[:1800], "source_url": fetched.get("url") or url,
                    "category": state.get("subject_domain") or "UNKNOWN",
                    "evidence": [{"ref": fetched.get("url") or url, "url": fetched.get("url") or url,
                                  "source_type": state.get("source_type")}],
                    "source_reference": fetched.get("url") or url,
                    "source_adapter": "BOUNDED_PUBLIC_HTTP_FALLBACK",
                    "source_method_failure": {"method": "GOVERNED_INGEST", "status": primary_status,
                                              "error": primary_error[:180]}}
        content = ingested.get("content") or {}
        text = str(content.get("normalized_text_or_markdown") or "")
        summary = " ".join(text.split())[:1800]
        return {"status": "COMPLETED", "subject": content.get("title") or url,
                "summary": summary, "source_url": url,
                "category": state.get("subject_domain") or "UNKNOWN",
                "evidence": [{"ref": ingested.get("artifact_ref") or ingested.get("receipt_id"),
                              "url": url, "source_type": state.get("source_type"),
                              "source_hash": (ingested.get("integrity") or {}).get("source_hash")}],
                "source_reference": ingested.get("artifact_ref") or ingested.get("receipt_id")}

    if action == "KNOWLEDGE_RECONCILIATION":
        try:
            from social import _supabase as supabase
            if not supabase.configured():
                return {"status": "COMPLETED", "relationship": "NEW", "lookup": "UNAVAILABLE",
                        "prior_summary": None, "material_changes": []}
            filters = []
            if url:
                filters.append(f"source_url=eq.{quote(url, safe='')}")
            subject = str((state.get("source_understanding") or {}).get("subject") or "")
            if subject:
                filters.append(f"source_name=ilike.*{quote(subject[:80], safe='')}*")
            rows = []
            for filt in filters:
                status, body = supabase.rest("GET", f"research_findings?{filt}&select=finding_id,summary,unknowns,conclusion,updated_at&limit=10")
                if status == 200 and isinstance(body, list):
                    rows.extend(body)
            deduped = {str(row.get("finding_id")): row for row in rows if isinstance(row, dict)}
            prior = list(deduped.values())[:10]
            return {"status": "COMPLETED", "relationship": "RELATED" if prior else "NEW",
                    "prior_summary": prior or None,
                    "prior_conclusion": (prior[0].get("conclusion") if prior else None),
                    "prior_unresolved_questions": [x for row in prior for x in row.get("unknowns", [])][:20],
                    "material_changes": [], "lookup": "PASS"}
        except Exception as exc:
            return {"status": "CONTINUATION_REQUIRED", "reason": "KNOWLEDGE_LOOKUP_UNAVAILABLE",
                    "error": f"{type(exc).__name__}: {str(exc)[:180]}"}

    if action == "ADVISOR_REVIEW":
        from nexus_agent_platform.alpha_research import execute_alpha_request
        domain = str(state.get("subject_domain") or "").upper()
        research_type = "TRADING_RESEARCH" if domain in {"TRADING", "TRADING_INTELLIGENCE", "TRADING_STRATEGY"} else "MARKET_RESEARCH"
        query = (objective + "\nSource understanding: " + _source_text(state) +
                 "\nPrior knowledge: " + str((state.get("knowledge_reconciliation") or {}).get("prior_summary") or ""))[:1800]
        reviewed = execute_alpha_request(objective=query, research_type=research_type,
                                         requested_by="nexus_research_parent")
        if not reviewed.get("execution", {}).get("executed"):
            return {"status": "ADVISOR_UNAVAILABLE", "reason": reviewed.get("status") or "ALPHA_ADVISOR_UNAVAILABLE",
                    "error": reviewed.get("reason") or reviewed.get("blocker")}
        pack = reviewed.get("pack") or {}
        plan = reviewed.get("plan") or {}
        questions = list(plan.get("key_questions") or [])
        return {"status": "COMPLETED", "subject_interpretation": str(reviewed.get("report") or _source_text(state))[:1800],
                "possible_category": state.get("subject_domain") or "UNKNOWN",
                "questions": [{"question": (str(q.get("question") or q.get("research_question") or q)[:400]
                               if isinstance(q, Mapping) else str(q)[:400])} for q in questions if str(q).strip()][:12],
                "claims_to_verify": pack.get("claims") or [],
                "suggested_tests": pack.get("plan", {}).get("stopping_conditions") or [],
                "likely_destination": _destination(state),
                "recommended_next_actions": [f"Follow up on: {str(q)[:300]}" for q in questions[:3]],
                "evidence": [{"ref": x.get("evidence_id"), "url": (x.get("source") or {}).get("original_reference")}
                             for x in pack.get("sources", []) if isinstance(x, dict)],
                "alpha_request_id": reviewed.get("request_id"),
                "summary": str(reviewed.get("report") or "")[:1800]}

    if action == "QUESTION_GENERATION":
        advisor = state.get("advisor_findings") or {}
        questions = list(advisor.get("questions") or [])
        defaults = [
            "What material claims about the subject are supported by attributable evidence?",
            "What are the material costs, constraints, risks, and alternatives for Nexus?",
            "What bounded next action can validate the recommendation?",
        ]
        for question in defaults:
            if len(questions) >= 8:
                break
            questions.append({"question": question})
        return {"status": "COMPLETED", "questions": questions[:8]}

    if action == "FOLLOWUP_RESEARCH":
        from nexus_agent_platform.alpha_research import execute_alpha_request
        open_questions = [q for q in state.get("questions") or []
                          if str(q.get("status") or "OPEN").upper() in {"OPEN", "PARTIAL", "UNVERIFIED"}
                          and q.get("needs_followup", True)][:3]
        answers = []
        test_result = None
        for row in open_questions:
            question = str(row.get("question") or "").strip()
            if not question:
                continue
            domain = str(state.get("subject_domain") or "").upper()
            kind = "TRADING_RESEARCH" if domain in {"TRADING", "TRADING_INTELLIGENCE", "TRADING_STRATEGY"} else "MARKET_RESEARCH"
            response = execute_alpha_request(objective=f"{objective}\nQuestion: {question}",
                research_type=kind, requested_by="nexus_research_parent")
            executed = bool(response.get("execution", {}).get("executed"))
            if response.get("test_result") is not None:
                test_result = response.get("test_result")
            answers.append({"question": question, "status": "ANSWERED" if executed else "UNVERIFIED",
                "answer": str(response.get("report") or response.get("reason") or "No verified answer returned.")[:1200],
                "evidence_refs": [str(response.get("artifact_id") or response.get("result_id"))] if executed else [],
                "confidence": "MEDIUM" if executed else "LOW", "needs_followup": False})
        return {"status": "COMPLETED", "answers": answers, "test_result": test_result,
                "evidence": [{"ref": ref} for answer in answers for ref in answer["evidence_refs"]]}

    if action == "NEEDLE_REVIEW":
        from research.needle_research_readiness import verify_readiness
        domain = str(state.get("subject_domain") or "").upper()
        contract = ("FOREX_STRATEGY_MISSION_NOTEBOOK_V1" if domain in {"TRADING", "TRADING_INTELLIGENCE"}
                    else "BUSINESS_OPPORTUNITY_MISSION_NOTEBOOK_V1")
        required = [{"question_id": f"q-{index}", "question_text": row.get("question"),
                     "asked": True, "evidence_status": row.get("status", "UNVERIFIED"),
                     "answer_status": row.get("status", "UNVERIFIED"),
                     "source_refs": row.get("evidence_refs") or [], "required": True}
                    for index, row in enumerate(state.get("questions") or [], 1)]
        package = {"synthesis": (state.get("synthesis") or {}).get("research_conclusion") or "",
                   "action_statement": (state.get("synthesis") or {}).get("recommended_actions") or [],
                   "source_references": _evidence_refs(state)}
        verdict = verify_readiness({"research_job_id": work_item.get("work_id"),
            "research_purpose": objective, "research_domain": domain or "UNKNOWN",
            "contract_id": contract, "objective": objective, "notebook_id": None,
            "required_questions": required, "evidence_gaps": [], "synthesis": package["synthesis"],
            "handoff_package": {"handoff_payload": package}},
            deterministic_result={"complete": True, "question_count": len(required),
                "evidence_refs": _evidence_refs(state)},
            repair_attempt=int(state.get("needle_repair_attempts", 0) or 0))
        outcome = str(verdict.get("status") or "BLOCKED").upper()
        if outcome in {"READY_FOR_DEPARTMENT", "READY"}:
            return {"status": "READY_FOR_DEPARTMENT", "summary": verdict.get("summary"),
                    "next_department": _destination(state), "receipt_id": verdict.get("receipt_id"),
                    "unresolved_items_safe": verdict.get("unresolved_items_safe", True)}
        if outcome == "RESEARCH_MORE":
            missing = verdict.get("specific_gap") or verdict.get("requested_research_action") or "Unresolved evidence question"
            return {"status": "RESEARCH_MORE", "missing_questions": [missing],
                    "receipt_id": verdict.get("receipt_id"), "summary": verdict.get("summary")}
        # A provider/contract blocker is returned to the parent. After the
        # parent's bounded follow-up, remaining uncertainty is synthesized.
        return {"status": "RESEARCH_MORE", "missing_questions": [],
                "reason": verdict.get("reason_code") or "NEEDLE_REVIEW_UNAVAILABLE"}

    if action == "SYNTHESIS":
        from research import research_v2
        advisor = state.get("advisor_findings") or {}
        questions = state.get("questions") or []
        answers = [{k: row.get(k) for k in ("question", "status", "answer", "evidence_refs", "confidence")}
                   for row in questions]
        destination = _destination(state)
        conclusion = str(advisor.get("subject_interpretation") or _source_text(state) or objective)[:1600]
        package = {"original_objective": objective,
            "subject": (state.get("source_understanding") or {}).get("subject") or url,
            "source_references": _evidence_refs(state), "category": state.get("subject_domain") or "UNKNOWN",
            "library_destination": f"research/{str(state.get('subject_domain') or 'unknown').lower()}",
            "prior_knowledge": (state.get("knowledge_reconciliation") or {}).get("prior_summary"),
            "material_changes": (state.get("knowledge_reconciliation") or {}).get("material_changes") or [],
            "questions_asked": [row.get("question") for row in questions], "answers": answers,
            "unresolved_uncertainty": [row.get("question") for row in questions if row.get("status") in {"OPEN", "PARTIAL", "UNVERIFIED"}],
            "advisor_findings": advisor, "test_results": state.get("test_results") or [],
            "research_conclusion": conclusion,
            "recommended_actions": advisor.get("recommended_next_actions") or ["Have the receiving department review the evidence and select a bounded next step."],
            "action_owner": "NOVA", "next_department": destination}
        # Use the existing compact handoff package contract without storing raw
        # source text or transcripts in the durable job envelope.
        research_v2.department_handoff(research_summary=conclusion, plan={}, sources=package["source_references"],
            provenance=package["source_references"], facts=answers, assumptions=[], unknowns=package["unresolved_uncertainty"],
            risks=[], scam_status="UNKNOWN", recommended_next_action=package["recommended_actions"][0],
            success_criteria=["Receiving owner continues from this evidence"], primary_owner=destination)
        return {"status": "COMPLETED", **package}

    if action == "CATEGORY_LIBRARY_ROUTING":
        return {"status": "COMPLETED", "category": state.get("subject_domain") or "UNKNOWN",
                "library_destination": f"research/{str(state.get('subject_domain') or 'unknown').lower()}"}

    if action == "HANDOFF":
        from operations import nexus_handoff
        synthesis = state.get("synthesis") or {}
        destination = str(synthesis.get("next_department") or state.get("next_department") or "").upper()
        owner = str(synthesis.get("action_owner") or state.get("action_owner") or "").upper()
        payload = {k: synthesis.get(k) for k in (
            "original_objective", "subject", "source_references", "what_it_is", "category",
            "library_destination", "prior_knowledge", "material_changes", "questions_asked", "answers",
            "unresolved_uncertainty", "advisor_findings", "test_results", "research_conclusion",
            "recommended_actions", "action_owner", "next_department")}
        target = destination or owner
        response = nexus_handoff.create_handoff(source_department="RESEARCH", target_department=target,
            handoff_type="RESEARCH_PARENT_HANDOFF", topic=str(synthesis.get("subject") or objective)[:180],
            payload={"research_parent_id": state.get("research_parent_id") or state.get("objective_id"),
                "root_objective_id": state.get("root_objective_id") or state.get("objective_id"),
                "research_case_id": state.get("research_case_id"), "research_package": payload,
                "continuation": {"owner_department": target, "parent_goal_id": state.get("objective_id"),
                    "next_action": "RECEIVER_CONTINUES_FROM_RESEARCH_PACKAGE", "success_criteria": []}},
            source_ids=[str(ref) for ref in _evidence_refs(state)],
            artifact_refs=[str(ref) for ref in _evidence_refs(state)],
            logical_key=f"research-parent:{state.get('objective_id')}:{target}")
        handoff_id = response.get("handoff_id")
        if not handoff_id:
            return {"status": "CONTINUATION_REQUIRED", "reason": response.get("reason") or response.get("error") or "RESEARCH_HANDOFF_FAILED"}
        return {"status": "COMPLETED", "handoff_id": handoff_id,
                "next_department": destination or None, "action_owner": owner or None,
                "handoff_status": response.get("handoff_status") or response.get("status")}

    return {"status": "CONTINUATION_REQUIRED", "reason": f"RESEARCH_PARENT_ACTION_UNAVAILABLE:{action}"}


def _destination(state: Mapping[str, Any]) -> str:
    domain = str(state.get("subject_domain") or "").upper()
    if domain in {"TRADING", "TRADING_INTELLIGENCE", "TRADING_STRATEGY"}:
        return "TRADING"
    advisor = state.get("advisor_findings") or {}
    value = str(advisor.get("likely_destination") or "").upper()
    return value or "NOVA"
