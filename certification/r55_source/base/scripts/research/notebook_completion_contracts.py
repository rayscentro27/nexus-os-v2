"""Canonical domain contracts for NotebookLM-backed Nexus Research.

Question selection and completion checks are deterministic. This module stores
contract state/provenance only; notebook transcripts stay in NotebookLM/local
case evidence, never in the compact department handoff.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
from nexus_agent_platform.runtime.paths import nexus_research_state_path

CONTRACTS: dict[str, dict[str, Any]] = {
    "BUSINESS_CREATION_NOTEBOOK_V1": {
        "research_purpose": "LIBRARY_INTELLIGENCE", "research_domain": "BUSINESS_CREATION",
        "handoff_department": "BUSINESS_CREATION", "is_library": True,
        "action_fields": ["REQUIRED", "OPTIONAL", "PRODUCT/LENDER-SPECIFIC", "UNVERIFIED", "AVOID", "DO_NOW", "CAN_WAIT", "NEXT_ACTION"],
        "questions": [
            "What type of business/activity is being created?", "What does the business actually sell?",
            "What truthful NAICS classification matches the primary business activity?", "What entity structures are relevant?",
            "What state/entity considerations matter?", "What records must remain consistent across state, IRS, bank, bureaus, website, applications, and other records?",
            "What EIN requirements matter?", "What good-standing requirements matter?", "What address types are acceptable?",
            "Are residential addresses acceptable, and under what conditions?", "Are virtual addresses acceptable, and under what conditions?",
            "Are coworking addresses acceptable, and under what conditions?", "Can registered-agent addresses create problems?",
            "Is a dedicated business phone required?", "Are VOIP numbers acceptable, and under what conditions?",
            "Is domain-based email required or simply recommended?", "Is a website required?",
            "If a website is not universally required, when does a website matter?", "What licensing, permit, or insurance requirements apply?",
            "What business-bank relationship should be established?", "When is brick-and-mortar banking advantageous?",
            "When is an online business bank sufficient?", "Does banking seasoning matter, and for which products?",
            "Do initial deposits or average balances matter, and for which products?", "Is DUNS required, and by whom?",
            "When does commercial bureau setup matter?", "When should business-credit building begin?",
            "Are vendor tradelines relevant, and for which goals or products?", "Which setup decisions commonly create future funding problems?",
            "Which commonly repeated fundability requirements are unsupported or lender-specific?", "What can be performed in parallel?",
            "What is the fastest legitimate path from formation to funding-readiness review?", "What remains unresolved?",
            "What should Business Creation do with this knowledge?",
        ],
    },
    "FUNDING_TECHNIQUE_INTELLIGENCE_NOTEBOOK_V1": {
        "research_purpose": "LIBRARY_INTELLIGENCE", "research_domain": "BUSINESS_FUNDING",
        "handoff_department": "CLYDE_CREDIT", "is_library": True,
        "action_fields": ["SOURCE_CLAIM", "NEXUS_VERIFIED_VERSION", "VERIFIED_REQUIREMENTS", "PRODUCT/LENDER-SPECIFIC", "UNVERIFIED", "CONTRADICTED", "REMEDIATION", "ALTERNATIVE", "WHEN_TO_USE", "WHEN_TO_AVOID", "NEXT_ACTION"],
        "questions": [
            "What exact funding strategy is being claimed?", "Which institution, lender, credit union, or product is involved?",
            "Does the product actually exist?", "What is the official website or product path?", "What funding amount is claimed?",
            "Is the claimed amount guaranteed, maximum, typical, anecdotal, or unverified?", "Who is the strategy designed for?",
            "Can a new business use it?", "Is time in business required?", "Is operating revenue required?",
            "Is personal credit considered?", "Is a personal guarantee required?", "Is business credit required?",
            "Is a minimum credit score claimed?", "Can that score requirement actually be verified?", "Does utilization matter?",
            "Do inquiries or new accounts matter?", "Is membership required?", "Are geography, employer, association, military, family, or other membership restrictions involved?",
            "Is a banking relationship required?", "Does account age matter?", "Do deposits or average balances matter?",
            "Is a website required?", "Does business phone matter?", "Does business address type matter?",
            "Does domain email matter?", "Does DUNS or PAYDEX matter?", "Do vendor tradelines matter?", "Does application sequence matter?",
            "What are the verified hard requirements?", "What appears lender/product specific?", "What is recommended but not required?",
            "What claims are unverified?", "What claims are contradicted?", "What commonly causes denial?",
            "What commonly increases success likelihood?", "Which client deficiencies can be fixed?", "For each fixable deficiency, what is the remediation path?",
            "How do we verify that remediation is complete?", "Is there a waiting, reporting, or seasoning period?", "What can happen in parallel?",
            "What alternative strategy fits someone who cannot satisfy this requirement?", "What should Clyde never state as guaranteed?",
            "When should Clyde consider this strategy?", "When should Clyde avoid or delay this strategy?", "What remains unresolved?", "What is the actionable rule?",
        ],
    },
    "BUSINESS_OPPORTUNITY_MISSION_NOTEBOOK_V1": {
        "research_purpose": "MISSION_RESEARCH", "research_domain": "BUSINESS_OPPORTUNITY",
        "handoff_department": "BUSINESS_OPPORTUNITIES", "is_library": False,
        "action_fields": ["SELECTED_CANDIDATES", "CUSTOMER_PROBLEM", "IMPORTANT_EVIDENCE", "MAJOR_ASSUMPTIONS", "UNRESOLVED_RISKS", "SOURCE_REFERENCES", "NEXT_ACTION"],
        "questions": [
            "What customer problem exists?", "Who experiences the problem?", "What evidence shows actual demand?",
            "Where are customers discussing or searching for the problem?", "What complaints exist about existing solutions?",
            "What current products or services solve the problem?", "Who are the meaningful competitors?", "What pricing evidence exists?",
            "What will buyers plausibly pay, and what evidence supports that estimate?", "What revenue models are viable?",
            "Is recurring revenue possible, and what evidence supports it?", "What customer-acquisition channels appear viable?",
            "What current marketing methods appear effective?", "Could GoClear or Nexus solve the problem directly?",
            "Could an affiliate or existing solution satisfy the need instead?", "What would Nexus need to build?",
            "What can Nexus automate?", "What requires human involvement?", "What expertise is needed?",
            "What software or services are needed?", "What are likely startup costs?", "What recurring costs exist?",
            "What is likely operating complexity?", "How quickly could an MVP reasonably launch?", "What margins appear plausible?",
            "What compliance, legal, or licensing issues exist?", "What meaningful differentiation is possible?", "How scalable is it?",
            "What could make the opportunity fail?", "What evidence contradicts the opportunity?", "What major assumptions remain unresolved?",
            "What would need to be tested before significant spending?", "Why should this candidate remain in the top-three set rather than alternatives?",
        ],
    },
    "FOREX_STRATEGY_MISSION_NOTEBOOK_V1": {
        "research_purpose": "MISSION_RESEARCH", "research_domain": "FOREX",
        "handoff_department": "TRADING", "is_library": False,
        "action_fields": ["PAIR", "TIMEFRAME", "MARKET_HYPOTHESIS", "IMPLEMENTABLE_RULES", "DATA_REQUIREMENTS", "BACKTEST_REQUIREMENTS", "KNOWN_ASSUMPTIONS", "UNRESOLVED_ASSUMPTIONS", "FAILURE_CONDITIONS", "NEXT_ACTION"],
        "questions": [
            "What currency pair or instrument is targeted?", "What strategy or hypothesis is being proposed?",
            "Where did the strategy originate?", "What market behavior is supposed to create the edge?", "What timeframe is intended?",
            "What session is intended?", "What market regime is it expected to work in?", "What indicators are used?",
            "Why is each indicator present?", "What exact entry rules are claimed?", "What exact exit rules are claimed?",
            "What stop-loss logic is used?", "What take-profit logic is used?", "Is trailing-stop logic involved?",
            "What risk/reward structure is intended?", "What position-sizing logic is intended?", "What session filters apply?",
            "What day/time filters apply?", "How should spreads be accounted for?", "How should slippage be modeled?",
            "How should swap or rollover be treated?", "How should major economic releases or news be handled?",
            "What historical data is needed?", "What historical period is appropriate?", "What sample or trade count is needed?",
            "What benchmark should be used?", "What metrics define success?", "What metrics define failure?",
            "What conditions invalidate the strategy?", "What overfitting risks exist?", "What evidence supports the strategy?",
            "What evidence contradicts it?", "Have similar rules been independently tested?", "Which assumptions remain unresolved?",
            "Are the strategy rules precise enough for deterministic implementation?",
        ],
    },
}

PURPOSES = {"LIBRARY_INTELLIGENCE", "MISSION_RESEARCH", "CLIENT_SPECIFIC_RESEARCH", "REFRESH_VERIFICATION"}
DOMAINS = {"BUSINESS_CREATION", "BUSINESS_FUNDING", "BUSINESS_OPPORTUNITY", "FOREX"}
CONTRACT_BY_PAIR = {(x["research_purpose"], x["research_domain"]): key for key, x in CONTRACTS.items()}
CONTRACT_STATE_ROOT = nexus_research_state_path("runtime", "research_notebook_contracts")
TRANSCRIPT_KEYS = {"transcript", "raw_transcript", "conversation", "full_conversation", "full_transcript", "raw_answer", "notebook_answer", "first_answer", "followup_answer"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def classify_research(*, objective: str, research_purpose: str | None = None,
                      research_domain: str | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve explicit or high-confidence purpose/domain deterministically.

    Ambiguous fields are returned as unresolved with LIGHT_REASONING suggested;
    this function never invokes a model.
    """
    context = context or {}
    text = _norm(" ".join([str(objective), *(str(v) for v in context.values() if isinstance(v, (str, int))) ]))
    purpose = str(research_purpose or context.get("research_purpose") or "").upper()
    domain = str(research_domain or context.get("research_domain") or "").upper()
    if not purpose:
        if any(term in text for term in ("library intelligence", "reusable knowledge", "knowledge library", "funding technique", "business creation", "fundability knowledge")):
            purpose = "LIBRARY_INTELLIGENCE"
        elif any(term in text for term in ("mission", "research this", "find me", "investigate", "opportunity", "opportunities", "strategy to test")):
            purpose = "MISSION_RESEARCH"
    if not domain:
        if any(term in text for term in ("forex", "currency pair", "fx strategy")):
            domain = "FOREX"
        elif any(term in text for term in ("funding", "lender", "credit union", "loan product", "funding strategy")):
            domain = "BUSINESS_FUNDING"
        elif any(term in text for term in ("business creation", "create a business", "formation", "fundability setup")):
            domain = "BUSINESS_CREATION"
        elif any(term in text for term in ("business opportunity", "business opportunities", "online business", "customer problem", "businesses nexus could build", "business_opportunities")):
            domain = "BUSINESS_OPPORTUNITY"
    if purpose and purpose not in PURPOSES:
        return {"status": "UNSUPPORTED_PURPOSE", "research_purpose": purpose, "research_domain": domain or None,
                "execution_class": "LIGHT_REASONING", "model_call_required": True}
    if domain and domain not in DOMAINS:
        return {"status": "UNSUPPORTED_DOMAIN", "research_purpose": purpose or None, "research_domain": domain,
                "execution_class": "LIGHT_REASONING", "model_call_required": True}
    if not purpose or not domain:
        return {"status": "AMBIGUOUS", "research_purpose": purpose or None, "research_domain": domain or None,
                "missing": [name for name, value in (("research_purpose", purpose), ("research_domain", domain)) if not value],
                "execution_class": "LIGHT_REASONING", "model_call_required": True}
    contract_id = CONTRACT_BY_PAIR.get((purpose, domain))
    if not contract_id:
        # Extension slots are intentional and fail closed until mapped.
        return {"status": "UNMAPPED_PURPOSE_DOMAIN", "research_purpose": purpose, "research_domain": domain,
                "execution_class": "DETERMINISTIC", "model_call_required": False}
    return {"status": "RESOLVED", "research_purpose": purpose, "research_domain": domain,
            "contract_id": contract_id, "execution_class": "DETERMINISTIC", "model_call_required": False}


