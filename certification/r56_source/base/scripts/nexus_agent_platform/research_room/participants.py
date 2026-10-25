"""Room participants append evidence and questions to the shared case."""
from __future__ import annotations

import re
from typing import Any

from .models import RoomMessage, utc_now


def append_message(case: dict[str, Any], role: str, content: str, kind: str = "COMMENT", **metadata: Any) -> None:
    case.setdefault("room_messages", []).append({**RoomMessage(role, content, kind, metadata). __dict__})
    case["updated_at"] = utc_now()


class ResearchLead:
    def contribute(self, case: dict[str, Any]) -> dict[str, Any]:
        from .execution_modes import classify_execution_mode, depth_for_mode
        mode = classify_execution_mode(case.get("original_request", ""), case.get("metadata"))
        case.setdefault("metadata", {})["execution_mode"] = mode
        case["metadata"].setdefault("depth_budget", depth_for_mode(mode, case["metadata"].get("depth_budget")))
        case["metadata"]["research_can_complete_with_uncertainty"] = True
        if case.get("handoff"):
            case["status"], case["next_participant"] = "COMPLETE", "DONE"
            return case
        from .advisor_router import lead_advisor_plan
        plan = lead_advisor_plan(case)
        case["advisor_plan"] = plan
        append_message(case, "RESEARCH_LEAD", "I will coordinate source understanding, questions, verification, and a useful proposed handoff.",
                       "COST_AWARE_PLAN", **plan)
        return case

    def select_next_participant(self, case: dict[str, Any]) -> str:
        """Select the next useful voice from shared case state, never a quality gate."""
        if case.get("status") == "COMPLETE" or case.get("handoff"):
            return "DONE"
        if str(case.get("next_participant") or "").upper() == "HANDOFF":
            return "HANDOFF"
        if not case.get("source_report"):
            return "SOURCE_ANALYST"
        if not case.get("knowledge_reconciliation"):
            return "KNOWLEDGE_RECONCILIATION"
        if not case.get("advisor_comments"):
            return "DOMAIN_ADVISOR"
        if not case.get("questions_generated"):
            return "QUESTION_GENERATOR"
        if not case.get("fact_check_completed"):
            return "FACT_CHECKER"
        if not case.get("needle_result"):
            return "NEEDLE"
        if ((case.get("needle_result") or {}).get("missing_questions")
                and not case.get("needle_followup_completed")):
            return "FOLLOWUP_RESEARCH"
        if not case.get("final_synthesis"):
            return "FINAL_STRATEGIST"
        return "DONE"


