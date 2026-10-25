"""Customer-first proactive selector for the existing Research worker."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from research.proactive_research_memory import persist_state, query_tokens

HISTORY = ROOT / "data/governed/proactive_research_objective_runs.jsonl"
RECENT_DAYS = 30
SATURATION_HOURS = 168

# Concrete domains remain search results for a current question, not permanent sources.
FAMILIES: tuple[dict[str, Any], ...] = (
    {"family":"CUSTOMER_NEEDS","business_reason":"Find unmet customer demand that could support a useful Nexus offer.","target":"small-business owners, creators, and people using digital services","question":"What recurring customer questions point to a problem that current products or services do not solve well?","queries":["recurring customer questions about small business operations software onboarding payments","creator small business owner asks for practical tools to save time customer demand"],"source_class":"CUSTOMER_DISCUSSIONS","useful":"Repeated first-person questions, concrete obstacles, and corroborating current alternatives.","priority":10,"customer_value":10,"revenue":7,"department_need":7,"expected_gain":8},
    {"family":"CUSTOMER_COMPLAINTS","business_reason":"Identify repeated service failures and costly friction customers describe.","target":"customers using business software, online services, and creator tools","question":"Which recurring customer complaints show that existing digital products or services leave important needs unmet?","queries":["customer complaints about small business software billing support onboarding data export","creator tool users complaints subscription pricing customer support workflow limits"],"source_class":"CUSTOMER_DISCUSSIONS","useful":"Specific repeated complaints with dated source evidence and identifiable affected customers.","priority":9,"customer_value":10,"revenue":7,"department_need":7,"expected_gain":8},
    {"family":"BUSINESS_OPPORTUNITIES","business_reason":"Find customer problems with evidence for a service, product, or affiliate response.","target":"small-business owners, independent operators, and digital product customers","question":"Which customer problems have evidence for a practical product, service, or partner solution?","queries":["customer workflow problem product service opportunity independent operators digital tools","recurring customer support friction current alternatives paid service opportunity"],"source_class":"WEB_SEARCH","useful":"A specific problem, affected group, current alternatives, and evidence of unmet demand.","priority":9,"customer_value":9,"revenue":10,"department_need":8,"expected_gain":9},
    {"family":"AFFILIATE_OPPORTUNITIES","business_reason":"Find existing products that may solve verified customer needs without building a duplicate.","target":"customers with validated business, creator, software, or service needs","question":"Which established products solve a current customer need and offer a verifiable partner or referral path?","queries":["customer need established SaaS tools official affiliate referral partner program","creator business productivity email commerce software partner program customer problem"],"source_class":"AFFILIATE_DISCOVERY","useful":"An official program page and product fit; payout claims remain unverified until official evidence.","priority":8,"customer_value":8,"revenue":9,"department_need":7,"expected_gain":8},
    {"family":"FUNDING_GRANTS","business_reason":"Find current funding or grant options that meet real business eligibility needs.","target":"small businesses and eligible community organizations","question":"Which current public grants or funding programs address a concrete small-business need?","queries":["2026 small business grants eligibility application deadline official program","small business funding programs underserved businesses current official eligibility"],"source_class":"FUNDING_GRANTS","useful":"Official program, eligibility, geography, amount, and deadline evidence; unknown terms stay unknown.","priority":8,"customer_value":8,"revenue":7,"department_need":8,"expected_gain":8},
    {"family":"SEO_MARKET_DEMAND","business_reason":"Identify customer language and search intent that can inform useful education or services.","target":"people seeking business, creator, and productivity guidance","question":"What current search questions reveal unmet demand for practical business or digital-service guidance?","queries":["small business automation setup cost practical questions search intent","creator business tools audience growth payment setup customer questions"],"source_class":"SEO_SEARCH_DEMAND","useful":"Observed related queries and corroborating current pages; search volume is not inferred.","priority":8,"customer_value":9,"revenue":7,"department_need":8,"expected_gain":8},
    {"family":"TECHNOLOGY_FOR_NEXUS","business_reason":"Assess technology only when it can materially improve a named Nexus capability.","target":"Nexus Research, Nova, Creative, Marketing, Systems, Labs, Trading, Funding, Credit, or Admin","question":"What recently available technology could measurably improve a specific Nexus workflow, cost, or reliability?","queries":["agent workflow reliability evaluation tool improves research evidence provenance open source","low latency speech synthesis streaming API tool practical integration latency cost"],"source_class":"GITHUB_TECHNOLOGY_DISCOVERY","useful":"A concrete Nexus use, verified capability, operational constraints, cost, and evaluation path.","priority":6,"customer_value":5,"revenue":5,"department_need":8,"expected_gain":7},
    {"family":"TRADING_INTELLIGENCE","business_reason":"Improve paper research with evidence on strategy failure modes or public indicator behavior.","target":"Trading research and paper/demo evaluation","question":"What public strategy or indicator evidence can improve a bounded paper test without enabling live trades?","queries":["TradingView public scripts strategy repainting risk management paper backtest evidence","TradingView public indicator scripts drawdown risk controls strategy validation"],"source_class":"TRADINGVIEW_PUBLIC_SCRIPTS","useful":"Public script or documentation with testable claims; no live execution or performance promises.","priority":6,"customer_value":4,"revenue":6,"department_need":8,"expected_gain":7},
    {"family":"VIRAL_COMMERCIAL_TRENDS","business_reason":"Detect customer-facing trends with commercial relevance and cross-platform evidence.","target":"customers and audiences relevant to Nexus offerings","question":"Which emerging commercial trend reflects a real customer need rather than attention alone?","queries":["recent small business customer trend rising demand product service complaints","creator or small business audience recurring questions new commercial demand trend"],"source_class":"VIRAL_SOCIAL_DISCOVERY","useful":"Dated audience/customer evidence, velocity if available, and a concrete commercial relevance check.","priority":5,"customer_value":7,"revenue":7,"department_need":5,"expected_gain":6},
    {"family":"COMPETITOR_GAPS","business_reason":"Find customer-visible gaps in alternatives serving a known Nexus audience.","target":"small-business owners comparing finance, credit, and operations services","question":"Where do existing alternatives fail customers or leave an important service gap?","queries":["small business software alternatives customer complaints missing features workflow","business funding service customer complaints competitor gap transparent eligibility"],"source_class":"WEB_SEARCH","useful":"Named alternatives, current customer evidence, and a specific underserved need.","priority":6,"customer_value":8,"revenue":8,"department_need":6,"expected_gain":7},
    {"family":"MERCH_MARKET_OPPORTUNITIES","business_reason":"Find themes with observable demand across communities and public campaigns.","target":"communities and audiences with recurring identity or cause-based themes","question":"Which recurring community themes show observable demand for useful merchandise or campaign products?","queries":["public merchandise campaigns recurring community themes product demand","Bonfire public campaigns community cause merchandise themes"],"source_class":"PUBLIC_CAMPAIGNS","useful":"Multiple dated demand signals; campaign presence is not sales evidence.","priority":5,"customer_value":7,"revenue":7,"department_need":5,"expected_gain":6},
    {"family":"AUTOMATION_OPPORTUNITIES","business_reason":"Find repeated customer work that can be safely reduced through automation.","target":"small businesses and Nexus operating teams","question":"Which repetitive customer or operating workflows remain costly despite available automation tools?","queries":["small business repeated manual workflow complaints automation needs","operations teams recurring administrative bottlenecks automation"],"source_class":"CUSTOMER_DISCUSSIONS","useful":"Firsthand repeated friction, current workaround, and tool or service alternatives.","priority":7,"customer_value":8,"revenue":8,"department_need":8,"expected_gain":8},
    {"family":"SERVICE_OPPORTUNITIES","business_reason":"Find service gaps customers already seek help to solve.","target":"small businesses seeking reliable implementation or specialist support","question":"What recurring customer needs are being addressed through paid services because self-serve options fall short?","queries":["small business owner asks for help service implementation recurring problem","small business services customer complaints support implementation"],"source_class":"CUSTOMER_DISCUSSIONS","useful":"Firsthand request for help, repeated need, and existing paid alternatives.","priority":6,"customer_value":8,"revenue":8,"department_need":6,"expected_gain":7},
    {"family":"PRODUCT_DEMAND","business_reason":"Identify products customers actively seek and the problems they expect them to solve.","target":"customers comparing products in relevant categories","question":"Which product needs recur in public customer discussions and product reviews, and what gaps remain?","queries":["product reviews recurring unresolved customer problems alternatives","customer asks for product recommendation recurring unmet need"],"source_class":"PRODUCT_REVIEWS","useful":"Repeated dated customer statements and review evidence; listing presence is not sales evidence.","priority":6,"customer_value":8,"revenue":8,"department_need":6,"expected_gain":7},
    {"family":"EMERGING_MARKET_CLUSTERS","business_reason":"Connect signals across customer, product, commerce, and search evidence before promoting a theme.","target":"audiences relevant to active Nexus priorities","question":"Which commercial theme is emerging across independent customer and product signals?","queries":["recent recurring customer need product demand multiple sources","emerging market theme customer complaints product alternatives"],"source_class":"MULTI_SOURCE_DISCOVERY","useful":"At least three independent sources spanning more than one source class.","priority":5,"customer_value":8,"revenue":8,"department_need":5,"expected_gain":8},
)

SOURCE_POLICY: dict[str, dict[str, Any]] = {
    "CUSTOMER_NEEDS": {"classes":["CUSTOMER_DISCUSSIONS","REVIEWS_AND_COMMUNITIES","WEB_SEARCH"],"strategy":"Prefer firsthand discussions/reviews, then search only to locate and corroborate evidence."},
    "CUSTOMER_COMPLAINTS": {"classes":["COMPLAINTS_AND_REVIEWS","CUSTOMER_DISCUSSIONS","WEB_SEARCH"],"strategy":"Prefer dated first-person complaints; cross-check against official alternatives."},
    "BUSINESS_OPPORTUNITIES": {"classes":["CUSTOMER_DISCUSSIONS","MARKETPLACE","WEB_SEARCH"],"strategy":"Establish the customer problem first, then inspect alternatives and commercial paths."},
    "AFFILIATE_OPPORTUNITIES": {"classes":["AFFILIATE_DIRECTORY","OFFICIAL_PARTNER_TERMS","CUSTOMER_NEEDS"],"strategy":"Discover through approved directories; verify economics only from official partner terms."},
    "FUNDING_GRANTS": {"classes":["OFFICIAL_GOVERNMENT","SBA","STATE_LOCAL_PROGRAMS"],"strategy":"Use official program sources for eligibility, amount and deadline evidence."},
    "SEO_MARKET_DEMAND": {"classes":["SEARCH_SUGGESTIONS","WEB_SEARCH","CUSTOMER_QUESTIONS"],"strategy":"Autocomplete describes query language; it does not establish search volume."},
    "TECHNOLOGY_FOR_NEXUS": {"classes":["GITHUB","OFFICIAL_DOCS","RELEASE_NOTES"],"strategy":"Use official code/docs and require a named Nexus workflow benefit."},
    "TRADING_INTELLIGENCE": {"classes":["TRADINGVIEW_PUBLIC_SCRIPTS","MARKET_DATA","NEXUS_BACKTEST"],"strategy":"Inspect public scripts, classify transparency, then independently recreate and test; never trust claimed returns."},
    "COMPETITOR_GAPS": {"classes":["CUSTOMER_DISCUSSIONS","PRODUCT_REVIEWS","OFFICIAL_PRODUCT_DOCS"],"strategy":"Use customer complaints or reviews to identify the gap, then verify current competitor capabilities from official product documentation."},
    "VIRAL_COMMERCIAL_TRENDS": {"classes":["DESIGNATED_YOUTUBE","PUBLIC_SOCIAL","SEARCH_DEMAND"],"strategy":"Use designated feeds or discovered public pages, then corroborate customer demand."},
    "MERCH_MARKET_OPPORTUNITIES": {"classes":["PUBLIC_CAMPAIGNS","MERCH_MARKETPLACES","COMMUNITY_SIGNALS"],"strategy":"Compare public campaign/product themes with independent community signals."},
    "AUTOMATION_OPPORTUNITIES": {"classes":["CUSTOMER_DISCUSSIONS","OFFICIAL_PRODUCT_DOCS","REVIEWS"],"strategy":"Start with firsthand workflow friction; inspect tools only as possible responses."},
    "SERVICE_OPPORTUNITIES": {"classes":["CUSTOMER_DISCUSSIONS","MARKETPLACE","WEB_SEARCH"],"strategy":"Look for repeated requests for help and verify current service alternatives."},
    "PRODUCT_DEMAND": {"classes":["PRODUCT_REVIEWS","CUSTOMER_DISCUSSIONS","MARKETPLACE"],"strategy":"Use customer/review evidence; distinguish visible listings from sales."},
    "EMERGING_MARKET_CLUSTERS": {"classes":["CUSTOMER_DISCUSSIONS","PRODUCT_MARKETPLACE","SEARCH_DEMAND","VIDEO_SOCIAL"],"strategy":"Require independent source diversity before clustering."},
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _history() -> list[dict[str, Any]]:
    try:
        lines = HISTORY.read_text(encoding="utf-8").splitlines()[-1000:]
    except OSError:
        return []
    rows = []
    for line in lines:
        try:
            row = json.loads(line)
            if isinstance(row, dict) and row.get("record_type") == "PROACTIVE_OBJECTIVE_RUN":
                rows.append(row)
        except ValueError:
            continue
    return rows


def _similarity(a: str, b: str) -> float:
    left, right = query_tokens(a), query_tokens(b)
    return len(left & right) / max(1, len(left | right))


def _score(family: dict[str, Any], history: list[dict[str, Any]], now: datetime) -> tuple[float, dict[str, float], bool]:
    recent = [r for r in history if r.get("objective_family") == family["family"]
              and (stamp := _stamp(r.get("last_run_at"))) and now - stamp <= timedelta(days=RECENT_DAYS)]
    latest = max(recent, key=lambda r: str(r.get("last_run_at")), default={})
    stamp = _stamp(latest.get("last_run_at"))
    age_hours = (now - stamp).total_seconds() / 3600 if stamp else 24 * RECENT_DAYS
    saturated = bool(latest and latest.get("saturation_state") == "SATURATED_RECENTLY"
                     and age_hours < SATURATION_HOURS and not latest.get("follow_up_created"))
    parts = {
        "CURRENT_COMPANY_PRIORITY": float(family["priority"]),
        "CUSTOMER_VALUE": float(family["customer_value"]),
        "REVENUE_POTENTIAL": float(family["revenue"]),
        "DEPARTMENT_NEED": float(family["department_need"]),
        "NOVELTY": 10.0 if not recent else max(0.0, 10.0 - 2.5 * len(recent)),
        "STALE_EVIDENCE_NEED": min(10.0, age_hours / 24),
        "SOURCE_FRESHNESS": 8.0,
        "LAST_RUN_RECENCY": min(10.0, age_hours / 24),
        "RECENT_SATURATION": -20.0 if saturated else -3.0 * len([r for r in recent[-3:] if int(r.get("qualified_findings", 0) or 0) == 0]),
        "EXPECTED_INFORMATION_GAIN": float(family["expected_gain"]),
    }
    return sum(parts.values()), parts, saturated


def choose_next_objective(*, history: list[dict[str, Any]] | None = None, at: datetime | None = None) -> dict[str, Any]:
    """Choose one eligible objective by customer/business value and novelty."""
    now = at or _now()
    rows = list(history if history is not None else _history())
    scored = []
    recent_family_counts: dict[str, int] = {}
    for prior_row in rows[-6:]:
        fam = str(prior_row.get("objective_family") or "")
        recent_family_counts[fam] = recent_family_counts.get(fam, 0) + 1
    for family in FAMILIES:
        score, components, saturated = _score(family, rows, now)
        repeated_family = recent_family_counts.get(family["family"], 0)
        if repeated_family:
            score -= 8.0 * repeated_family
            components["FAMILY_DIVERSITY"] = -8.0 * repeated_family
        variants_used = sum(1 for row in rows if row.get("objective_family") == family["family"])
        query = family["queries"][variants_used % len(family["queries"])]
        recent_similar = next((row for row in reversed(rows[-150:])
            if _stamp(row.get("last_run_at")) and now - _stamp(row.get("last_run_at")) <= timedelta(days=RECENT_DAYS)
            and row.get("source_class") == family["source_class"]
            and _similarity(query, str(row.get("query") or "")) >= .68
            and int(row.get("qualified_findings", 0) or 0) == 0), None)
        if recent_similar:
            saturated = True
            score -= 20.0
            components["RECENT_SATURATION"] = -20.0
        scored.append((saturated, -score, family, query, components, score, recent_similar))
    eligible = [row for row in scored if not row[0]] or scored
    saturated, _, family, query, components, score, prior = min(eligible, key=lambda row: (row[1], row[2]["family"]))
    latest = max((r for r in rows if r.get("objective_family") == family["family"]),
                 key=lambda r: str(r.get("last_run_at") or ""), default={})
    policy = SOURCE_POLICY[family["family"]]
    lane = ("TRADINGVIEW_PUBLIC_SCRIPTS" if family["family"] == "TRADING_INTELLIGENCE"
            else "AFFILIATE_PROGRAM_DISCOVERY" if family["family"] == "AFFILIATE_OPPORTUNITIES"
            else "FUNDING_GRANTS" if family["family"] == "FUNDING_GRANTS"
            else "SEO_SEARCH_DEMAND" if family["family"] == "SEO_MARKET_DEMAND"
            else "GITHUB_DISCOVERY" if family["family"] == "TECHNOLOGY_FOR_NEXUS"
            else "CUSTOMER_NEEDS_COMPLAINTS" if family["family"] in {"CUSTOMER_NEEDS","CUSTOMER_COMPLAINTS","AUTOMATION_OPPORTUNITIES","SERVICE_OPPORTUNITIES","PRODUCT_DEMAND"}
            else "WEB_SEARCH")
    return {
        "objective_family": family["family"], "business_reason": family["business_reason"],
        "target_customer_or_department": family["target"], "research_question": family["question"],
        "query_family": "qf_" + hashlib.sha256(" ".join(sorted(query_tokens(query))).encode()).hexdigest()[:20],
        "query": query, "source_class": family["source_class"], "what_would_make_this_useful": family["useful"],
        "score": round(score, 3), "score_components": components,
        "why_selected": f"Highest eligible customer/business score ({score:.2f}); customer value, revenue potential, department need, freshness, novelty, recency, saturation and expected information gain were included.",
        "prior_semantic_match": (prior or {}).get("query"),
        "objective_id": "proactive_" + family["family"].lower(),
        "lane": lane,
        "evidence_needed": family["useful"],
        "best_source_classes": policy["classes"],
        "why_these_sources": policy["strategy"],
        "last_run_at": latest.get("last_run_at"),
        "last_result": latest.get("last_result"),
        "saturation_state": "SATURATED_RECENTLY" if saturated else "ELIGIBLE",
    }


def record_objective_run(objective: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Append objective, query, evidence and saturation state to durable memory."""
    records = result.get("records") or []
    urls = sorted({str(row.get("url") or row.get("source_url")) for row in records if row.get("url") or row.get("source_url")})
    findings = int(result.get("evidence_supported_finding_count", 0) or 0)
    at = _now().isoformat()
    queries = result.get("queries") or [objective["query"]]
    executed_query = str(queries[0]) if queries else str(objective["query"])
    row = {
        "record_type":"PROACTIVE_OBJECTIVE_RUN", "objective_family":objective["objective_family"],
        "objective_id":objective["objective_id"], "business_reason":objective["business_reason"],
        "target_customer_or_department":objective["target_customer_or_department"],
        "research_question":objective["research_question"], "query_family":objective["query_family"],
        "evidence_needed":objective.get("evidence_needed"), "best_source_classes":objective.get("best_source_classes",[]),
        "why_these_sources":objective.get("why_these_sources"),
        "query":executed_query, "source_class":objective["source_class"],
        "objective_source_class":objective["source_class"],
        "source_classes_used":result.get("source_classes_used", []),
        "source_engines_used":sorted({str(r.get("source_engine") or r.get("source") or "") for r in records if r.get("source_engine") or r.get("source")}),
        "why_this_objective_was_selected":objective["why_selected"], "score_components":objective["score_components"],
        "last_run_at":at, "last_result":{"execution_status":(result.get("quality_assessment") or {}).get("execution_status",result.get("status")), "research_conclusion":(result.get("quality_assessment") or {}).get("research_conclusion", "RESEARCH_INCONCLUSIVE"), "next_research_action":(result.get("quality_assessment") or {}).get("next_research_action", "CHANGE_SOURCE_STRATEGY"), "raw_signals":int(result.get("results_found",len(records)) or 0),
        "new_signals":int(result.get("new_sources",0) or 0), "acquisition_cases":int(result.get("qualified_findings_created",0) or 0), "qualified_findings":findings,
        "handoffs":int(result.get("department_handoffs_created",0) or 0),"query_family":objective["query_family"]},
        "qualified_findings":findings, "follow_up_created":bool(result.get("follow_up_created")),
        "source_urls":urls,"result_ids":sorted({str(x) for x in (result.get("result_ids") or urls)}),
        "raw_signals":int(result.get("results_found", len(records)) or 0),
        "saturation_state":"SATURATED_RECENTLY" if findings == 0 and not result.get("follow_up_created") else "ACTIVE",
        "research_conclusion":(result.get("quality_assessment") or {}).get("research_conclusion", "RESEARCH_INCONCLUSIVE"),
        "next_research_action":(result.get("quality_assessment") or {}).get("next_research_action", "CHANGE_SOURCE_STRATEGY"),
        "quality_assessment":result.get("quality_assessment"),
        "raw_signal_ids":result.get("raw_signal_ids", []),
        "status":result.get("status"),"last_run_snapshot":objective,
    }
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
    persist_state({"memory_kind":"PROACTIVE_OBJECTIVE_RUN","objective_id":objective["objective_id"],
                   "query_family":objective["query_family"], **row})
    return row


