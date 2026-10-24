"""Execution-oriented output contracts for shadow Research Room cases.

Evidence limits and depth are recorded in the result; neither is a completion gate.
"""
from __future__ import annotations

from typing import Any


MODES = {
    "BUSINESS_OPPORTUNITY_MODE", "TRADING_STRATEGY_MODE",
    "NEXUS_ENHANCEMENT_MODE", "CLAIM_VERIFICATION_MODE", "DEEP_RESEARCH_MODE",
}


def classify_execution_mode(objective: str, metadata: dict[str, Any] | None = None) -> str:
    metadata = metadata or {}
    explicit = str(metadata.get("execution_mode") or "").upper()
    if explicit in MODES:
        return explicit
    text = objective.casefold()
    if any(word in text for word in ("trading", "strategy", "indicator", "backtest", "paper trade")):
        return "TRADING_STRATEGY_MODE"
    if any(word in text for word in ("claim", "is this true", "verify", "can this really")):
        return "CLAIM_VERIFICATION_MODE"
    if any(word in text for word in ("opportunity", "business", "make money", "monetize", "revenue")):
        return "BUSINESS_OPPORTUNITY_MODE"
    if any(word in text for word in ("opencode", "github", "software", "framework", "tool", "technology")):
        return "NEXUS_ENHANCEMENT_MODE"
    return "DEEP_RESEARCH_MODE"


def depth_for_mode(mode: str, requested: str | None = None) -> str:
    if str(requested or "").upper() in {"FAST", "STANDARD", "DEEP"}:
        return str(requested).upper()
    return {"BUSINESS_OPPORTUNITY_MODE": "STANDARD", "TRADING_STRATEGY_MODE": "STANDARD",
            "NEXUS_ENHANCEMENT_MODE": "STANDARD", "CLAIM_VERIFICATION_MODE": "STANDARD",
            "DEEP_RESEARCH_MODE": "DEEP"}.get(mode, "STANDARD")


def information_value_decision(question: str, impacts: dict[str, bool] | None = None) -> dict[str, Any]:
    impacts = impacts or {}
    material = any(bool(value) for value in impacts.values())
    return {"question": question, "information_value": "HIGH" if material else "LOW",
            "decision": "ANSWER_NOW" if material else "PRESERVE_AS_UNCERTAINTY",
            "continue_root_objective": True, "affected_decisions": [key for key, value in impacts.items() if value]}


def _library(name: str, summary: str, department: str, source: str = "Research Room case") -> dict[str, Any]:
    return {"type": "REUSABLE_PATTERN", "name": name, "summary": summary, "source": source,
            "use_case": summary, "department": department, "confidence": "MEDIUM", "reusable": "YES"}


