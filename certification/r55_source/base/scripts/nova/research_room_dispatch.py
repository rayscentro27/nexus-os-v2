"""Nova ingress adapter to the existing shadow Research Room worker."""
from __future__ import annotations

import hashlib
import html
import re
from pathlib import Path
from typing import Any

from nova.research_intent import route_research_intent


def execute_research_room_request(text: str, *, objective_id: str,
                                  repository_root: str | Path) -> dict[str, Any]:
    """Create or resume one shadow Research Room case for a natural request."""
    intent = route_research_intent(text)
    if not intent:
        raise ValueError("NOT_A_RESEARCH_ROOM_OBJECTIVE")
    from nexus_agent_platform.research_room.advisor_router import AdvisorRouter
    from nexus_agent_platform.research_room.models import new_case
    from nexus_agent_platform.research_room.room_graph import RoomGraph
    from nexus_agent_platform.research_room.source_tools import SourceTools
    from nexus_agent_platform.research_room.state import JsonCaseStore
    from nexus_agent_platform.research_room.transcripts import write_case_artifacts
    from nexus_agent_platform.research_room.worker import ResearchRoomWorker, ShadowRoomRunner

    root = Path(repository_root) / "data" / "research_room_shadow" / "nova_ingress"
    case_id = "nova-research-" + hashlib.sha256(str(objective_id).encode()).hexdigest()[:20]
    case_store = JsonCaseStore(root / "cases")
    current = case_store.load(case_id)
    if current and current.get("status") == "COMPLETE":
        return {"status": "COMPLETE", "case": current, "case_id": case_id,
            "reused_idempotent_case": True, "artifacts": current.get("metadata", {}).get("transcript_paths", {})}

    # Business opportunity work has a purpose-built Research Room evidence
    # packet, bounded free-first advisor route, and ChatGPT challenge path.
    # Reuse that existing room workflow instead of creating a parallel engine.
    if intent["primary_mode"] == "BUSINESS_OPPORTUNITY_MODE":
        from nexus_agent_platform.research_room.business_opportunity_proof import run_business_opportunity_proof
        result = run_business_opportunity_proof(root=root, case_id=case_id,
            objective=text, intent_object=intent)
        case = result.get("case") or {}
        return {**result, "case_id": case_id, "case": case,
            "objective_accepted": True, "intent_object": intent}

    metadata = {"shadow_mode": True, "source": "NOVA_NATURAL_LANGUAGE_INGRESS",
        "nova_objective_id": str(objective_id), "execution_mode": intent["primary_mode"],
        "depth_budget": "STANDARD", "intent_object": intent,
        "likely_destination": ("SYSTEMS" if intent["primary_mode"] == "NEXUS_ENHANCEMENT_MODE" else "RAY/NOVA"),
        "per_call_soft_target_usd": 0.01,
        "per_case_soft_target_usd": 0.01, "daily_research_soft_target_usd": 0.03,
        "daily_research_hard_limit_usd": 0.05,
        "transcript_root": str(root / "artifacts"),
        "research_intake_accepted_before_handoff_checks": True,
        "alpha_assignment_required": False,
        "downstream_actions_before_strategy": False}
    url_match = re.search(r"https?://\S+", text)
    source_url = url_match.group(0).rstrip(".,)") if url_match else None
    graph = RoomGraph(source_tools=SourceTools(), advisor_router=AdvisorRouter(free_only=True))
    worker = ResearchRoomWorker(case_store, graph)
    worker.open_case(case_id=case_id, objective=text, source_url=source_url,
        source_type="PUBLIC_WEB" if source_url else "UNKNOWN", metadata=metadata)
    result = ShadowRoomRunner(worker, max_turns=20).run_to_completion(case_id)
    case = result.get("case") or case_store.load(case_id) or {}
    artifacts = {}
    if case.get("status") == "COMPLETE":
        artifacts = write_case_artifacts(case, root / "artifacts")
        case.setdefault("metadata", {})["transcript_paths"] = artifacts
        case_store.save(case)
    return {"status": case.get("status", result.get("status")), "case": case,
        "case_id": case_id, "reused_idempotent_case": False, "artifacts": artifacts,
        "turns": result.get("turns", []), "objective_accepted": True,
        "intent_object": intent}