class SourceAnalyst:
    def __init__(self, source_tools: Any): self.source_tools = source_tools
    def contribute(self, case: dict[str, Any]) -> dict[str, Any]:
        if isinstance(case.get("source_report"), dict):
            source = case["source_report"]
            if source.get("status") not in {"SOURCE_ACQUIRED", "SOURCE_INCOMPLETE"}:
                source = {"status": "SOURCE_INCOMPLETE", **source}
        else:
            url = (case.get("source_references") or [{}])[0].get("url")
            source = self.source_tools.acquire(url, objective=case["original_request"])
        case["source_report"] = source
        acquired = source.get("sources") or ([source] if source.get("url") else [])
        for item in acquired:
            case.setdefault("findings", []).append({"kind": "SOURCE_UNDERSTANDING",
                "status": "SOURCE_ACQUIRED", "question_id": item.get("question_id"),
                "method": item.get("method"), "title": item.get("title"),
                "summary": item.get("summary"), "claims": item.get("claims") or [],
                "source_refs": item.get("source_refs") or [],
                "source_content_hash": item.get("source_content_hash")})
        for ref in source.get("source_refs") or []:
            if ref not in case.setdefault("source_references", []):
                case["source_references"].append(ref)
        # The full acquired source stays in source_report. Findings and room
        # messages are the compact working record, so synthesis and later
        # participants do not duplicate a transcript/page body.
        source_text = str(source.get("text") or "")
        claims = [re.sub(r"\s+", " ", part).strip()[:400]
                  for part in re.split(r"(?<=[.!?])\s+|\s+[█#]{1,}\s*", source_text)
                  if len(part.strip()) >= 35][:8]
        case.setdefault("findings", []).append({
            "kind": "SOURCE_UNDERSTANDING", "status": source.get("status"),
            "method": source.get("method"), "source_type": source.get("source_type"),
            "title": source.get("title"), "summary": str(source.get("summary") or "")[:1800],
            "claims": claims, "source_refs": source.get("source_refs") or ([{"url": url}] if url else []),
            "source_content_hash": source.get("source_content_hash"),
            "source_character_count": source.get("source_character_count"),
        })
        for failure in source.get("method_failures") or []:
            case.setdefault("unresolved_items", []).append({"kind": "SOURCE_METHOD_UNAVAILABLE", **failure})
        if source.get("status") != "SOURCE_ACQUIRED":
            case.setdefault("unresolved_items", []).append({"kind": "SOURCE_LIMITATION", "detail": source.get("limitation")})
        append_message(case, "SOURCE_ANALYST", source.get("summary") or source.get("text", "Source content unavailable; limitation retained.")[:1800], "SOURCE_REPORT",
                       source_status=source.get("status"), method=source.get("method"))
        case["next_participant"] = "KNOWLEDGE_RECONCILIATION"
        return case


class DomainAdvisor:
    def __init__(self, router: Any): self.router = router
    def contribute(self, case: dict[str, Any]) -> dict[str, Any]:
        from .advisor_router import select_domain
        domain = select_domain(case)
        purpose = f"domain advisor for {domain}: {case['original_request']}"
        result = self.router.ask(role=f"DOMAIN_ADVISOR:{domain}", case_context=case, objective=purpose)
        if result.get("cost_routing"):
            case["cost_routing"] = result["cost_routing"]
        result.setdefault("domain", domain)
        case.setdefault("advisor_comments", []).append(result)
        case.setdefault("advisor_sessions", []).append({
            "role": f"DOMAIN_ADVISOR:{domain}", "provider": result.get("provider"),
            "model": result.get("model"), "input_prompt": result.get("prompt_sent", "UNKNOWN"),
            "full_response": result.get("full_response", result.get("analysis", "UNKNOWN")),
            "usage": result.get("usage", {}), "estimated_cost_usd": result.get("estimated_cost_usd", "UNKNOWN"),
            "duration_ms": result.get("duration_ms", "UNKNOWN"), "routing_decision": result.get("routing_decision", {}),
        })
        append_message(case, "DOMAIN_ADVISOR", str(result.get("analysis") or result.get("reason") or "Advisor unavailable; continue using available evidence."),
                       "ADVISOR", provider=result.get("provider"), status=result.get("status"))
        case["next_participant"] = "QUESTION_GENERATOR"
        return case


class QuestionGenerator:
    def generate(self, case: dict[str, Any]) -> dict[str, Any]:
        advisor = (case.get("advisor_comments") or [{}])[-1]
        questions = advisor.get("new_questions") or advisor.get("questions") or []
        if isinstance(questions, str):
            questions = [questions]
        if not questions:
            questions = [
                "Which claims materially affect the requested decision, and what evidence supports them?",
                "What important costs, risks, constraints, and alternatives remain uncertain?",
            ]
        for item in questions:
            text = str(item.get("question") if isinstance(item, dict) else item).strip()
            if text and not any(row.get("question", "").casefold() == text.casefold()
                                for row in case.setdefault("questions", [])):
                case["questions"].append({"question": text, "status": "OPEN", "answer": None,
                    "evidence_refs": [], "confidence": None, "needs_followup": True})
        append_message(case, "QUESTION_GENERATOR", f"Added or confirmed {len(case['questions'])} material research question(s).", "QUESTIONS")
        case["questions_generated"] = True
        case["next_participant"] = "FOLLOWUP_RESEARCH"
        return case