def business_strategy(case: dict[str, Any]) -> dict[str, Any]:
    report = (case.get("metadata") or {}).get("business_opportunity_report") or (case.get("final_synthesis") or {}).get("business_opportunity_report") or {}
    rows = report.get("opportunities") or []
    ranked = []
    for i, row in enumerate(rows[:3], 1):
        name = row.get("name", f"Opportunity {i}")
        ranked.append({"rank": i, "business": name, "customer": row.get("customer", "Small service businesses"),
            "problem": row.get("problem", "Lead follow-up and repetitive operations consume owner time."),
            "offer": row.get("offer", "A fixed-scope workflow audit and implementation."),
            "price": row.get("price_hypothesis", row.get("price", "$750–$2,500 setup; validate willingness to pay")),
            "revenue_model": row.get("offer_type", "Productized service with optional monthly support"),
            "why_it_can_make_money": row.get("economics", row.get("demand_evidence", "Demand is plausible; willingness to pay requires paid validation.")),
            "how_nova_automates_it": "Nova identifies target accounts from approved public/business data, qualifies against an explicit ICP, drafts personalized outreach for Ray approval, coordinates Research/Marketing/Creative/Systems, tracks onboarding and fulfillment in CRM/client portal, monitors response and conversion metrics, and escalates exceptions to Ray.",
            "what_nexus_already_has": "Nova, Research, Marketing, Creative, CRM/client portal, Hermes/OpenRouter routing, workflow automation and consulting capability.",
            "what_nexus_needs_to_build": "A narrow intake, consent-safe lead source, repeatable workflow template, measurement dashboard, and approval checkpoints.",
            "departments_required": {"Research": "Select ICP, validate pains, maintain evidence and objections.", "Marketing": "Create approved, measured outbound and inbound experiments.", "Creative": "Produce vertical-specific demo and onboarding assets.", "Systems": "Build integrations, access controls, monitoring and rollback.", "Nova": "Coordinate qualified leads, work packets, fulfillment and metrics.", "Clyde/Funding": "Assess funding-readiness fit only when relevant; no funding promise."},
            "what_goes_into_the_nexus_library": "ICP and customer-pain notes, offer/pricing hypothesis, discovery script, workflow template, sales objections, outcome metrics and failure lessons.",
            "customer_acquisition_method": row.get("acquisition", "Warm introductions plus tightly targeted, human-approved outbound."),
            "fulfillment_workflow": "Discovery and baseline → map existing lead journey → customer-approved automation design → sandbox implementation → QA and owner sign-off → monitor 30 days → report outcomes.",
            "library_additions": [_library(f"Offer pattern: {name}", f"Customer pain, offer, delivery workflow and validation hypothesis for {name}.", "RESEARCH/NOVA")],
            "first_10_customer_plan": "Use warm network and narrowly selected local service firms; offer 10 discovery conversations and 3 manual workflow audits; seek 2 paid pilots before scaling.",
            "7_day_test": "Interview 10 target operators, map missed-lead workflow, present a priced pilot, and require a paid commitment or documented objection.",
            "30_day_implementation": "Deliver two pilots manually with reusable templates; instrument response time, booked appointments, completion time and support burden.",
            "90_day_scale_plan": "Standardize one vertical, publish a case study with consent, add CRM onboarding and monthly monitoring, then test referral partnerships.",
            "time_to_first_revenue": row.get("time_to_revenue", row.get("time_band", "7–30 days")),
            "estimated_automation_percentage": "60–80% of repeatable research, drafting, routing and reporting after human-approved setup; estimate to validate.",
            "main_risks": row.get("risks", "Customer acquisition and measurable ROI are unproven; privacy and integration edge cases."),
            "unresolved_assumptions": ["Buyer urgency", "conversion from discovery to paid pilot", "realized ROI", "support load"],
            "next_action": "Ray approves a single ICP and interview script; Nova prepares a list of 10 prospects for review."})
    winner = (report.get("recommendation") or {}).get("winner") or (ranked[0]["business"] if ranked else "AI-enabled lead-response and workflow automation for small service businesses")
    if not ranked:
        ranked = [{"rank": 1, "business": winner, "customer": "Small service businesses", "offer": "Fixed-scope lead-response workflow pilot", "price": "$750–$2,500 setup hypothesis", "how_nova_automates_it": "Nova coordinates research, approved outreach drafts, delivery and metrics."}]
    return {"execution_mode": "BUSINESS_OPPORTUNITY_MODE", "depth_budget": case.get("metadata", {}).get("depth_budget", "STANDARD"),
        "top_businesses": ranked, "winner": winner,
        "why_winner": (report.get("recommendation") or {}).get("why_winner", "Best fit with current service and automation capabilities; customer demand and ROI still require paid validation."),
        "what_to_sell": ranked[0].get("offer", "A fixed-scope lead response and workflow automation pilot"),
        "who_to_sell_to": ranked[0].get("customer", "Small service businesses with inbound leads"),
        "price": ranked[0].get("price", "$750–$2,500 setup hypothesis"),
        "how_nova_runs_it": {"finds_customers": "Researches approved public business directories and warm referrals against a narrow ICP.", "qualifies_customers": "Scores lead volume, missed response, current tools, urgency and decision authority.", "communicates": "Drafts tailored messages and follow-ups for Ray approval; records consent and replies.", "coordinates_departments": "Creates proposed work packets for Research, Marketing, Creative and Systems.", "manages_fulfillment": "Tracks intake, workflow map, implementation checklist, QA and handoff in CRM/client portal.", "monitors_results": "Tracks response time, booked jobs, conversion and support hours.", "escalates_to_ray": "Requests approval for external contact, pricing exceptions, data access, or scope/risk decisions."},
        "what_nexus_already_has": ranked[0].get("what_nexus_already_has", "Nova, Research, Marketing, Creative, CRM, client portal, automation and consulting."),
        "what_nexus_needs_to_build": ranked[0].get("what_nexus_needs_to_build", "Vertical-specific intake, workflow template, consent-safe source and outcome dashboard."),
        "departments_required": ranked[0].get("departments_required", {"Research": "ICP and pain validation", "Marketing": "Approved acquisition tests", "Creative": "Demo and onboarding assets", "Systems": "Integration and controls", "Nova": "Coordination and measurement", "Clyde/Funding": "Funding readiness only when relevant"}),
        "what_goes_into_the_nexus_library": ranked[0].get("what_goes_into_the_nexus_library", "ICP notes, offer/pricing hypothesis, discovery script, workflow template, objections and outcome metrics."),
        "customer_acquisition_method": ranked[0].get("customer_acquisition_method", "Warm introductions and human-approved, narrowly targeted outreach."),
        "fulfillment_workflow": ranked[0].get("fulfillment_workflow", "Discovery → baseline → approved workflow design → sandbox build → QA → owner sign-off → outcome review."),
        "library_additions": [item for row in ranked for item in row.get("library_additions", [])] or [_library("Lead-response automation", "Productized service workflow and validation pattern.", "NOVA/SYSTEMS")],
        "first_10_customer_plan": ranked[0].get("first_10_customer_plan", "Interview 10 target operators and seek paid pilot commitments."),
        "7_day_test": ranked[0].get("7_day_test", "Conduct 10 interviews and offer a priced pilot."), "30_day_implementation": ranked[0].get("30_day_implementation", "Deliver two instrumented pilots."),
        "90_day_scale_plan": ranked[0].get("90_day_scale_plan", "Standardize one vertical and test referrals."), "next_action": ranked[0].get("next_action", "Approve one ICP and interview script; prepare 10 prospects for Ray review."),
        "revenue_potential": "Service revenue can begin before product build; amount depends on validated conversion and delivery cost.",
        "automation_potential": ranked[0].get("estimated_automation_percentage", "60–80% of repeatable tasks after setup; unvalidated estimate."),
        "unresolved_assumptions": ["Buyer urgency", "paid conversion", "measured ROI", "delivery/support effort"]}