def select_contract(research_purpose: str, research_domain: str) -> dict[str, Any]:
    """Select contract from a resolved purpose/domain pair; no model call."""
    pair = (str(research_purpose).upper(), str(research_domain).upper())
    contract_id = CONTRACT_BY_PAIR.get(pair)
    if not contract_id:
        raise ValueError(f"NO_NOTEBOOK_CONTRACT:{pair[0]}:{pair[1]}")
    contract = CONTRACTS[contract_id]
    return {"contract_id": contract_id, **contract,
            "question_rows": [question_row(contract_id, q) for q in contract["questions"]]}


def question_row(contract_id: str, question_text: str) -> dict[str, Any]:
    normalized = _norm(question_text)
    qid = "q_" + hashlib.sha256(f"{contract_id}|{normalized}".encode()).hexdigest()[:20]
    return {"question_id": qid, "contract_id": contract_id, "question_text": question_text,
            "required": True, "asked": False, "answer_status": "UNVERIFIED",
            "evidence_status": "UNVERIFIED", "supplementation_attempted": False,
            "source_refs": [], "last_checked_at": None}


def new_contract_state(*, objective: str, research_purpose: str, research_domain: str,
                       notebook_id: str | None = None, source_inventory: list[dict[str, Any]] | None = None,
                       research_job_id: str | None = None) -> dict[str, Any]:
    contract = select_contract(research_purpose, research_domain)
    return {"schema_version": "nexus.notebook-completion-contract.v1", "contract_id": contract["contract_id"],
        "research_purpose": research_purpose, "research_domain": research_domain,
        "objective": objective, "research_job_id": research_job_id, "notebook_id": notebook_id,
        "source_inventory": _compact_sources(source_inventory or []), "required_questions": contract["question_rows"],
        "evidence_gaps": [], "gaps_reviewed": False, "supplementation_attempted": False,
        "synthesis": None, "action_statement": None, "structured_extraction": None,
        "handoff_package": None, "handoff_status": "NOT_ATTEMPTED", "library_entry_ids": [],
        "verification_status": "IN_PROGRESS", "created_at": _now(), "updated_at": _now()}