class FollowupResearcher:
    def research(self, case: dict[str, Any]) -> dict[str, Any]:
        # Shadow v1 records what current evidence can and cannot answer. Real
        # source adapters can be injected without changing the case contract.
        source_text = str((case.get("source_report") or {}).get("text") or "").casefold()
        updated = []
        for question in case.get("questions", []):
            if question.get("status") == "ANSWERED":
                continue
            needle_evidence = case.get("metadata", {}).get("needle_followup_evidence") or []
            evidence_row = next((row for row in needle_evidence
                if question.get("question") == row.get("question") and row.get("answer")), None)
            if evidence_row:
                question.update(status="ANSWERED", answer=evidence_row["answer"], needs_followup=False,
                    confidence=evidence_row.get("confidence", "MEDIUM"), evidence_refs=evidence_row.get("evidence_refs", []))
                case.setdefault("answers", []).append({"question": question["question"], "answer": question["answer"],
                    "confidence": question["confidence"], "evidence_refs": question["evidence_refs"]})
                continue
            terms = [term for term in question.get("question", "").casefold().split() if len(term) > 5]
            matched = [term for term in terms if term in source_text]
            if matched:
                answer = "Source contains relevant terms (" + ", ".join(matched[:4]) + "); independent confirmation remains limited."
                question.update(status="PARTIAL", answer=answer, needs_followup=False,
                                evidence_refs=[(case.get("source_report") or {}).get("url")])
                case.setdefault("answers", []).append({"question": question["question"], "answer": answer,
                    "confidence": "LOW", "evidence_refs": question["evidence_refs"]})
            else:
                question.update(status="UNVERIFIED", answer="Not materially answered by the available source evidence.", needs_followup=False)
                case.setdefault("unresolved_items", []).append({"kind": "UNANSWERED_QUESTION", "question": question["question"]})
            updated.append(question)
        append_message(case, "FACT_CHECKER", f"Bounded follow-up reviewed {len(updated)} question(s); unresolved claims remain explicit.", "FOLLOWUP")
        result = {"status": "FOLLOWUP_COMPLETE", "reviewed": len(updated)}
        case["followup_result"] = result
        case["needle_followup_completed"] = True
        return result


class FactChecker:
    def __init__(self, verifier: Any = None): self.verifier = verifier
    def contribute(self, case: dict[str, Any]) -> dict[str, Any]:
        if self.verifier:
            result = self.verifier(case)
        else:
            src = case.get("source_report") or {}
            result = {"status": "PARTIAL", "claims": [], "note": "Independent verifier adapter not configured; source claims are retained as unverified."}
        case.setdefault("findings", []).append({"kind": "FACT_CHECK", **result})
        case["fact_check_completed"] = True
        append_message(case, "FACT_CHECKER", str(result.get("note") or "Verification notes added."), "FACT_CHECK", status=result.get("status"))
        case["next_participant"] = "NEEDLE"
        return case