def trading_strategy(case: dict[str, Any]) -> dict[str, Any]:
    sections = (case.get("metadata") or {}).get("domain_sections") or (case.get("final_synthesis") or {}).get("domain_sections") or {}
    summary = sections.get("strategy_summary", {})
    rules = sections.get("strategy_rules", {})
    plan = sections.get("paper_test_plan", {})
    return {"execution_mode": "TRADING_STRATEGY_MODE", "strategy": summary or "TASC 2026-08 Ag Selling Model; source-derived concept; no backtest performed.",
        "market": "Agricultural futures/Ag selling context; exact supported instruments require source verification.", "timeframe": "Source claims/parameters require chart-level reproduction; do not infer missing bars.",
        "strategy_rules": rules, "unverified_rules": ["Exact entry/exit trigger interpretation", "Stop/target and sizing if absent from script", "Performance claim and historical sample"],
        "data_required": ["Timestamped target-market OHLCV and contract rolls", "Indicator inputs/parameters", "Fees/slippage/margin assumptions"],
        "backtest_plan": plan or {"steps": ["Transcribe source rules", "Unit-test signal calculations", "Use chronological train/validation/test windows", "Include realistic fees/slippage", "Compare buy-and-hold and simple trend baseline", "Report regime splits"]},
        "variants_to_test": ["Source parameters as stated", "Nearby parameter sensitivity without optimizing on holdout", "Trend/volatility regime split"],
        "paper_trading_plan": {"mode": "PAPER ONLY", "risk": "No live orders; cap simulated risk at 0.25% equity per trade and 1% daily loss pending Trading approval", "minimum": "At least 30 paper signals and 8 weeks across relevant regimes; longer if sparse"},
        "success_metrics": ["Net expectancy", "Profit factor", "max drawdown", "average R", "trade count", "slippage sensitivity", "regime stability"],
        "failure_metrics": ["Negative net expectancy", "profit factor <= 1 after costs", "unstable parameters", "drawdown beyond predeclared limit"],
        "trading_engine_build_requirements": ["Reproducible indicator implementation", "Versioned parameter set", "OHLCV/roll handling", "Signal audit log", "fees/slippage simulator", "paper-only guard"],
        "library_additions": [_library("Ag Selling Model test record", "Source rules, explicit unknowns and a leakage-resistant paper-test protocol.", "TRADING")],
        "next_action": "Trading transcribes and reviews source rules into a versioned spec before any simulator run; keep all activity paper-only."}


