"""Secret-safe full advisor transcript and case report artifacts."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_SECRET = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+|((?:api[_-]?key|token|password|secret)\s*[:=]\s*)[^\s,;]+")


def redact(value: Any) -> str:
    text = str(value if value is not None else "UNKNOWN")
    return _SECRET.sub(lambda m: (m.group(1) or "") + "[REDACTED]" if m.group(1) else (m.group(2) or "") + "[REDACTED]", text)


def _business_report_markdown(case: dict[str, Any]) -> str:
    synthesis = case.get("final_synthesis") or {}
    strategy = synthesis.get("execution_strategy") or case.get("execution_strategy") or {}
    mode = strategy.get("execution_mode") or case.get("metadata", {}).get("execution_mode")
    if not mode:
        mode = "BUSINESS_OPPORTUNITY_MODE" if ((case.get("metadata") or {}).get("business_opportunity_report") or synthesis.get("business_opportunity_report")) else "DEEP_RESEARCH_MODE"
    if mode != "BUSINESS_OPPORTUNITY_MODE":
        return "\n".join(["# Nexus Execution Strategy", "", f"Case: {case.get('case_id', 'UNKNOWN')}",
            f"Mode: {mode}", f"Status: {case.get('status', 'UNKNOWN')}", "", "## Strategy", "",
            "```json", json.dumps(strategy, ensure_ascii=False, indent=2, default=str), "```", "",
            "## Proposed Handoff", "", json.dumps(case.get("handoff", {}), ensure_ascii=False, indent=2, default=str), ""])
    report = synthesis.get("business_opportunity_report") or (case.get("metadata") or {}).get("business_opportunity_report") or {}
    recommendation = report.get("recommendation") or {}
    lines = ["# Final Research Report", "", f"Case: {case.get('case_id', 'UNKNOWN')}",
        f"Status: {case.get('status', 'UNKNOWN')}", "", "## Recommendation", "",
        f"**Winner:** {recommendation.get('winner', 'UNKNOWN')}", "",
        str(recommendation.get("why_winner", "No recommendation persisted.")), "",
        f"**What Nexus should sell:** {recommendation.get('what_to_sell', 'UNKNOWN')}", "",
        f"**Target customer:** {recommendation.get('target_customer', 'UNKNOWN')}", "",
        f"**Proposed price:** {recommendation.get('proposed_price', 'UNKNOWN')}", "",
        f"**Why not #2:** {recommendation.get('why_not_opportunity_2', 'UNKNOWN')}", "",
        f"**Why not #3:** {recommendation.get('why_not_opportunity_3', 'UNKNOWN')}", "",
        "## Ranked Opportunities", ""]
    for index, opportunity in enumerate(report.get("opportunities", []), 1):
        lines.extend([f"### {index}. {opportunity.get('name', 'Unnamed opportunity')}", "",
            f"**Weighted score:** {opportunity.get('weighted_score', 'UNKNOWN')}/10  ",
            f"**Raw score:** {opportunity.get('total_score', 'UNKNOWN')}/120  ",
            f"**Time to revenue:** {opportunity.get('time_to_revenue', opportunity.get('time_band', 'UNKNOWN'))}", "",
            f"**Customer:** {opportunity.get('customer', 'UNKNOWN')}", "",
            f"**Problem and urgency:** {opportunity.get('problem', 'UNKNOWN')}", "",
            f"**Demand evidence:** {opportunity.get('demand_evidence', 'UNKNOWN')}", "",
            f"**Offer:** {opportunity.get('offer', 'UNKNOWN')}", "",
            f"**Offer type:** {opportunity.get('offer_type', 'UNKNOWN')}", "",
            f"**Price hypothesis:** {opportunity.get('price_hypothesis', 'UNKNOWN')}", "",
            f"**Economics:** {opportunity.get('economics', 'UNKNOWN')}", "",
            f"**Acquisition:** {opportunity.get('acquisition', 'UNKNOWN')}", "",
            f"**Competition:** {opportunity.get('competition', 'UNKNOWN')}", "",
            f"**Nexus fit and gaps:** {opportunity.get('nexus_fit', 'UNKNOWN')}", "",
            f"**Scalability:** {opportunity.get('scalability', 'UNKNOWN')}", "",
            f"**Risks:** {opportunity.get('risks', 'UNKNOWN')}", "",
            f"**Validation test:** {opportunity.get('validation_test', 'UNKNOWN')}", "",
            "**Dimension scores (1–10):**", ""])
        for dimension, score in (opportunity.get("scores") or {}).items():
            lines.append(f"- {dimension.replace('_', ' ').title()}: {score}/10")
        lines.append("")
    for title, key in (("First 10 Customer Plan", "first_10_customer_plan"),
        ("7-Day Validation Plan", "seven_day_validation_plan"), ("30-Day Launch Plan", "thirty_day_launch_plan"),
        ("Success Metrics", "success_metrics"), ("Kill or Pivot Signals", "kill_or_pivot_signals")):
        lines.extend([f"## {title}", ""])
        for item in recommendation.get(key, []):
            lines.append(f"- {item}")
        lines.append("")
    needle = case.get("needle_result") or {}
    lines.extend(["## Needle and Unresolved Questions", "",
        f"Result: {needle.get('coverage_status', 'UNKNOWN')}", "",
        f"Requested question: {needle.get('requested_question', 'UNKNOWN')}", ""])
    for question in needle.get("missing_questions", []):
        lines.append(f"- {question}")
    lines.extend(["", "## Advisor Comparison", ""])
    comparison = case.get("multi_advisor_comparison") or {}
    for heading, key in (("Agreements", "agreements"), ("Disagreements", "disagreements")):
        lines.append(f"**{heading}:**")
        lines.extend(f"- {item}" for item in comparison.get(key, []))
        lines.append("")
    lines.extend(["**Second advisor added material value:** " + str(comparison.get("second_advisor_material_value", "UNKNOWN")), "",
        "## Public Sources", ""])
    for source in case.get("source_references", []):
        lines.append(f"- [{source.get('title', 'Source')}]({source.get('url', 'UNKNOWN')})")
    lines.extend(["", "## Proposed Handoff", "", json.dumps(case.get("handoff", {}), ensure_ascii=False, indent=2, default=str), ""])
    return "\n".join(lines)


def write_case_artifacts(case: dict[str, Any], root: str | Path) -> dict[str, str]:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    case_id = str(case["case_id"])
    markdown_path = root / f"{case_id}.transcript.md"
    jsonl_path = root / f"{case_id}.transcript.jsonl"
    report_path = root / f"{case_id}.final-report.md"
    cost_path = root / f"{case_id}.cost-report.json"
    lines = ["# Research Room Transcript", "", "## Case", f"Case ID: {case_id}",
        f"Objective: {redact(case.get('original_request'))}", f"Started: {case.get('created_at', 'UNKNOWN')}",
        f"Completed: {case.get('updated_at', 'UNKNOWN')}", f"Status: {case.get('status', 'UNKNOWN')}", ""]
    events = [{"event": "case", "case_id": case_id, "objective": redact(case.get("original_request")),
        "status": case.get("status"), "started": case.get("created_at"), "completed": case.get("updated_at")}]
    for session in case.get("advisor_sessions", []):
        role = str(session.get("role") or "Advisor")
        lines.extend([f"## {role}", f"Provider: {session.get('provider', 'UNKNOWN')}",
            f"Model: {session.get('model', 'UNKNOWN')}", "", "### Input sent", "", "```text",
            redact(session.get("input_prompt", "UNKNOWN")), "```", "", "### Full response", "", "```text",
            redact(session.get("full_response", "UNKNOWN")), "```", "",
            f"Tokens: {json.dumps(session.get('usage', {}), sort_keys=True)}",
            f"Cost: {session.get('estimated_cost_usd', 'UNKNOWN')}",
            f"Latency ms: {session.get('duration_ms', 'UNKNOWN')}", ""])
        events.append({"event": "advisor_session", **{k: redact(v) if k in {"input_prompt", "full_response"} else v for k, v in session.items()}})
    participant_inputs = {
        "RESEARCH_LEAD": ("Coordinate evidence review, questions, comparison, synthesis, and a shadow-only proposed handoff.",
            json.dumps(case.get("advisor_plan", {}), ensure_ascii=False, default=str)),
        "SOURCE_ANALYST": (case.get("original_request", "UNKNOWN"), (case.get("source_report") or {}).get("text", "UNKNOWN")),
        "FACT_CHECKER": (json.dumps(case.get("source_references", []), ensure_ascii=False),
            json.dumps([x for x in case.get("findings", []) if x.get("kind") == "FACT_CHECK"], ensure_ascii=False)),
        "NEEDLE": ((case.get("needle_result") or {}).get("requested_question", "UNKNOWN"),
            json.dumps(case.get("needle_result", {}), ensure_ascii=False)),
        "FINAL_STRATEGIST": (json.dumps({"advisors": case.get("advisor_comments", []),
            "answers": case.get("answers", []), "uncertainties": case.get("unresolved_items", [])}, ensure_ascii=False, default=str),
            json.dumps(case.get("final_synthesis", {}), ensure_ascii=False, default=str)),
    }
    for role, (input_text, response_text) in participant_inputs.items():
        lines.extend([f"## {role.replace('_', ' ').title()}", "", "### Input", "", "```text",
            redact(input_text), "```", "", "### Full response", "", "```text", redact(response_text), "```", ""])
        events.append({"event": "participant", "role": role, "input": redact(input_text), "full_response": redact(response_text)})
    lines.extend(["## Source Evidence", ""])
    for ref in case.get("source_references", []):
        lines.append(f"- {ref.get('title', 'Source')}: {ref.get('url', 'UNKNOWN')} ({ref.get('kind', ref.get('type', 'PUBLIC'))})")
        events.append({"event": "source", **ref})
    lines.extend(["", "## Needle", "", json.dumps(case.get("needle_result", {}), indent=2, ensure_ascii=False),
        "", "## Final Strategist", "", json.dumps(case.get("execution_strategy") or case.get("final_synthesis", {}).get("execution_strategy") or case.get("final_synthesis", {}), indent=2, ensure_ascii=False),
        "", "## Proposed Handoff", "", json.dumps(case.get("handoff", {}), indent=2, ensure_ascii=False), ""])
    events.extend([{"event": "needle", "result": case.get("needle_result", {})},
        {"event": "final_synthesis", "content": case.get("final_synthesis", {})},
        {"event": "proposed_handoff", "content": case.get("handoff", {})}])
    markdown_text = "\n".join(redact(x) for x in lines)
    # Advisor/provider payloads sometimes arrive with newline characters escaped
    # as the two printable characters ``\\n``. Render those as paragraph breaks
    # in human Markdown; JSONL retains the lossless machine representation.
    markdown_path.write_text(markdown_text.replace("\\n", "\n"), encoding="utf-8")
    jsonl_path.write_text("\n".join(redact(json.dumps(row, ensure_ascii=False, default=str)) for row in events) + "\n", encoding="utf-8")
    report_path.write_text(redact(_business_report_markdown(case)) + "\n", encoding="utf-8")
    cost_path.write_text(json.dumps(case.get("model_usage", {}), indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    return {"markdown": str(markdown_path), "jsonl": str(jsonl_path), "final_report": str(report_path), "cost_report": str(cost_path)}