class Needle:
    def review(self, case: dict[str, Any]) -> dict[str, Any]:
        questions = case.setdefault("questions", [])
        open_texts = [str(q.get("question") or "") for q in questions if isinstance(q, dict)
            and str(q.get("status") or "OPEN").upper() not in {"ANSWERED", "NOT_APPLICABLE"}
            and q.get("needs_followup") is not False]
        metadata = case.get("metadata") or {}
        candidates = list(metadata.get("needle_candidate_questions") or [])
        legacy_review = str(metadata.get("needle_review_question") or "").strip()
        if legacy_review:
            candidates.append(legacy_review)
        all_existing_texts = [str(q.get("question") or "") for q in questions if isinstance(q, dict)]
        new_questions = []
        for candidate in candidates[:5]:
            question = " ".join(str(candidate or "").split())[:800]
            if not question or any(question.casefold() == existing.casefold() for existing in all_existing_texts):
                continue
            questions.append({"question": question, "status": "OPEN", "answer": None,
                "evidence_refs": [], "confidence": None, "needs_followup": True, "origin": "NEEDLE"})
            open_texts.append(question)
            all_existing_texts.append(question)
            new_questions.append(question)
        missing_questions = open_texts
        coverage = "MORE_INFORMATION_USEFUL" if missing_questions else "NO_MATERIAL_GAPS"
        result = {"coverage_status": coverage,
            "requested_question": "What material unanswered question could still change the recommendation, economics, implementation path, or next action?",
            "new_questions": new_questions, "missing_questions": missing_questions,
            "unresolved_count": len(missing_questions)}
        append_message(case, "NEEDLE", f"Question audit: {coverage}; {len(missing_questions)} unresolved material question(s).", "QUESTION_AUDIT")
        case["needle_result"] = result
        case["next_participant"] = "ADVISOR_FOLLOWUP" if missing_questions else "FINAL_STRATEGIST"
        return result


class FinalSynthesizer:
    def synthesize(self, case: dict[str, Any]) -> dict[str, Any]:
        from .execution_modes import build_execution_strategy
        src = case.get("source_report") or {}
        question_rows = case.get("questions") or []
        destination = str(case.get("metadata", {}).get("likely_destination") or "RAY/NOVA").upper()
        execution_strategy = build_execution_strategy(case)
        synthesis = {
            "original_objective": case["original_request"], "subject": src.get("title") or case["original_request"],
            "source_references": case.get("source_references", []), "what_it_is": str(src.get("summary") or src.get("text", "")[:900] or "Subject identified from the request; source content unavailable.")[:1800],
            "category": case.get("metadata", {}).get("category", "UNKNOWN"),
            "library_destination": case.get("metadata", {}).get("library_destination"),
            "prior_knowledge": case.get("prior_nexus_knowledge", []), "material_changes": (case.get("knowledge_reconciliation") or {}).get("material_changes", []),
            "key_findings": case.get("findings", []), "questions_asked": question_rows,
            "answers": case.get("answers", []), "unresolved_uncertainty": case.get("unresolved_items", []) + [
                {"kind": "UNANSWERED_QUESTION", "question": q.get("question")} for q in question_rows if q.get("status") != "ANSWERED"],
            "advisor_findings": case.get("advisor_comments", []), "test_results": case.get("test_results", []),
            "multi_advisor_comparison": case.get("multi_advisor_comparison", {}),
            "business_opportunity_report": case.get("metadata", {}).get("business_opportunity_report"),
            "research_conclusion": (case.get("metadata", {}).get("business_opportunity_report") or {}).get("recommendation", {}).get("why_winner")
                or "Available evidence is summarized with limitations; further action should reflect unresolved claims and uncertainty.",
            "recommended_actions": (case.get("metadata", {}).get("business_opportunity_report") or {}).get("recommendation", {}).get("next_actions")
                or case.get("metadata", {}).get("recommended_actions", ["Review the findings and choose a bounded next validation step."]),
            "action_owner": "RAY/NOVA" if destination == "RAY/NOVA" else None,
            "next_department": None if destination == "RAY/NOVA" else destination,
            "domain_sections": case.get("metadata", {}).get("domain_sections", {}),
            "execution_mode": execution_strategy["execution_mode"],
            "execution_strategy": execution_strategy,
            "library_additions": execution_strategy.get("library_additions", []),
            "next_action": execution_strategy.get("next_action"),
        }
        case["final_synthesis"] = synthesis
        case["execution_strategy"] = execution_strategy
        append_message(case, "FINAL_STRATEGIST", execution_strategy.get("next_action") or synthesis["research_conclusion"], "EXECUTION_STRATEGY",
                       execution_mode=execution_strategy["execution_mode"])
        case["next_participant"] = "HANDOFF"
        return synthesis
