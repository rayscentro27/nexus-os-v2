"""Governed case-type playbooks for iterative NotebookLM research.

Playbooks describe questions and evidence gaps; they never encode conclusions.
The same case and notebook are reused across bounded research iterations.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PLAYBOOK_DIR = ROOT / "configs/research/notebook_playbooks"
REQUIRED_FIELDS = {
    "playbook_id", "case_type", "version", "objective_description", "initial_prompt",
    "required_questions", "optional_questions", "source_classes", "gap_to_source_rules",
    "followup_templates", "expected_output_schema", "handoff_destination",
    "handoff_contract", "completion_criteria",
}


def load_registry() -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    for path in sorted(PLAYBOOK_DIR.glob("*.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        missing = REQUIRED_FIELDS - row.keys()
        if missing:
            raise ValueError(f"{path.name} missing {sorted(missing)}")
        if row["case_type"] in registry:
            raise ValueError(f"duplicate playbook case_type {row['case_type']}")
        row["path"] = str(path.relative_to(ROOT))
        registry[row["case_type"]] = row
    return registry


def select_playbook(*, objective_family: str = "", owner_department: str = "",
                    source_type: str = "", current_goal: str = "", case_context: str = "") -> dict[str, Any]:
    """Select from objective/owner first; source type only breaks ambiguity."""
    family, owner = objective_family.upper(), owner_department.upper()
    text = " ".join((family, owner, source_type, current_goal, case_context)).casefold()
    if "TRADING" in family or "MERCURY_TRADING" in owner or "tradingview" in text or "trading" in text:
        chosen, why = "TRADING_STRATEGY", "Trading objective/owner or strategy source has precedence."
    elif "FUND" in family or "GRANT" in text:
        chosen, why = "FUNDING_GRANT", "Funding or grant objective."
    elif "TECHNOLOGY" in family or "github" in text or "model capability" in text:
        chosen, why = "TECHNOLOGY_CAPABILITY", "Technology capability objective."
    elif "SYSTEM" in family or "UPGRADE" in text or "reliability" in text:
        chosen, why = "NEXUS_SYSTEM_UPGRADE", "Nexus system reliability or upgrade objective."
    elif "CREATIVE" in family or any(x in text for x in ("image generator", "video generator", "avatar", "creative model")):
        chosen, why = "CREATIVE_TOOL_MODEL", "Creative tool/model evaluation objective."
    elif "MARKETING" in family or "campaign" in text or "content pattern" in text:
        chosen, why = "MARKETING_CAMPAIGN_INTELLIGENCE", "Marketing campaign intelligence objective."
    elif "COMPETITOR" in family or "competitor" in text or "market comparison" in text:
        chosen, why = "COMPETITOR_MARKET", "Competitor/market comparison objective."
    elif "CUSTOMER" in family or "complaint" in text or "unmet need" in text:
        chosen, why = "CUSTOMER_NEED_COMPLAINT", "Customer need/complaint evidence is primary."
    elif "BUSINESS" in family or "OPPORTUNITY" in family or "ATLAS_OPPORTUNITY" in owner:
        chosen, why = "BUSINESS_OPPORTUNITY", "Business opportunity development objective."
    else:
        chosen, why = "BUSINESS_OPPORTUNITY", "Default case development playbook; caller should confirm objective fit."
    row = load_registry()[chosen]
    return {**row, "selection_reason": why}


def gap_source_classes(question: str, playbook: dict[str, Any]) -> list[str]:
    low = question.casefold()
    for rule in playbook.get("gap_to_source_rules", []):
        if any(token.casefold() in low for token in rule.get("match_any", [])):
            return list(rule.get("source_classes") or [])
    return list(playbook.get("source_classes") or [])[:3]


def build_notebook_prompt(playbook: dict[str, Any], case: dict[str, Any], *, followup: bool = False) -> str:
    questions = playbook.get("required_questions", [])
    if followup:
        questions = [q.get("question", "") for q in (case.get("open_questions") or [])]
    return (
        str(playbook.get("initial_prompt") or "") + "\n"
        "You are synthesizing evidence inside one Nexus research case. Use only sources in this notebook. "
        "Do not invent missing facts or treat source claims as verified outcomes. Cite source numbers/titles. "
        "For each question label ANSWERED, PARTIALLY_ANSWERED, UNANSWERED, or CONTRADICTORY; state evidence, "
        "source, confidence, and what remains unknown. For unknowns propose a specific follow-up and best source class.\n\n"
        f"CASE_ID: {case.get('case_id')}\nOBJECTIVE: {case.get('objective')}\n"
        f"PLAYBOOK: {playbook['case_type']} v{playbook['version']}\n"
        f"QUESTIONS:\n" + "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions)) +
        "\n\nReturn a structured synthesis with: evidence by question, source agreements, disagreements, "
        "missing information, non-blocking assumptions, true blocking unknowns, recommendation class, "
        "recommended next source classes, and next action. Keep source-supported rules separate from design assumptions."
    )


def analyze_answer(answer: str, questions: list[str], playbook: dict[str, Any]) -> dict[str, Any]:
    """Conservatively map text coverage to explicit dispositions; never fabricate answers."""
    body = (answer or "").casefold()
    rows = []
    for index, question in enumerate(questions, 1):
        # Prefer the model's explicit per-question status in the matching
        # section. The token fallback is only for unnumbered legacy answers.
        section_match = re.search(
            rf"^\s*#{{1,6}}\s*(?:Question\s+)?{index}\s*[.:][^\n]*[\s\S]*?(?=^\s*#{{1,6}}\s*(?:Question\s+)?{index+1}\s*[.:]|\Z)",
            answer or "", re.IGNORECASE | re.MULTILINE,
        )
        explicit = ""
        if section_match:
            status_match = re.search(r"\b(ANSWERED|PARTIALLY_ANSWERED|UNANSWERED|CONTRADICTORY)\b",
                                     section_match.group(0), re.IGNORECASE)
            explicit = status_match.group(1).upper() if status_match else ""
        tokens = [t for t in re.findall(r"[a-z0-9]{4,}", question.casefold()) if t not in {"what", "which", "where", "does", "have", "from", "with", "this", "that", "should"}]
        hits = sum(1 for token in tokens if token in body)
        status = explicit or ("ANSWERED" if hits >= max(2, round(len(tokens) * .45)) else "PARTIALLY_ANSWERED" if hits else "UNANSWERED")
        if any(word in body for word in ("conflicting sources", "sources disagree", "contradictory evidence")) and hits:
            status = "CONTRADICTORY"
        rows.append({"question": question, "status": status,
                     "why_it_matters": "Required by the selected domain playbook.",
                     "best_source_classes": gap_source_classes(question, playbook)})
    return {"question_dispositions": rows,
            "open": [row for row in rows if row["status"] != "ANSWERED"],
            "answered_count": sum(row["status"] == "ANSWERED" for row in rows)}
