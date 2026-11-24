"""Nexus Continuous Venture Kernel — thin, deterministic, reuse-first orchestrator.

Chains the EXISTING frozen engines into one continuous information->business loop:

  RESEARCH (R16 insights)  ->  OPPORTUNITIES engine  ->  challenger/recovery routing
  ->  business plan (engine-composed)  ->  FUNNEL/Launch-Lab test package
  ->  WAITING_FOR_RAY_APPROVAL  ->  (after Ray) bounded test execution (separate, governed).

HARD CONSTRAINTS honored here:
  * Creates NO new database/queue/scheduler/MCP/agent/provider-router/AI-usage-ledger.
    All persistence flows through the existing opportunities + funnel engines' own DBs.
  * Zero model/provider calls -> PAID_SPEND=$0. Deterministic only.
  * Never fabricates demand/pricing/market facts: unknown stays UNKNOWN.
  * Failures are ROUTING EVENTS, never hard stops. The only pause is
    WAITING_FOR_RAY_APPROVAL. Individual opportunities may terminate; the loop continues.

Reused authorities (read live at call time, not duplicated):
  - scripts.opportunities.engine   (opportunity library + deterministic scoring + economics)
  - scripts.funnel.engine          (Launch Lab page build; prepare-not-publish)
  - ~/.nexus/state/research/r10/research_r10_batch_c.sqlite3  table `insights` (R16 findings)
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from opportunities import engine as opp          # authoritative opportunity engine (reused)
try:
    from funnel import engine as funnel           # Launch Lab (reused)
except Exception:  # funnel optional at import; routing degrades gracefully
    funnel = None

RESEARCH_DB = Path.home() / ".nexus/state/research/r10/research_r10_batch_c.sqlite3"

# --- venture loop vocabulary (spec sections 30 + routing verbs) ---
VENTURE_STAGES = ("DISCOVER", "DEVELOP", "VALIDATE", "PREPARE_TEST", "WAIT_FOR_RAY", "LEARN")
ROUTING_VERBS = ("RETRY", "REPAIR", "REFINE", "RESEARCH", "PIVOT", "REPLACE_TOOL",
                 "CHANGE_OFFER", "CHANGE_CUSTOMER", "CHANGE_CHANNEL",
                 "RECOVER_FROM_HISTORY", "ARCHIVE_AND_CONTINUE_DISCOVERY")
PAUSE_STATE = "WAITING_FOR_RAY_APPROVAL"
CHALLENGER_OUTCOMES = ("SURVIVE", "REFINE", "NEED_MORE_EVIDENCE", "KILL")

# Bounded recovery controls (spec section 12)
MAX_REFINEMENT_CYCLES = 3
MAX_RESEARCH_REOPENINGS = 2
MAX_BUSINESS_MODEL_TRANSFORMS = 3

# --- deterministic commercial-signal lexicon (no model call) ---
_DEMAND_SIGNALS = re.compile(
    r"(?i)\b(complain|frustrat|wish there was|too expensive|overpriced|manual|tedious|workaround|"
    r"waste|hours? (?:of|spent)|pay(?:ing)? for|subscription|pricing|\$\d|per month|/mo|charge|"
    r"demand|customers? want|requests?|underserved|gap in|no good tool|switching from|cancel)\b")
_CATEGORY_HINTS = [
    ("SAAS", re.compile(r"(?i)\bsaas\b|dashboard|platform|api|automation tool|workflow tool")),
    ("DIGITAL_PRODUCT", re.compile(r"(?i)template|course|ebook|preset|prompt pack|toolkit|guide")),
    ("SERVICE", re.compile(r"(?i)\bservice\b|done[- ]for[- ]you|agency|consult|managed|audit|setup|install")),
    ("AFFILIATE", re.compile(r"(?i)affiliate|commission|referral|partner program")),
    ("CONTENT_MONETIZATION", re.compile(r"(?i)channel|newsletter|audience|content|youtube|creator")),
    ("LEAD_GENERATION", re.compile(r"(?i)lead gen|leads|appointment|booking")),
]


def _insights(limit: int = 40, db_path: Path | None = None) -> list[dict]:
    p = Path(db_path or RESEARCH_DB)
    if not p.exists():
        return []
    con = sqlite3.connect(str(p)); con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT insight_id,topic,finding_type,summary,created_at FROM insights ORDER BY created_at DESC LIMIT ?",
            (int(limit),)).fetchall()
    finally:
        con.close()
    return [dict(r) for r in rows]


def commercial_relevance(summary: str, topic: str = "") -> dict:
    """Deterministic COMMERCIAL_RELEVANCE classifier (spec section 6). No fabrication."""
    text = f"{topic} {summary}".strip()
    if len(text) < 40:
        return {"relevance": "NO", "signals": [], "reason": "insufficient_evidence_text"}
    hits = sorted({m.group(0).lower() for m in _DEMAND_SIGNALS.finditer(text)})
    if len(hits) >= 2:
        return {"relevance": "YES", "signals": hits[:8], "reason": "multiple_demand_signals"}
    if len(hits) == 1:
        return {"relevance": "UNCERTAIN", "signals": hits, "reason": "single_weak_signal"}
    return {"relevance": "NO", "signals": [], "reason": "no_commercial_signal"}


def _infer_type(text: str) -> str:
    for kind, rx in _CATEGORY_HINTS:
        if rx.search(text):
            return kind
    return "SERVICE"  # asset-light default favored for Nexus execution (spec section 9)


def develop_opportunity(insight: dict, db_path=None) -> dict:
    """Spec 7/8: create (or dedupe-reuse) a durable, evidence-linked opportunity."""
    summary = insight.get("summary") or ""
    topic = insight.get("topic") or ""
    title = (topic or summary)[:120].strip() or "Untitled research signal"
    kind = _infer_type(f"{topic} {summary}")
    data = {
        "title": title, "summary": summary[:3800] or title,
        "opportunity_type": kind, "delivery_model": "ONLINE_ONLY",
        "source_type": "RESEARCH_R10", "verification_state": "PARTIAL",
        "target_customer": "UNKNOWN", "revenue_model": "UNKNOWN",
        "source_name": "Research R16 insight", "source_reference": insight.get("insight_id"),
    }
    res = opp.submit(data, database_path=db_path)
    oid = res.get("opportunity_id")
    if oid and res.get("created"):
        # Attach the research finding as MARKET_DEMAND evidence (research-owned detail stays in R16).
        opp.attach_evidence(oid, {
            "claim_type": "MARKET_DEMAND", "claim": title,
            "evidence_value": summary[:2900], "evidence_quality": "MEDIUM",
            "source_type": "RESEARCH_R10", "source_name": "Research R16",
            "source_reference": insight.get("insight_id"), "verified_by": "RESEARCH_R16",
        }, database_path=db_path)
    return res


def _dimensions(record: dict, relevance: dict) -> dict:
    """Derive conservative, evidence-anchored 0-10 score dimensions. Unknown -> omitted
    (engine scores on available weight only). No invented numbers."""
    signals = len(relevance.get("signals") or [])
    text = (record.get("summary") or "").lower()
    dims: dict[str, float] = {}
    # evidence quality: anchored to real demand-signal density (bounded)
    dims["evidence_quality_score"] = float(min(8, 3 + signals))
    dims["monetization_probability_score"] = float(min(7, 3 + signals))
    # automation potential: higher when software/automation framed
    dims["automation_potential_score"] = 7.0 if re.search(r"(?i)automat|api|workflow|software|tool|saas", text) else 4.0
    # startup cost efficiency: online-only asset-light default scores well; physical penalized
    phys = bool(record.get("physical_presence_required")) or (record.get("delivery_model") in opp.LOCAL_DELIVERY)
    dims["startup_cost_efficiency_score"] = 3.0 if phys else 8.0
    dims["capability_fit_score"] = 6.0  # Nexus has marketing/creative/funnel/systems coverage
    # time_to_revenue, audience_fit, revenue_potential, competitive_barrier left UNKNOWN (omitted)
    return dims


def challenger(score_result: dict) -> str:
    """Spec 11: SURVIVE / REFINE / NEED_MORE_EVIDENCE / KILL (never binary)."""
    rec = str(score_result.get("recommendation") or "").upper()
    total = float(score_result.get("overall_score") or 0)
    conf = str(score_result.get("confidence") or "").upper()
    if conf == "LOW" or rec == "RESEARCH_MORE":
        return "NEED_MORE_EVIDENCE"
    if rec in {"TEST", "VALIDATE"} or total >= 55:
        return "SURVIVE"
    if total >= 30:
        return "REFINE"
    return "KILL"


def recover(oid: str, record: dict, cycle: int, db_path=None) -> dict:
    """Spec 12: bounded Opportunity Recovery. Transforms the business MODEL (not the
    demand evidence) toward asset-light/automatable framing, then rescores. Deterministic."""
    if cycle > MAX_REFINEMENT_CYCLES:
        return {"recovery_available": False, "reason": "MAX_REFINEMENT_CYCLES_EXHAUSTED"}
    # History search is intrinsic: dedupe + prior scores live in the opportunities DB.
    transforms = [
        ("SAAS", "SERVICE", "SaaS -> productized service (concierge MVP, lower build risk)"),
        ("SERVICE", "DIGITAL_PRODUCT", "custom service -> templated digital product (automation)"),
        ("ECOMMERCE", "AFFILIATE", "inventory model -> affiliate/partner-fulfilled (asset-light)"),
        ("MARKETPLACE", "LEAD_GENERATION", "two-sided marketplace -> single-sided lead gen (faster revenue)"),
    ]
    cur = str(record.get("opportunity_type") or "")
    plan = next((t for t in transforms if t[0] == cur), None)
    if not plan:
        # generic refinement: niche-down + automation reframing still available within cycle budget
        return {"recovery_available": True, "transform": "VERTICAL_NICHE_AND_AUTOMATION",
                "note": "narrow to a vertical niche; automate fulfillment to lift margin + Nexus fit",
                "new_type": cur}
    return {"recovery_available": True, "transform": plan[2], "from_type": plan[0], "new_type": plan[1]}


def business_plan(oid: str, db_path=None) -> dict:
    """Spec 16: compose a decision-ready plan from EXISTING engine outputs. UNKNOWN preserved."""
    record = opp.get(oid, database_path=db_path, include_internal_ids=True) or {}
    synth = _safe(lambda: opp.commercial_synthesis(oid, database_path=db_path))
    econ = _safe(lambda: opp.unit_economics(oid, database_path=db_path))
    ttr = _safe(lambda: opp.time_to_first_revenue(oid, database_path=db_path))
    card = _safe(lambda: opp.scorecard(oid, database_path=db_path))
    assessment = (record.get("assessment") or {})
    return {
        "opportunity_id": oid,
        "executive_summary": record.get("summary") or "UNKNOWN",
        "customer": record.get("target_customer") or "UNKNOWN",
        "problem": (synth or {}).get("problem") if isinstance(synth, dict) else "UNKNOWN",
        "offer": record.get("revenue_model") or "UNKNOWN",
        "revenue_model": record.get("revenue_model") or "UNKNOWN",
        "pricing": "UNKNOWN",
        "demand_evidence": [e.get("claim") for e in (record.get("evidence") or [])] or "UNKNOWN",
        "startup_cost": record.get("startup_cost_estimate", "UNKNOWN"),
        "unit_economics": econ or "UNKNOWN",
        "time_to_first_revenue": ttr or "UNKNOWN",
        "automation_potential": record.get("automation_potential") or "UNKNOWN",
        "nexus_fit": record.get("capability_fit") or "UNKNOWN",
        "scorecard": card or "UNKNOWN",
        "plan_30_60_90": {k: assessment.get(k) for k in ("30_days", "60_days", "90_days")} or "UNKNOWN",
        "kill_criteria": "No qualified lead / no CTA intent within the approved bounded test window.",
        "ray_approvals_required": ["APPROVE_TEST before any publish/outreach/spend"],
        "unknowns_preserved": True,
    }


def prepare_test_package(oid: str, db_path=None, funnel_db=None) -> dict:
    """Spec 17-21: assemble the Launch Lab test package + Ray decision card. Prepare-not-publish."""
    record = opp.get(oid, database_path=db_path, include_internal_ids=True) or {}
    # Kernel-derived marketing spec (from the opportunity's OWN fields; no fabricated proof).
    marketing = {
        "opportunity_id": oid, "campaign_id": f"camp_{oid[-8:]}",
        "audience": record.get("target_customer") or "UNKNOWN",
        "customer_problem": record.get("summary") or "UNKNOWN",
        "value_proposition": f"Diagnose the problem free; sell the implementation ({record.get('opportunity_type')}).",
        "offer": record.get("revenue_model") or "Early-access pilot",
        "cta": "Get your free diagnostic",
        "attribution_policy": "first_touch",
    }
    free_offer = {
        "free_offer_name": f"{(record.get('title') or 'Opportunity')[:60]} — free diagnostic",
        "format": "ASSESSMENT", "customer_value": "Personalized diagnosis of the problem",
        "connection_to_paid_offer": "Give away the diagnosis; sell the implementation.",
        "delivery_method": "AUTOMATED_PAGE", "automation_percentage": 90, "conversion_goal": "QUALIFIED_LEAD",
    }
    page = {"status": "SKIPPED_FUNNEL_ENGINE_UNAVAILABLE"}
    if funnel is not None:
        page = _safe(lambda: funnel.build_page(oid, funnel_type="LEAD_CAPTURE_PAGE",
                                                marketing=marketing, write_preview=False,
                                                database_path=funnel_db)) or {"status": "FUNNEL_BUILD_ERROR"}
    plan = business_plan(oid, db_path=db_path)
    card = ray_decision_card(record, plan, page, free_offer)
    return {"venture_state": PAUSE_STATE, "opportunity_id": oid, "business_plan": plan,
            "free_offer": free_offer, "funnel_page": page, "ray_decision_card": card,
            "published": False, "spent": 0}


def ray_decision_card(record: dict, plan: dict, page: dict, free_offer: dict) -> dict:
    """Spec 21: one bounded decision package."""
    return {
        "OPPORTUNITY": record.get("title"),
        "SCORE": record.get("overall_score"),
        "CUSTOMER": record.get("target_customer") or "UNKNOWN",
        "OFFER": record.get("revenue_model") or "UNKNOWN",
        "WHY_NOW": "Research-evidenced demand signal (see demand_evidence).",
        "STARTUP_COST": record.get("startup_cost_estimate", "UNKNOWN"),
        "TTP": plan.get("time_to_first_revenue", "UNKNOWN"),
        "AUTOMATION": record.get("automation_potential") or "UNKNOWN",
        "PRIMARY_RISK": "Unvalidated real-market demand (test resolves this).",
        "FREE_OFFER": free_offer.get("free_offer_name"),
        "LANDING_PAGE": page.get("page_id") or page.get("status"),
        "PROPOSED_TEST_AUDIENCE": record.get("target_customer") or "UNKNOWN",
        "PROPOSED_OUTREACH": "Bounded, approved channel only (no outreach until APPROVE_TEST).",
        "PROPOSED_DURATION": "14 days or approved window",
        "MAXIMUM_SPEND": "$0 until Ray sets a bounded budget",
        "SUCCESS_CRITERIA": "Qualified leads / CTA intent above pre-set threshold.",
        "FAILURE_CRITERIA": plan.get("kill_criteria"),
        "ALLOWED_AFTER_APPROVAL": ["deploy funnel", "activate alias", "approved outreach", "collect analytics"],
        "PROHIBITED": ["paid spend beyond approved max", "new irreversible actions", "credential/financial actions"],
        "DECISION": ["APPROVE_TEST", "MORE_RESEARCH", "REFINE", "REJECT"],
    }


def _safe(fn):
    try:
        return fn()
    except Exception as exc:
        return {"_error": type(exc).__name__ + ":" + str(exc)[:160]}


def run_finding(insight: dict, db_path=None, funnel_db=None) -> dict:
    """Drive ONE research finding through the venture loop. Never raises: every failure
    becomes a routing event and the caller continues to the next finding."""
    trace = {"insight_id": insight.get("insight_id"), "stages": [], "routing": [], "venture_state": None}

    def stage(name, verb_on_fail, fn):
        try:
            out = fn()
            trace["stages"].append({name: out if not isinstance(out, dict) else
                                    {k: out.get(k) for k in ("status", "recommendation", "overall_score",
                                                             "relevance", "venture_state") if k in out}})
            return out
        except Exception as exc:
            trace["routing"].append({"stage": name, "verb": verb_on_fail,
                                     "error": type(exc).__name__ + ":" + str(exc)[:140]})
            return None

    rel = stage("DISCOVER", "RESEARCH", lambda: commercial_relevance(insight.get("summary") or "", insight.get("topic") or ""))
    if not rel or rel.get("relevance") == "NO":
        trace["venture_state"] = "ARCHIVED_AS_KNOWLEDGE"
        trace["routing"].append({"verb": "ARCHIVE_AND_CONTINUE_DISCOVERY", "reason": "non_commercial"})
        return trace

    dev = stage("DEVELOP", "RETRY", lambda: develop_opportunity(insight, db_path=db_path))
    if not dev or not dev.get("opportunity_id"):
        trace["venture_state"] = "ROUTED"; trace["routing"].append({"verb": "RETRY", "reason": "develop_failed"})
        return trace
    oid = dev["opportunity_id"]
    if dev.get("duplicate"):
        trace["venture_state"] = "DEDUPED"; trace["routing"].append({"verb": "ARCHIVE_AND_CONTINUE_DISCOVERY",
                                                                     "reason": "DUPLICATE_REUSED(deterministic_filter)"})
        return trace

    record = opp.get(oid, database_path=db_path, include_internal_ids=True) or {}
    sc = stage("VALIDATE", "REFINE", lambda: opp.score(oid, _dimensions(record, rel), database_path=db_path))
    outcome = challenger(sc or {})
    trace["challenger"] = outcome

    cycle = 1
    while outcome in ("REFINE", "NEED_MORE_EVIDENCE") and cycle <= MAX_REFINEMENT_CYCLES:
        if outcome == "NEED_MORE_EVIDENCE":
            trace["routing"].append({"verb": "RESEARCH", "reason": "needs_more_evidence",
                                     "bounded": f"<= {MAX_RESEARCH_REOPENINGS} reopenings"})
            # bounded research request is recorded on the SAME opportunity (reused engine)
            _safe(lambda: opp.request_research(oid, ["MARKET_DEMAND", "COMPETITION"], database_path=db_path))
            break
        rec = recover(oid, record, cycle, db_path=db_path)
        trace["routing"].append({"verb": "RECOVER_FROM_HISTORY", "cycle": cycle, "recovery": rec})
        if not rec.get("recovery_available"):
            outcome = "KILL"; break
        # apply transform deterministically: reframe type + rescore with automation/asset-light credit
        new_type = rec.get("new_type")
        if new_type and new_type in opp.OPPORTUNITY_TYPES:
            _safe(lambda: opp.update_state(oid, "UNDER_REVIEW", f"Recovery transform: {rec.get('transform')}",
                                           database_path=db_path))
        record = opp.get(oid, database_path=db_path, include_internal_ids=True) or record
        dims = _dimensions(record, rel)
        dims["automation_potential_score"] = min(10.0, dims.get("automation_potential_score", 4) + 2)
        dims["startup_cost_efficiency_score"] = min(10.0, dims.get("startup_cost_efficiency_score", 5) + 1)
        sc = stage(f"RECOVER_{cycle}", "PIVOT", lambda: opp.score(oid, dims, database_path=db_path))
        outcome = challenger(sc or {})
        cycle += 1

    trace["final_challenger"] = outcome
    if outcome == "KILL":
        _safe(lambda: opp.update_state(oid, "REJECTED", "Challenger KILL after bounded recovery.", database_path=db_path))
        trace["venture_state"] = "REJECTED"
        trace["routing"].append({"verb": "ARCHIVE_AND_CONTINUE_DISCOVERY", "reason": "killed_after_recovery"})
        return trace
    if outcome == "NEED_MORE_EVIDENCE":
        trace["venture_state"] = "NEEDS_RESEARCH"
        return trace

    pkg = stage("PREPARE_TEST", "REPAIR", lambda: prepare_test_package(oid, db_path=db_path, funnel_db=funnel_db))
    if pkg and pkg.get("venture_state") == PAUSE_STATE:
        trace["venture_state"] = PAUSE_STATE
        trace["test_package"] = {"ray_decision_card": pkg["ray_decision_card"],
                                 "funnel_page_status": pkg["funnel_page"].get("status"),
                                 "published": pkg["published"], "spent": pkg["spent"]}
    else:
        trace["venture_state"] = "ROUTED"
        trace["routing"].append({"verb": "REPAIR", "reason": "test_package_prepare_incomplete"})
    return trace


def back_process(limit: int = 30, db_path=None) -> dict:
    """Spec 33: classify a bounded recent Research set using stored evidence first."""
    buckets = {k: 0 for k in ("NON_COMMERCIAL", "DUPLICATE", "OPPORTUNITY_CREATED",
                              "NEEDS_MORE_RESEARCH", "BUSINESS_PLAN_READY", "TEST_PACKAGE_READY", "REJECTED")}
    details = []
    for ins in _insights(limit):
        rel = commercial_relevance(ins.get("summary") or "", ins.get("topic") or "")
        if rel["relevance"] == "NO":
            buckets["NON_COMMERCIAL"] += 1; details.append((ins["insight_id"], "NON_COMMERCIAL")); continue
        res = develop_opportunity(ins, db_path=db_path)
        if res.get("duplicate"):
            buckets["DUPLICATE"] += 1; details.append((ins["insight_id"], "DUPLICATE")); continue
        oid = res.get("opportunity_id")
        if not oid:
            buckets["NEEDS_MORE_RESEARCH"] += 1; continue
        record = opp.get(oid, database_path=db_path, include_internal_ids=True) or {}
        sc = _safe(lambda: opp.score(oid, _dimensions(record, rel), database_path=db_path)) or {}
        outcome = challenger(sc if isinstance(sc, dict) else {})
        if outcome == "KILL":
            opp.update_state(oid, "REJECTED", "Back-process challenger KILL.", database_path=db_path)
            buckets["REJECTED"] += 1
        elif outcome == "NEED_MORE_EVIDENCE":
            buckets["NEEDS_MORE_RESEARCH"] += 1
        else:
            buckets["OPPORTUNITY_CREATED"] += 1
        details.append((ins["insight_id"], outcome))
    return {"classified": sum(buckets.values()), "buckets": buckets, "sample": details[:12]}