def _compact_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for src in sources:
        if not isinstance(src, dict):
            continue
        rows.append({k: src.get(k) for k in ("source_id", "notebook_source_id", "url", "title", "source_class", "source_date", "last_verified_at", "evidence_status") if src.get(k) is not None})
    return rows


def build_required_question_prompt(state: dict[str, Any]) -> str:
    contract = CONTRACTS[state["contract_id"]]
    rows = state["required_questions"]
    lines = ["RESEARCH NOTEBOOK COMPLETION CONTRACT", f"CONTRACT_ID: {state['contract_id']}",
        f"RESEARCH_PURPOSE: {state['research_purpose']}", f"RESEARCH_DOMAIN: {state['research_domain']}",
        f"OBJECTIVE: {state['objective']}", "Use evidence already in this notebook. Do not invent missing facts.",
        "For EVERY required question return its exact question_id and one evidence status: VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED, or CONTRADICTED.",
        "For each include answer, concise evidence basis, source IDs/URLs, confidence, and unresolved gap. Mark unsupported claims UNVERIFIED.",
        "REQUIRED QUESTIONS:"]
    if state.get("research_domain") == "BUSINESS_OPPORTUNITY":
        lines.append("For BUSINESS_OPPORTUNITY, first list the candidate opportunities in the objective, then answer EVERY question separately for EACH candidate using the same evidence fields so Business Opportunities can compare candidates. Do not collapse candidates into one answer.")
    lines.extend(f"{i+1}. [{q['question_id']}] {q['question_text']}" for i, q in enumerate(rows))
    lines.extend(["After the per-question answers provide: evidence gaps; synthesis; ACTION STATEMENT; structured extraction; and proposed next action.",
        "The action statement must distinguish: " + ", ".join(contract["action_fields"]) + ".",
        "Return JSON when possible with keys question_results, evidence_gaps, synthesis, action_statement, structured_extraction."])
    return "\n".join(lines)