def run_selected_proactive_objective() -> dict[str, Any]:
    """Use the production objective selector and existing bounded discovery lane."""
    objective = choose_next_objective()
    if "hacker news" in objective["query"].lower() or "hackernews" in objective["source_class"].lower():
        raise RuntimeError("PROACTIVE_HACKER_NEWS_DEFAULT_REGRESSION")
    from nexus_agent_platform.proactive_discovery import run_lane
    from nexus_agent_platform.research_tool_layer import plan_source_strategy
    source_strategy = plan_source_strategy(objective["research_question"], objective.get("evidence_needed"))
    if objective.get("best_source_classes"):
        source_strategy["source_classes_planned"] = list(objective["best_source_classes"])
    if objective.get("why_these_sources"):
        source_strategy["why_these_sources"] = list(objective["why_these_sources"])
    result = run_lane(objective["query"], objective["lane"],
                      bounds={"max_queries":1,"max_results_per_query":3,"max_new_sources":6,"max_runtime_per_lane":220},
                      use_lane_followup=False, objective_family=objective.get("objective_family"),
                      source_strategy=source_strategy, originating_goal_id=objective.get("originating_goal_id"))
    from nexus_agent_platform.research_quality import assess_run, persist_raw_signals
    quality = assess_run(objective, result)
    raw_signal_ids = persist_raw_signals(objective, result, quality)
    result["source_classes_planned"] = objective.get("best_source_classes", [])
    result["research_conclusion"] = result.get("research_conclusion") or quality.get("research_conclusion")
    result["next_research_action"] = result.get("next_research_action") or quality.get("next_research_action")
    result["quality_assessment"] = quality
    result["raw_signal_ids"] = raw_signal_ids
    row = record_objective_run(objective, result)
    return {**result,"objective":objective,"objective_run":row,
            "source_classes_used":row["source_classes_used"],"qualified_findings_created":row["qualified_findings"],
            "handoffs_created":row["last_result"]["handoffs"],"saturation_state":row["saturation_state"],
            "current_proactive_objective":objective["research_question"],
            "why_this_objective_was_selected":objective["why_selected"],
            "quality_assessment":quality,"raw_signal_ids":raw_signal_ids,
            "next_research_direction":"Rotate to another unsaturated customer/business objective family." if row["saturation_state"]=="SATURATED_RECENTLY" else "Continue the open evidence gap through the existing Research contract."}


def repetition_regression_guard(history: list[dict[str, Any]] | None = None, n: int = 4) -> bool:
    rows = list(history if history is not None else _history())[-max(n,2):]
    if len(rows) < n:
        return True
    if len({str(row.get("objective_family")) for row in rows}) == 1:
        return not all(int(row.get("qualified_findings",0) or 0)==0 for row in rows)
    for index,row in enumerate(rows):
        query=str(row.get("query") or "")
        if all(_similarity(query,str(other.get("query") or ""))>=.72
               and row.get("source_class")==other.get("source_class")
               and int(other.get("qualified_findings",0) or 0)==0
               for j,other in enumerate(rows) if j!=index):
            return False
    return True


def hacker_news_default_guard() -> bool:
    return all("hacker news" not in " ".join([str(f.get("query","")),str(f.get("source_class",""))]).lower()
               and "hackernews" not in str(f.get("source_class","")).lower() for f in FAMILIES)