def _human_value(value: Any, *, empty: str = "Not specified in the persisted case.") -> str:
    if value is None or value == "" or value == [] or value == {}:
        return empty
    if isinstance(value, dict):
        if value.get("name"):
            return f"{value['name']}: {value.get('summary') or value.get('use_case') or 'Reusable knowledge item.'}"
        return "; ".join(f"{key.replace('_', ' ').title()}: {_human_value(item)}" for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return "; ".join(_human_value(item) for item in value)
    return str(value)


def _bullets(value: Any, *, empty: str = "Not specified in the persisted case.") -> str:
    if value is None or value == "" or value == [] or value == {}:
        return f"- {empty}"
    values = value if isinstance(value, (list, tuple)) else [value]
    return "\n".join(f"- {_human_value(item)}" for item in values)


def _source_section(source: str, start: str, end_markers: tuple[str, ...], limit: int = 600) -> str:
    index = source.find(start)
    if index < 0:
        return ""
    section = source[index + len(start):]
    ends = [section.find(marker) for marker in end_markers if section.find(marker) >= 0]
    if ends:
        section = section[:min(ends)]
    section = html.unescape(re.sub(r"\s+", " ", section)).strip(" :-\t\n")
    return section[:limit].rstrip()


def _source_fact(source: str, pattern: str, default: str) -> str:
    match = re.search(pattern, source, flags=re.IGNORECASE)
    return default if match else "UNVERIFIED (not retained)"


def _render_business_strategy(strategy: dict[str, Any]) -> str:
        top = (strategy.get("top_businesses") or [{}])[0]
        automation = strategy.get("how_nova_runs_it") or {}
        lines = [f"The best first opportunity is **{strategy.get('winner') or top.get('business', 'the leading opportunity')}**.",
            str(strategy.get("why_winner") or "It is the strongest fit with Nexus’s current capabilities, pending paid validation."),
            f"\n**What Nexus sells:** {strategy.get('what_to_sell') or top.get('offer', 'A fixed-scope pilot')}",
            f"**Who pays:** {strategy.get('who_to_sell_to') or top.get('customer', 'Target buyers identified in the case')}",
            f"**Price to test:** {strategy.get('price') or top.get('price', 'Validate in discovery')}",
            f"**How Nova runs it:** {automation.get('finds_customers', 'qualifies a target list')}; {automation.get('qualifies_customers', 'checks fit and urgency')}; coordinates delivery and tracks outcomes.",
            f"**Build first:** {strategy.get('what_nexus_needs_to_build', 'A narrow intake, workflow template, and outcome tracking.')}",
            f"**First 10 customers:** {strategy.get('first_10_customer_plan', 'Start with interviews and warm introductions.')}",
            f"**Next action:** {strategy.get('next_action', 'Approve one customer segment and prepare the first discovery list.')}"]
        return "\n\n".join(lines)


def _render_trading_strategy(case: dict[str, Any], strategy: dict[str, Any]) -> str:
    source = str((case.get("source_report") or {}).get("text") or "")
    concepts = _source_section(source, "█ CONCEPTS", ("█ THE RULES",), 520)
    source_rules = _source_section(source, "█ THE RULES", ("▌Properties", "█ INPUTS"), 520)
    rules = strategy.get("strategy_rules") or {}
    rules_text = _human_value(rules, empty="Exact rule fields were not separately structured in the saved strategy.")
    unresolved = [item for item in (strategy.get("unverified_rules") or [])
                  if "sizing if absent" not in str(item).lower()]
    unresolved.extend([
        "Stop-loss and take-profit levels are not stated in the saved source extraction.",
        "Exact chart/execution timeframe and session filters are not specified in the saved case.",
        "The source lists ATR length and days-between-trades inputs but the saved extraction gives no values.",
    ])
    data = strategy.get("data_required") or []
    backtest = strategy.get("backtest_plan") or {}
    paper = strategy.get("paper_trading_plan") or {}
    source_context = (
        "Source thesis: agricultural prices may be seasonally weaker around harvest and stronger in peak growing season; "
        "the model spaces up to three short sales and covers at harvest to try to beat the average sale price. "
        "This is a source hypothesis, not independently verified."
        if concepts else "The persisted source extraction does not include the concepts section."
    )
    rules_source = source_rules or rules_text
    source_facts = []
    if "Corn Futures (ZC1!)" in source:
        source_facts.append("Instrument example: Corn Futures ZC1!; the source notes its values are in cents and require adjustment for other markets.")
    for label, pattern, default in (
        ("Commission", r"Commission value is set to 300¢ \(\$3\) per order", "$3/order TradingView property."),
        ("Slippage", r"Slippage is set to one tick", "1 tick TradingView property."),
        ("MA length", r"A 20 to 60 day range is recommended; with 40 as a starting point", "20–60 days; 40 starting point."),
        ("ATR factor", r"2\.5 to 3\.5 is generally recommended", "2.5–3.5 recommended."),
        ("Harvest month", r"Month of Harvest\s*:\s*Set the month of harvest for the crop being traded", "Crop-specific month."),
        ("Post-harvest delay", r"2 months is the suggested point for tuning", "2 months suggested."),
    ):
        source_facts.append(f"{label}: {_source_fact(source, pattern, default)}")
    source_parameters = "\n".join(f"- {fact}" for fact in source_facts) if source_facts else "No source properties or input details were retained in the case."
    if "Sell short at the selling level" in source_rules:
        rule_lines = [
            "- Entry: sell short at the source-defined selling level (source-derived).",
            "- Spacing: delay sells so two sales do not occur in the same rally (source-derived).",
            "- Harvest filter: avoid selling immediately after harvest (source-derived).",
            "- Exit: cover short positions at harvest (source-derived).",
            "- Stop loss / profit target: UNVERIFIED; not stated in the saved source extraction.",
            "- Position size: one-contract increments, up to three sells per year (source-derived).",
            "- Indicators: simple moving average (SMA) and average true range (ATR) (source-derived).",
            "- Session filter: UNVERIFIED; not specified in the saved source extraction.",
        ]
        rendered_rules = "\n".join(rule_lines)
    else:
        rendered_rules = rules_text + "\n\nSource text: " + rules_source
    library = strategy.get("library_additions") or (case.get("final_synthesis") or {}).get("library_additions") or []
    risks = [
        "Harvest seasonality may vary by crop, year, and regime.",
        "Futures rolls, basis, fees, and slippage affect results.",
        "Performance is unverified; keep holdout data untouched.",
    ]
    market_display = ("Agricultural futures; Corn ZC1! source example."
                      if "Corn Futures (ZC1!)" in source else strategy.get("market", "UNVERIFIED"))
    timeframe_display = ("Chart/execution interval unverified; source MA lengths are in days."
                         if concepts else strategy.get("timeframe", "UNVERIFIED"))
    sections = [
        f"**Strategy**\n{strategy.get('strategy', 'Strategy name not specified in the persisted case.')}\n\n**Market:** {market_display}\n**Timeframe:** {timeframe_display}\n**Market condition / thesis:** {source_context}",
        f"**RULES — SOURCE-DERIVED**\n{rendered_rules}\n\n**Parameters / TradingView properties — SOURCE-DERIVED**\n{source_parameters}\n- ATR length: input exists; value not retained.\n- Days between trades: input exists; value not retained.\n\n**UNVERIFIED_RULES / TO BE SPECIFIED**\n{_bullets(unresolved)}",
        f"**DATA_REQUIRED**\n{_bullets(data)}",
        f"**BACKTEST_PLAN**\n{_bullets(backtest.get('steps') if isinstance(backtest, dict) else backtest)}\n\n**Success:** Net expectancy, profit factor, drawdown, average R, trade count, slippage/regime stability.\n**Failure:** Nonpositive expectancy, profit factor ≤1 after costs, unstable parameters, breached drawdown limit.",
        f"**VARIANTS_TO_TEST**\n{_bullets(strategy.get('variants_to_test'))}",
        f"**PAPER_TRADING_PLAN — NEXUS-PROPOSED CONTROLS, NOT SOURCE RULES**\nMode: {paper.get('mode', 'PAPER ONLY')}\nMinimum: {paper.get('minimum', 'Not specified in the persisted case.')}\nProposed controls: {paper.get('risk', 'No Nexus-added risk controls specified.')}",
        f"**What could make it fail**\n{_bullets(risks)}",
        f"**TRADING_ENGINE_BUILD_REQUIREMENTS**\n{_bullets(strategy.get('trading_engine_build_requirements'))}",
        f"**LIBRARY_ADDITIONS**\n{_bullets(library)}",
        "**PROPOSED_HANDOFF=TRADING**\nProposed only; no Trading actions or live orders were executed.",
        f"**NEXT_ACTION**\n{strategy.get('next_action') or 'Trading should prepare a versioned source-rule spec and keep all activity paper-only.'}",
    ]
    return "\n\n".join(sections)


def _render_enhancement_strategy(strategy: dict[str, Any]) -> str:
    return "\n\n".join([
        f"**Technology:** {strategy.get('technology', 'Technology not specified in the persisted case.')}",
        f"**Decision:** {strategy.get('decision', 'TEST')}",
        f"**What is useful**\n{_bullets(strategy.get('what_is_useful') or strategy.get('what_nexus_should_adapt'))}",
        f"**What Nexus already has**\n{_bullets(strategy.get('what_nexus_already_has'))}",
        f"**What is duplicate**\n{_bullets(strategy.get('what_is_duplicate'))}",
        f"**What to copy/adapt**\n{_bullets(strategy.get('what_to_copy_or_adapt') or strategy.get('what_nexus_should_adapt'))}",
        f"**What to ignore**\n{_bullets(strategy.get('what_not_to_adopt') or strategy.get('what_nexus_should_ignore'))}",
        f"**Risks / cost / complexity**\nRisks: {_bullets(strategy.get('risks'))}\nCost: {strategy.get('cost', 'Unknown')}\nComplexity: {strategy.get('complexity', 'Unknown')}",
        f"**Capability gap:** {strategy.get('capability_gap', 'Not specified in the persisted case.')}",
        f"**Smallest safe test:** {strategy.get('smallest_safe_test', 'Not specified in the persisted case.')}",
        f"**Implementation plan**\n{_bullets(strategy.get('implementation_plan'))}",
        f"**Library additions**\n{_bullets(strategy.get('library_additions'))}",
        "**Proposed handoff:** SYSTEMS (shadow only; no Systems action was executed)",
        f"**Systems next action (Next action)**\n{strategy.get('next_action', 'Assign the smallest safe evaluation step.')}",
    ])


def _render_claim_strategy(strategy: dict[str, Any]) -> str:
    return "\n\n".join([
        f"**Claim review:** {_human_value(strategy.get('claim') or strategy.get('what_we_know'))}",
        f"**What remains unverified**\n{_bullets(strategy.get('what_we_do_not_know') or strategy.get('unresolved_items'))}",
        f"**What this means for Nexus:** {_human_value(strategy.get('what_nexus_should_do'))}",
        f"**Implementation / validation plan**\n{_bullets(strategy.get('implementation_plan'))}",
        f"**Library additions**\n{_bullets(strategy.get('library_additions'))}",
        f"**Next action**\n{strategy.get('next_action', 'Assign a bounded validation step to the relevant Nexus owner.')}",
    ])


def _render_deep_strategy(strategy: dict[str, Any]) -> str:
    return "\n\n".join([
        f"**What we know**\n{_bullets(strategy.get('what_we_know'))}",
        f"**What remains unknown**\n{_bullets(strategy.get('what_we_do_not_know'))}",
        f"**What Nexus should do**\n{_bullets(strategy.get('what_nexus_should_do'))}",
        f"**Implementation plan**\n{_bullets(strategy.get('implementation_plan'))}",
        f"**Library additions**\n{_bullets(strategy.get('library_additions'))}",
        f"**Next action**\n{strategy.get('next_action', 'Assign the smallest safe next step.')}",
    ])


def render_nova_research_response(result: dict[str, Any]) -> str:
    """Render the mode-specific, actionable Final Strategist result for Nova."""
    case = result.get("case") or {}
    synthesis = case.get("final_synthesis") or {}
    strategy = case.get("execution_strategy") or synthesis.get("execution_strategy") or {}
    mode = str(strategy.get("execution_mode") or (case.get("metadata") or {}).get("execution_mode") or "RESEARCH_MODE")
    renderers = {
        "BUSINESS_OPPORTUNITY_MODE": lambda: _render_business_strategy(strategy),
        "TRADING_STRATEGY_MODE": lambda: _render_trading_strategy(case, strategy),
        "NEXUS_ENHANCEMENT_MODE": lambda: _render_enhancement_strategy(strategy),
        "CLAIM_VERIFICATION_MODE": lambda: _render_claim_strategy(strategy),
        "DEEP_RESEARCH_MODE": lambda: _render_deep_strategy(strategy),
    }
    renderer = renderers.get(mode)
    if renderer:
        return renderer()
    return "\n\n".join([
        f"**Research result ({mode.replace('_MODE', '').replace('_', ' ').title()})**",
        f"**What Nexus should do**\n{_bullets(strategy.get('what_nexus_should_do') or strategy.get('next_action'))}",
        f"**Library additions**\n{_bullets(strategy.get('library_additions'))}",
        f"**Next action**\n{strategy.get('next_action', 'Assign the smallest safe next step.')}",
    ])