# Stable contract question IDs are independent of execution grouping.  The
# group map is intentionally expressed in contract question indexes so adding
# a wording clarification does not silently change group membership.
BUSINESS_OPPORTUNITY_QUESTION_GROUPS = {
    "GROUP_A_DEFINITION": (0, 1),
    "GROUP_B_DEMAND": (2, 3, 4),
    "GROUP_C_COMPETITION": (5, 6, 7),
    "GROUP_D_ECONOMICS": (8, 9, 10, 20, 21, 24),
    "GROUP_E_ACQUISITION": (11, 12),
    "GROUP_F_OPERATIONS": (15, 16, 17, 18, 19, 22, 23),
    "GROUP_G_NEXUS_FIT": (13, 14),
    "GROUP_H_RISK_AND_CONTRADICTION": (25, 26, 27, 28, 29, 30, 31),
    "GROUP_I_SELECTION": (32,),
}


def question_groups(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return deterministic prompt groups without changing stable question IDs."""
    rows = [row for row in state.get("required_questions", []) if row.get("required")]
    if state.get("contract_id") != "BUSINESS_OPPORTUNITY_MISSION_NOTEBOOK_V1":
        return [{"group_id": "GROUP_ALL", "questions": rows}] if rows else []
    grouped: list[dict[str, Any]] = []
    # Map canonical contract question IDs, not current row offsets. Adaptive
    # director questions are appended at runtime and must never shift baseline
    # question membership between groups.
    canonical = {question_row(state["contract_id"], text)["question_id"]: index
        for index, text in enumerate(CONTRACTS[state["contract_id"]]["questions"])}
    assigned: set[str] = set()
    for group_id, indexes in BUSINESS_OPPORTUNITY_QUESTION_GROUPS.items():
        selected = [row for row in rows if canonical.get(row.get("question_id")) in indexes]
        assigned.update(row.get("question_id") for row in selected)
        if selected:
            grouped.append({"group_id": group_id, "questions": selected})
    remainder = [row for row in rows if row.get("question_id") not in assigned]
    if remainder:
        grouped.append({"group_id": "GROUP_UNMAPPED_REMAINDER", "questions": remainder})
    return grouped


def build_question_group_prompt(state: dict[str, Any], group_id: str,
                                rows: list[dict[str, Any]]) -> str:
    """Ask one coherent question group; synthesis is reserved for the final pass."""
    return "\n".join([
        "RESEARCH NOTEBOOK COMPLETION CONTRACT — GROUPED QUESTION PASS",
        f"CONTRACT_ID: {state['contract_id']}", f"GROUP_ID: {group_id}",
        f"RESEARCH_PURPOSE: {state['research_purpose']}",
        f"RESEARCH_DOMAIN: {state['research_domain']}", f"OBJECTIVE: {state['objective']}",
        "Use the sources in this dedicated notebook. Treat the original creator/video as a source claim, not independent verification.",
        "Answer ONLY the required questions listed below. For each return the exact question_id, a substantive answer, evidence_status (VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED, or CONTRADICTED), evidence basis, source IDs/URLs, confidence, and unresolved gap.",
        "Do not invent facts. Distinguish source claims, official/primary evidence, secondary evidence, community/review evidence, and inference.",
        "Return JSON with a question_results array; each row must contain question_id, answer, evidence_status, evidence_basis, source_refs, confidence, unresolved_gap.",
        "QUESTIONS:",
        *[f"[{row['question_id']}] {row['question_text']}" for row in rows],
    ])


def build_targeted_gap_prompt(state: dict[str, Any], question_ids: list[str]) -> str:
    selected = {q["question_id"]: q for q in state.get("required_questions", [])}
    rows = [selected[qid] for qid in question_ids if qid in selected]
    return (f"Use the same research notebook for contract {state['contract_id']}. Recheck only these evidence gaps. "
        "For each question ID return evidence_status VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED, or CONTRADICTED; cite notebook source IDs, state what the source establishes, and preserve anything unresolved. Do not infer facts.\n"+
        "\n".join(f"[{q['question_id']}] {q['question_text']}" for q in rows))


def build_synthesis_prompt(state: dict[str, Any]) -> str:
    counts = question_counts(state)
    # Keep NotebookLM's final synthesis prompt bounded. The notebook already
    # contains the full question/answer evidence; the handoff prompt needs only
    # compact gap references and statuses, not another expanded gap transcript.
    gaps = [{"question_id":g.get("question_id"),"evidence_status":g.get("evidence_status"),
             "reviewed":bool(g.get("reviewed")),
             "supplementation_attempted":bool(g.get("supplementation_attempted")),
             "web_supplementation_not_appropriate":bool(g.get("web_supplementation_not_appropriate"))}
            for g in state.get("evidence_gaps",[])]
    action_fields = CONTRACTS[state["contract_id"]]["action_fields"]
    domain_output = ("For BUSINESS_OPPORTUNITY, synthesis must cover RESEARCH_OBJECTIVE, BUSINESS_MODEL, TARGET_CUSTOMER, CUSTOMER_PROBLEM, "
        "DEMAND_EVIDENCE, COMPETITION, PRICING_AND_ECONOMICS, CUSTOMER_ACQUISITION, DELIVERY_AND_OPERATIONS, NEXUS_FIT, "
        "KEY_VERIFIED_FINDINGS, PARTIALLY_VERIFIED_FINDINGS, UNVERIFIED_FINDINGS, CONTRADICTED_FINDINGS, MAJOR_RISKS, "
        "MAJOR_ASSUMPTIONS, REMAINING_RESEARCH_GAPS, FASTEST_VALIDATION_MODEL, EXTERNAL_CASH_COST, NEXUS_INTERNAL_EXECUTION, "
        "HUMAN_ONLY_REQUIREMENTS, TIME_TO_MVP, TIME_TO_FIRST_LAUNCH, AFFILIATE_OPTION, MERCH_OPTION, CONTENT_OPTION, "
        "ACTION_STATEMENT, and NEXT_DEPARTMENT. The action statement must explain "
        "what the opportunity is, why it does or does not deserve planning, what is well/weakly supported, what remains unknown, "
        "and what Business Opportunities should do next. Include FASTEST_LAUNCHABLE_VERSION, ESTIMATED_DAYS_TO_LAUNCH, "
        "ESTIMATED_INCREMENTAL_CASH, ASSETS_NEXUS_CAN_CREATE, CHANNELS_NEXUS_CAN_USE, FIRST_REVENUE_PATH, VALIDATION_WINDOW, "
        "SUCCESS_SIGNAL, PIVOT_SIGNAL, and WHAT_NOT_TO_BUILD_UNTIL_VALIDATED. Separate researched inputs, modeled assumptions, "
        "and calculated outputs. Do not assume a Nexus capability is available unless the case context verifies it. Do not build a business plan.") if state.get("research_domain") == "BUSINESS_OPPORTUNITY" else ""
    return (f"Synthesize the completed research objective from this same notebook. Synthesis format version=2. Contract={state['contract_id']}; "
        f"question counts={json.dumps(counts,separators=(',',':'))}; unresolved gaps={json.dumps(gaps,ensure_ascii=False,separators=(',',':'))}. "
        "Do not invent facts or claim profitability/eligibility without evidence. Return JSON with exactly the conceptual fields "
        "synthesis (string), action_statement (object), and structured_extraction (object). "
        f"Action statement must distinguish these domain fields: {', '.join(action_fields)}. "
        f"{domain_output} "
        "For mission research, extraction must be executable by the designated department and include assumptions, evidence, and source references. "
        "For library intelligence, extraction must contain reusable rules with evidence status, applicability limits, and unresolved exceptions. "
        "Do not include a transcript.")


def extract_deliverables(response: str) -> dict[str, Any]:
    try:
        value = json.loads(response)
    except (TypeError, ValueError):
        text=str(response or "").strip()
        if text.startswith("```"):
            lines=text.splitlines()
            if lines and lines[0].strip().startswith("```"):
                lines=lines[1:]
            if lines and lines[-1].strip()=="```":
                lines=lines[:-1]
            text="\n".join(lines).strip()
        try:
            value=json.loads(text)
        except (TypeError,ValueError):
            return {"synthesis": None, "action_statement": None, "structured_extraction": None}
    if not isinstance(value, dict):
        return {"synthesis": None, "action_statement": None, "structured_extraction": None}
    action = value.get("action_statement")
    extraction = value.get("structured_extraction")
    return {"synthesis": str(value.get("synthesis") or "").strip() or None,
            "action_statement": action if isinstance(action, dict) and action else None,
            "structured_extraction": extraction if isinstance(extraction, dict) and extraction else None}


def register_notebook_submission(state: dict[str, Any], *, prompt: str, submission_confirmed: bool,
                                 response: str = "", source_refs: list[str] | None = None,
                                 status_by_question: dict[str, str] | None = None) -> dict[str, Any]:
    """Record asked status only for a confirmed submission containing its exact question."""
    statuses = status_by_question or _extract_statuses(response)
    refs = [str(x) for x in (source_refs or []) if x]
    for row in state["required_questions"]:
        if submission_confirmed and row["question_text"] in prompt:
            row["asked"] = True
            row["last_checked_at"] = _now()
        value = str(statuses.get(row["question_id"], "")).upper()
        if value in {"VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "CONTRADICTED"}:
            row["answer_status"] = value
            row["evidence_status"] = value
            row["source_refs"] = sorted(set(row.get("source_refs", [])) | set(refs))
            row["last_checked_at"] = _now()
    prior_gaps = {row.get("question_id"): row for row in state.get("evidence_gaps", [])}
    state["evidence_gaps"] = _derive_gaps(state["required_questions"], prior_gaps)
    state["updated_at"] = _now()
    return state


def _extract_statuses(response: str) -> dict[str, str]:
    try:
        obj = json.loads(response)
    except (TypeError, ValueError):
        text=str(response or "").strip()
        if text.startswith("```"):
            lines=text.splitlines()
            if lines and lines[0].strip().startswith("```"): lines=lines[1:]
            if lines and lines[-1].strip()=="```": lines=lines[:-1]
            text="\n".join(lines).strip()
        try:
            obj=json.loads(text)
        except (TypeError,ValueError):
            # NotebookLM sometimes wraps a single JSON object in explanatory
            # text. Extract the object without interpreting its claims.
            match=re.search(r"\{.*\}",text,re.S)
            try: obj=json.loads(match.group(0)) if match else None
            except (TypeError,ValueError): obj=None
    rows = obj.get("question_results") if isinstance(obj, dict) else None
    out = {}
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        qid = str(row.get("question_id") or "")
        status = str(row.get("evidence_status") or row.get("answer_status") or "").upper()
        if qid and status in {"VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "CONTRADICTED"}:
            out[qid] = status
    return out


def _derive_gaps(rows: list[dict[str, Any]], prior: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    prior = prior or {}
    result = []
    for q in rows:
        if not q.get("required") or q.get("evidence_status") == "VERIFIED":
            continue
        old = prior.get(q["question_id"], {})
        result.append({"question_id": q["question_id"], "question_text": q["question_text"],
            "evidence_status": q["evidence_status"], "reviewed": bool(old.get("reviewed")),
            "supplementation_attempted": bool(q.get("supplementation_attempted") or old.get("supplementation_attempted")),
            "source_refs": sorted(set(q.get("source_refs") or []) | set(old.get("source_refs") or [])),
            "unresolved_note": old.get("unresolved_note")})
    return result


def record_gap_review(state: dict[str, Any], *, question_ids: list[str], supplementation_attempted: bool,
                      source_refs: list[str] | None = None, unresolved_note: str | None = None,
                      answer_updates: dict[str, str] | None = None) -> dict[str, Any]:
    allowed = {q["question_id"] for q in state["required_questions"]}
    ids = set(question_ids) & allowed
    if answer_updates:
        for q in state["required_questions"]:
            value = str(answer_updates.get(q["question_id"]) or "").upper()
            if value in {"VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "CONTRADICTED"}:
                q["evidence_status"] = q["answer_status"] = value
    for q in state["required_questions"]:
        if q["question_id"] in ids:
            q["supplementation_attempted"] = bool(supplementation_attempted)
            q["last_checked_at"] = _now()
            q["source_refs"] = sorted(set(q.get("source_refs") or []) | set(source_refs or []))
    for gap in state.get("evidence_gaps", []):
        if gap["question_id"] in ids:
            gap["reviewed"] = True
            gap["supplementation_attempted"] = bool(supplementation_attempted)
            gap["unresolved_note"] = str(unresolved_note or "Evidence remains unresolved after bounded review.")[:500]
            gap["source_refs"] = sorted(set(gap.get("source_refs") or []) | set(source_refs or []))
    prior_gaps={row.get("question_id"):row for row in state.get("evidence_gaps",[])}
    state["evidence_gaps"]=_derive_gaps(state.get("required_questions",[]),prior_gaps)
    state["gaps_reviewed"] = all(g.get("reviewed") for g in state.get("evidence_gaps", []))
    state["supplementation_attempted"] = bool(state.get("supplementation_attempted") or supplementation_attempted)
    state["updated_at"] = _now()
    return state


def record_gap_out_of_scope(state: dict[str, Any], *, question_id: str, reason: str) -> dict[str, Any]:
    """Close a gap only when its evidence is explicitly outside this mission's scope.

    This preserves the question as UNVERIFIED and does not claim that research
    was attempted. The explicit scope reason lets deterministic completion
    distinguish a reviewed limitation from an abandoned gap.
    """
    row=next((item for item in state.get("required_questions",[])
        if item.get("question_id")==question_id),None)
    gap=next((item for item in state.get("evidence_gaps",[])
        if item.get("question_id")==question_id),None)
    if row is None or gap is None or not row.get("required"):
        return state
    if row.get("evidence_status") not in {"VERIFIED","PARTIALLY_VERIFIED","CONTRADICTED"}:
        row["evidence_status"]=row["answer_status"]="UNVERIFIED"
    row["supplementation_attempted"]=False
    row["last_checked_at"]=_now()
    gap.update({"reviewed":True,"supplementation_attempted":False,
        "web_supplementation_not_appropriate":True,
        "web_supplementation_scope_reason":str(reason)[:500],
        "unresolved_note":str(reason)[:500]})
    state["updated_at"]=_now()
    return state


def set_synthesis(state: dict[str, Any], *, synthesis: str, action_statement: dict[str, Any],
                  structured_extraction: dict[str, Any]) -> dict[str, Any]:
    state["synthesis"] = str(synthesis).strip() or None
    state["action_statement"] = action_statement if isinstance(action_statement, dict) else None
    state["structured_extraction"] = structured_extraction if isinstance(structured_extraction, dict) else None
    state["updated_at"] = _now()
    return state


def build_handoff_package(state: dict[str, Any], *, receipt_id: str,
                          library_entry_ids: list[str] | None = None,
                          next_department: str | None = None) -> dict[str, Any]:
    counts = question_counts(state)
    contract = CONTRACTS[state["contract_id"]]
    return {"research_job_id": state.get("research_job_id"), "research_purpose": state["research_purpose"],
        "research_domain": state["research_domain"], "contract_id": state["contract_id"],
        "notebook_id": state.get("notebook_id"), "notebook_status": state.get("verification_status"),
        **counts, "supplementation_attempted": state.get("supplementation_attempted", False),
        "synthesis_present": bool(state.get("synthesis")), "action_statement_present": bool(state.get("action_statement")),
        "structured_extraction_present": bool(state.get("structured_extraction")),
        "library_entry_ids": list(library_entry_ids or []),
        "handoff_payload":{"action_statement":_scrub(state.get("action_statement") or {}),
            "structured_extraction":_scrub(state.get("structured_extraction") or {}),
            "synthesis":str(state.get("synthesis") or "")[:2500]},
        "next_department": next_department or contract["handoff_department"],
        "provenance":{"notebook_id":state.get("notebook_id"),"source_inventory":_compact_sources(state.get("source_inventory") or []),
            "evidence_gaps":[{"question_id":g["question_id"],"evidence_status":g.get("evidence_status"),"unresolved_note":g.get("unresolved_note"),"source_refs":g.get("source_refs",[])} for g in state.get("evidence_gaps",[])],
            "receipt_id":receipt_id,"last_verified_at":state.get("updated_at")}}


def question_counts(state: dict[str, Any]) -> dict[str, int]:
    rows = [q for q in state.get("required_questions", []) if q.get("required")]
    return {"question_count_required":len(rows),"question_count_asked":sum(bool(q.get("asked")) for q in rows),
        "question_count_verified":sum(q.get("evidence_status")=="VERIFIED" for q in rows),
        "question_count_partial":sum(q.get("evidence_status")=="PARTIALLY_VERIFIED" for q in rows),
        "question_count_unverified":sum(q.get("evidence_status")=="UNVERIFIED" for q in rows),
        "question_count_contradicted":sum(q.get("evidence_status")=="CONTRADICTED" for q in rows)}


def verify_completion(state: dict[str, Any], *, web_supplementation_appropriate: bool = True) -> dict[str, Any]:
    rows = [q for q in state.get("required_questions", []) if q.get("required")]
    gaps=state.get("evidence_gaps",[])
    required_action=CONTRACTS[state["contract_id"]]["action_fields"]
    action=state.get("action_statement") if isinstance(state.get("action_statement"),dict) else {}
    normalize=lambda value: re.sub(r"[^A-Z0-9]+","",str(value).upper())
    action_keys={normalize(k) for k in action}
    missing_action_fields=[field for field in required_action if normalize(field) not in action_keys]
    criteria = {
        "all_required_questions_identified": bool(rows),
        "all_required_questions_asked_at_least_once": bool(rows) and all(q.get("asked") for q in rows),
        "all_evidence_gaps_reviewed": all(bool(g.get("reviewed")) for g in gaps),
        "web_supplementation_attempted_where_appropriate": (not web_supplementation_appropriate or all(g.get("supplementation_attempted") or g.get("web_supplementation_not_appropriate") for g in gaps)),
        "unresolved_items_explicitly_marked": all(g.get("reviewed") and g.get("unresolved_note") for g in gaps),
        "synthesis_present": bool(state.get("synthesis")),
        "action_statement_present": bool(action) and not missing_action_fields,
        "structured_extraction_present": bool(state.get("structured_extraction")),
        "handoff_package_present": bool(state.get("handoff_package")),
    }
    return {"complete": all(criteria.values()), "criteria": criteria,
        "question_counts": question_counts(state),
        "missing_action_fields":missing_action_fields,
        "unasked_question_ids":[q["question_id"] for q in rows if not q.get("asked")],
        "unreviewed_gap_ids":[g["question_id"] for g in state.get("evidence_gaps",[]) if not g.get("reviewed")]}


def finalize_contract(state: dict[str, Any], *, receipt_id: str,
                      library_entry_persisted: bool = False, handoff_persisted: bool = False,
                      web_supplementation_appropriate: bool = True) -> dict[str, Any]:
    verification = verify_completion(state, web_supplementation_appropriate=web_supplementation_appropriate)
    if not verification["complete"]:
        state["verification_status"] = "INCOMPLETE"
        return {"ok":False,"state":state,"verification":verification}
    contract = CONTRACTS[state["contract_id"]]
    if contract["is_library"] and not library_entry_persisted:
        state["verification_status"] = "INCOMPLETE"
        verification["complete"] = False
        verification["criteria"]["library_distillation_persisted"] = False
        return {"ok":False,"state":state,"verification":verification}
    if not contract["is_library"] and not handoff_persisted:
        state["verification_status"] = "HANDOFF_PENDING"
        verification["complete"] = False
        verification["criteria"]["compact_handoff_persisted"] = False
        return {"ok":False,"state":state,"verification":verification}
    state["verification_status"] = "COMPLETE"
    state["completion_receipt_id"] = receipt_id
    state["updated_at"] = _now()
    return {"ok":True,"state":state,"verification":verification}


def _scrub(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k):_scrub(v) for k,v in value.items() if str(k).casefold() not in TRANSCRIPT_KEYS}
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    if isinstance(value, str):
        return value[:4000]
    return value


def compact_handoff(state: dict[str, Any], *, receipt_id: str,
                    library_entry_ids: list[str] | None = None, next_department: str | None = None) -> dict[str, Any]:
    package = build_handoff_package(state, receipt_id=receipt_id, library_entry_ids=library_entry_ids,
                                    next_department=next_department)
    def contains_transcript_key(value: Any) -> bool:
        if isinstance(value, dict):
            return any(str(key).casefold() in TRANSCRIPT_KEYS or contains_transcript_key(item)
                       for key,item in value.items())
        if isinstance(value, list):
            return any(contains_transcript_key(item) for item in value)
        return False
    if contains_transcript_key(package):
        raise ValueError("FULL_NOTEBOOK_CONTENT_IN_HANDOFF")
    return package


def persist_state(state: dict[str, Any], *, case_id: str | None = None) -> str:
    """Atomic local checkpoint for contract state; NotebookLM remains corpus of record."""
    identity = re.sub(r"[^A-Za-z0-9_.-]", "_", str(case_id or state.get("research_job_id") or state["contract_id"]))[:120]
    target = CONTRACT_STATE_ROOT / f"{identity}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(_scrub(state), ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    try:
        return str(target.relative_to(ROOT))
    except ValueError:
        return str(target)


def load_state(*, case_id: str | None = None, research_job_id: str | None = None) -> dict[str, Any] | None:
    identity = re.sub(r"[^A-Za-z0-9_.-]", "_", str(case_id or research_job_id or ""))[:120]
    if not identity:
        return None
    target = CONTRACT_STATE_ROOT / f"{identity}.json"
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, ValueError):
        return None


def persist_library_entry(state: dict[str, Any], extraction: dict[str, Any]) -> dict[str, Any]:
    """Persist distilled knowledge to the existing department knowledge library."""
    if CONTRACTS[state["contract_id"]]["is_library"] is not True:
        raise ValueError("MISSION_RESEARCH_NOT_LIBRARY_DISTILLATION")
    if not isinstance(extraction, dict) or not extraction:
        raise ValueError("STRUCTURED_EXTRACTION_REQUIRED")
    from nexus_agent_platform import supabase_knowledge
    experts = ("CLYDE_CREDIT", "ATLAS_OPPORTUNITY") if state["research_domain"] == "BUSINESS_CREATION" else ("CLYDE_CREDIT", "GRANT_FUNDING")
    rows=[]
    for expert in experts:
        stable = "knowledge_" + hashlib.sha256(f"{state['contract_id']}|{state.get('objective')}|{expert}".encode()).hexdigest()[:24]
        row = {"knowledge_id":stable,"finding_id":state.get("research_job_id") or stable,"expert_id":expert,
            "subject":state["research_domain"],"lesson":json.dumps(_scrub(extraction),ensure_ascii=False)[:6000],
            "source_lineage":{"contract_id":state["contract_id"],"notebook_id":state.get("notebook_id"),
                "sources":_compact_sources(state.get("source_inventory") or []),
                "evidence_gaps":[{"question_id":g["question_id"],"evidence_status":g.get("evidence_status"),"unresolved_note":g.get("unresolved_note")} for g in state.get("evidence_gaps",[])]},
            "assessment_lineage":{"research_purpose":state["research_purpose"],"research_domain":state["research_domain"]},
            "result_lineage":{"structured_extraction":_scrub(extraction)},"created_at":_now()}
        code, response = supabase_knowledge._write("department_knowledge",row)
        if code not in {200,201,204}:
            return {"status":"LIBRARY_WRITE_FAILED","expert_id":expert,"http_status":code,"error":response,
                "library_entry_ids":[x["library_entry_id"] for x in rows]}
        rows.append({"library_entry_id":stable,"expert_id":expert,"record":row})
    return {"status":"PERSISTED","library_entry_ids":[x["library_entry_id"] for x in rows],"entries":rows}