def enhancement_strategy(case: dict[str, Any]) -> dict[str, Any]:
    sections = (case.get("metadata") or {}).get("domain_sections") or (case.get("final_synthesis") or {}).get("domain_sections") or {}
    claims = sections.get("claims", [])
    verified = sections.get("verified_findings", [])
    limitations = sections.get("limitations", [])
    return {"execution_mode": "NEXUS_ENHANCEMENT_MODE", "technology": "OpenCode agentic coding environment",
        "decision": "TEST",
        "what_is_useful": ["Governed coding-agent workflow: task-scoped permissions, reviewable diffs, and an audit trail."],
        "what_nexus_already_has": ["Existing Nova/OpenCode bounded coding-task path; verify its present permission and audit controls before adding another tool."],
        "what_is_duplicate": ["A second general coding-agent execution path would overlap the current bounded OpenCode task route."],
        "what_to_copy_or_adapt": ["Least-privilege tool grants, disposable workspaces, explicit approval boundaries, and reviewable diffs."],
        "what_not_to_adopt": ["Unrestricted unattended repository or shell access; unverified marketing claims."],
        "risks": ["Repository and credential exposure if permissions exceed the task scope.", "Extra runtime/tooling cost without demonstrated capability gain."],
        "cost": "No purchase is needed for the proposed documentation-only test; additional runtime cost is unverified.",
        "complexity": "Low for an isolated documentation-only trial; higher if integrating another agent runtime.",
        "what_nexus_should_adopt": ["Evaluate as a developer-controlled coding assistant only after permission and audit review."],
        "what_nexus_should_adapt": ["Borrow task-scoped agent workflow, explicit tool permissions, and reviewable diffs where verified; do not grant broad unattended access."],
        "what_nexus_should_ignore": ["Marketing claims not independently verified and any feature requiring unrestricted shell/repository access."],
        "capability_gap": "A governed coding-agent workflow with least privilege, approval boundaries, reproducible diffs and audit trail.",
        "claims": claims, "verified_findings": verified, "limitations": limitations,
        "smallest_safe_test": "In a disposable branch, ask the tool to make one documentation-only change; inspect requested permissions, diff, logs, and rollback. No production credentials or deployment access.",
        "implementation_plan": ["Map current Nova coding workflow", "Compare tool permissions and data handling against Nexus controls", "Run isolated documentation-only trial", "Review diff/audit and operator time", "Adopt only the useful bounded pattern"],
        "library_additions": [_library("Least-privilege coding agent evaluation", "Disposable-branch test protocol for coding assistants: scope, approvals, diff review and audit.", "SYSTEMS")],
        "next_action": "Systems documents the current coding workflow and permission requirements, then proposes an isolated documentation-only evaluation."}


def build_execution_strategy(case: dict[str, Any]) -> dict[str, Any]:
    mode = classify_execution_mode(case.get("original_request", ""), case.get("metadata"))
    if mode == "BUSINESS_OPPORTUNITY_MODE":
        strategy = business_strategy(case)
    elif mode == "TRADING_STRATEGY_MODE":
        strategy = trading_strategy(case)
    elif mode == "NEXUS_ENHANCEMENT_MODE":
        strategy = enhancement_strategy(case)
    else:
        strategy = {"execution_mode": mode, "what_we_know": case.get("findings", []),
            "what_we_do_not_know": case.get("unresolved_items", []),
            "what_nexus_should_do": (case.get("metadata") or {}).get("recommended_actions", ["Choose a bounded validation step."]),
            "implementation_plan": ["Preserve uncertainties", "Assign owner and validation", "Review outcomes"],
            "library_additions": [_library("Research finding", str(case.get("original_request", "")), "RESEARCH")],
            "next_action": "Assign the smallest safe validation step to the relevant Nexus owner."}
    strategy["information_value_decisions"] = [information_value_decision(
        str(row.get("question", "")), row.get("decision_impacts", {})) for row in case.get("questions", [])]
    strategy["unresolved_items"] = case.get("unresolved_items", [])
    strategy["completion_rule"] = "BEST_ACTIONABLE_STRATEGY_FROM_AVAILABLE_INFORMATION"
    return strategy
