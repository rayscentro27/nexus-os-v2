"""Nexus Marketing Engine: durable acquisition-system authority.

Mission: MONETIZE_NEXUS. Marketing is Nexus's outside-world commercial
connection and its ongoing market-feedback sensor. It consumes the certified
Business Opportunities -> Marketing handoff (``opportunities_marketing_handoff``)
and turns a completed Monetization Opportunity Package into a live, measurable
acquisition system plus a Nova-readable next-commercial-decision recommendation.

Boundaries (both upstream departments are FROZEN_CERTIFIED):
  * Business Opportunities owns the commercial case: unit economics, scoring,
    market/competitor/regulatory research, and monetization-model selection.
    Marketing READS the handoff and never recomputes any of it.
  * Creative creates assets. Marketing only produces a stable Creative request
    contract (CREATIVE CREATES; MARKETING DEPLOYS, MEASURES, AND OPTIMIZES).

Data policy: LOCAL_SQLITE_IS_AUTHORITATIVE=YES, SUPABASE_IS_COORDINATION_LAYER=YES,
SUPABASE_IS_RAW_DATA_WAREHOUSE=NO. Full engine state, raw evidence, intermediate
work and large content stay local; only condensed cross-engine summaries are
coordination-eligible. If Supabase and SQLite disagree, local SQLite wins.

Approval policy: SOLUTION_FIRST / RAY_DECIDES. Marketing autonomously researches,
plans, drafts, scores, prepares campaigns/funnels/Creative requests/approval
cards, and measures already-authorized activity. It never converts planning
permission into spending permission: paid spend, paid APIs, commercial-account
activation, governed publishing, credential changes, and approval-gated
production actions require explicit Ray approval and are emitted as approval
cards, not executed here.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA_VERSION = 1
ENGINE_VERSION = "nexus-marketing-engine-v1"
DB_PATH = Path.home() / ".nexus/state/marketing/marketing.sqlite3"

UNKNOWN = "UNKNOWN"

CAMPAIGN_STATUSES = {
    "INTAKE", "PLANNED", "AWAITING_APPROVAL", "ORGANIC_LIVE", "PAID_TEST_LIVE",
    "MEASURING", "OPTIMIZING", "HOLD", "STOPPED", "COMPLETED", "ARCHIVED",
}
NEXT_ACTIONS = {"SCALE", "CONTINUE", "MODIFY", "HOLD", "STOP"}
RETENTION_CLASSES = {"EVENT_DETAIL", "CAMPAIGN_WORKING", "LONG_TERM_KNOWLEDGE", "LEGAL_HOLD"}
COMPANY_PURPOSES = {
    "MONETIZE_NEXUS", "SAVE_NEXUS_MONEY", "IMPROVE_NEXUS",
    "MAINTAIN_NEXUS", "PROTECT_NEXUS_FROM_UNNECESSARY_EXPOSURE",
}

# Deterministic recommendation thresholds (policy constants, not opportunity data).
_ROAS_SCALE = 2.0
_ROAS_CONTINUE = 1.0

SCHEMA = """
CREATE TABLE IF NOT EXISTS marketing_campaigns (
 campaign_id TEXT PRIMARY KEY,
 opportunity_id TEXT NOT NULL,
 title TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN (
  'INTAKE','PLANNED','AWAITING_APPROVAL','ORGANIC_LIVE','PAID_TEST_LIVE',
  'MEASURING','OPTIMIZING','HOLD','STOPPED','COMPLETED','ARCHIVED')),
 company_purpose TEXT NOT NULL DEFAULT 'MONETIZE_NEXUS',
 audience TEXT, customer_problem TEXT, positioning TEXT, offer TEXT, value_proposition TEXT,
 primary_channel TEXT, alternative_channels_json TEXT,
 funnel_type TEXT, funnel_json TEXT,
 landing_page_objective TEXT, landing_page_requirements_json TEXT, cta TEXT,
 organic_strategy_json TEXT, paid_test_json TEXT,
 approval_required INTEGER NOT NULL DEFAULT 0, approval_state TEXT,
 attribution_plan_json TEXT, measurement_plan_json TEXT, creative_request_json TEXT,
 forecast_json TEXT, handoff_snapshot_json TEXT, missing_inputs_json TEXT,
 expected_test_cost TEXT,
 recommended_next_action TEXT, recommendation_reason TEXT,
 retention_class TEXT NOT NULL DEFAULT 'CAMPAIGN_WORKING',
 retain_until TEXT, legal_hold INTEGER NOT NULL DEFAULT 0,
 promoted_to_long_term INTEGER NOT NULL DEFAULT 0, deletion_eligible INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(opportunity_id)
);
CREATE TABLE IF NOT EXISTS marketing_connections (
 connection_id TEXT PRIMARY KEY,
 platform TEXT NOT NULL, capability TEXT,
 read_available INTEGER, write_available INTEGER, publish_available INTEGER, analytics_available INTEGER,
 auth_state TEXT, approval_required INTEGER, cost TEXT,
 business_purpose TEXT, status TEXT, last_verified TEXT, notes TEXT,
 UNIQUE(platform, capability)
);
CREATE TABLE IF NOT EXISTS marketing_performance (
 perf_id TEXT PRIMARY KEY,
 campaign_id TEXT NOT NULL REFERENCES marketing_campaigns(campaign_id) ON DELETE CASCADE,
 opportunity_id TEXT NOT NULL,
 window TEXT NOT NULL,
 impressions REAL, reach REAL, clicks REAL, ctr REAL,
 landing_page_visits REAL, cta_clicks REAL, affiliate_clicks REAL,
 leads REAL, conversions REAL, conversion_rate REAL,
 cpc REAL, cpl REAL, cac REAL,
 ad_spend REAL, content_cost REAL, commissions REAL,
 gross_revenue REAL, net_revenue REAL, roas REAL,
 attribution_json TEXT, source TEXT, notes TEXT,
 retention_class TEXT NOT NULL DEFAULT 'EVENT_DETAIL', retain_until TEXT,
 recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_marketing_perf_campaign ON marketing_performance(campaign_id, recorded_at);
CREATE TABLE IF NOT EXISTS marketing_intelligence (
 intel_id TEXT PRIMARY KEY,
 opportunity_id TEXT, campaign_id TEXT,
 intel_type TEXT NOT NULL, observation TEXT, structured_json TEXT, source TEXT,
 retention_class TEXT NOT NULL DEFAULT 'EVENT_DETAIL', retain_until TEXT,
 promoted_to_long_term INTEGER NOT NULL DEFAULT 0, deletion_eligible INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_marketing_intel_owner ON marketing_intelligence(opportunity_id, intel_type);
CREATE TABLE IF NOT EXISTS marketing_history (
 event_id TEXT PRIMARY KEY,
 campaign_id TEXT, opportunity_id TEXT,
 event_type TEXT NOT NULL, previous_state TEXT, new_state TEXT,
 actor TEXT, reason TEXT, metadata_json TEXT, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_marketing_history_owner ON marketing_history(campaign_id, created_at);
"""

# Honest Layer-1 connection registry. Seeded once; every row names the revenue or
# market-intelligence workflow it enables. Defaults are conservative: nothing is
# claimed active or authenticated until verified. Paid/publish rows are approval-gated.
_CONNECTION_SEED = [
    # (platform, capability, read, write, publish, analytics, auth_state, approval_required, cost, business_purpose, status, notes)
    ("WEBSITE", "LANDING_PAGE_PUBLISH", 1, 1, 0, 1, "NOT_CONNECTED", 1, "LOW",
     "Host offer/landing pages that convert acquired attention into leads/sales.", "INACTIVE",
     "Publishing is approval-gated; generation/spec is autonomous."),
    ("SEO_SEARCH_CONSOLE", "ORGANIC_SEARCH", 1, 0, 0, 1, "NOT_CONNECTED", 0, "NONE",
     "Capture existing search demand (buyer guides, comparisons) at zero media cost.", "INACTIVE",
     "Read-only analytics when connected; organic-first primary channel."),
    ("YOUTUBE", "VIDEO_ORGANIC", 1, 1, 0, 1, "NOT_CONNECTED", 1, "NONE",
     "Organic video demand capture and review/compare content.", "INACTIVE", "Publishing approval-gated."),
    ("TIKTOK", "SHORT_VIDEO_ORGANIC", 1, 1, 0, 1, "NOT_CONNECTED", 1, "NONE",
     "Capture creator-driven / viral product demand legitimately.", "INACTIVE", "Publishing approval-gated."),
    ("INSTAGRAM", "SOCIAL_ORGANIC", 1, 1, 0, 1, "NOT_CONNECTED", 1, "NONE",
     "Organic social demand capture for consumer/beauty/electronics launches.", "INACTIVE", "Publishing approval-gated."),
    ("FACEBOOK", "SOCIAL_ORGANIC", 1, 1, 0, 1, "NOT_CONNECTED", 1, "NONE",
     "Organic social reach and community-driven acquisition.", "INACTIVE", "Publishing approval-gated."),
    ("LINKEDIN", "B2B_ORGANIC", 1, 1, 0, 1, "NOT_CONNECTED", 1, "NONE",
     "B2B/service acquisition and authority content.", "INACTIVE", "Publishing approval-gated."),
    ("PINTEREST", "VISUAL_DISCOVERY", 1, 1, 0, 1, "NOT_CONNECTED", 1, "NONE",
     "Evergreen visual discovery for product/buyer-intent content.", "INACTIVE", "Publishing approval-gated."),
    ("X", "SOCIAL_ORGANIC", 1, 1, 0, 1, "NOT_CONNECTED", 1, "NONE",
     "Real-time demand capture around launches and trends.", "INACTIVE", "Optional; publishing approval-gated."),
    ("NEWSLETTER_BEEHIIV", "EMAIL_ORGANIC", 1, 1, 0, 1, "NOT_CONNECTED", 1, "LOW",
     "Owned-audience nurture and repeat monetization.", "INACTIVE", "Sending approval-gated."),
    ("EMAIL_LEAD_CAPTURE", "LEAD_CAPTURE", 1, 1, 0, 1, "NOT_CONNECTED", 0, "LOW",
     "Capture leads from funnels for routing and attribution.", "INACTIVE", "Capture/routing is autonomous; sending is gated."),
    ("GOOGLE_ADS", "PAID_SEARCH", 1, 1, 1, 1, "NOT_CONNECTED", 1, "VARIABLE",
     "Bounded paid search test only after organic proves interest.", "INACTIVE", "Spend requires explicit Ray approval."),
    ("META_ADS", "PAID_SOCIAL", 1, 1, 1, 1, "NOT_CONNECTED", 1, "VARIABLE",
     "Bounded paid social test only after organic proves interest.", "INACTIVE", "Spend requires explicit Ray approval."),
    ("TIKTOK_ADS", "PAID_SOCIAL", 1, 1, 1, 1, "NOT_CONNECTED", 1, "VARIABLE",
     "Bounded paid short-video test only after organic proves interest.", "INACTIVE", "Spend requires explicit Ray approval."),
    ("AFFILIATE_OPENAFFILIATE", "AFFILIATE_DISCOVERY", 1, 0, 0, 1, "READ_ONLY_PUBLIC", 1, "NONE",
     "Legitimate affiliate/referral monetization of existing demand (discovery via existing opportunities adapter).",
     "PARTIAL", "Discovery read-only exists; account activation is approval-gated."),
    ("RETAILER_AFFILIATE", "RETAILER_AFFILIATE", 1, 0, 0, 1, "NOT_CONNECTED", 1, "NONE",
     "Monetize brand-funded demand via retailer affiliate links/buyer guides.", "INACTIVE",
     "Account activation approval-gated; no fabricated affiliation."),
    ("ANALYTICS_UTM", "ATTRIBUTION", 1, 1, 0, 1, "AVAILABLE", 0, "NONE",
     "Trace campaign->opportunity revenue via UTM/sub-ID/campaign IDs where platforms support it.", "ACTIVE",
     "Attribution planning is autonomous and uses only platform-supported mechanisms."),
    ("NOVA_TELEGRAM", "EXECUTIVE_INTERFACE", 1, 0, 0, 0, "CONNECTED", 0, "NONE",
     "Deliver Nova-readable Marketing status and next-action recommendations to Ray.", "ACTIVE",
     "Existing Nexus route; Marketing logic stays in Marketing, not Nova."),
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _clean_text(value: Any, limit: int = 2000) -> str:
    return " ".join(str(value or "").split())[:limit]


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _db_path(path: str | Path | None) -> Path:
    return Path(path).expanduser() if path is not None else DB_PATH


@contextmanager
def _connect(path: str | Path | None = None, *, readonly: bool = False) -> Iterator[sqlite3.Connection]:
    db_path = _db_path(path)
    if readonly:
        con = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True, timeout=4)
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(db_path.parent, 0o700)
        except OSError:
            pass
        con = sqlite3.connect(db_path, timeout=8)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=FULL")
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=8000")
    try:
        yield con
        if not readonly:
            con.commit()
    except BaseException:
        if not readonly:
            con.rollback()
        raise
    finally:
        con.close()


def initialize(path: str | Path | None = None) -> dict[str, Any]:
    db_path = _db_path(path)
    with _connect(db_path) as con:
        version = int(con.execute("PRAGMA user_version").fetchone()[0])
        if version > SCHEMA_VERSION:
            raise RuntimeError("MARKETING_SCHEMA_NEWER_THAN_RUNTIME")
        con.executescript(SCHEMA)
        con.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        if int(con.execute("SELECT count(*) FROM marketing_connections").fetchone()[0]) == 0:
            for row in _CONNECTION_SEED:
                platform, capability, r, w, pub, an, auth, appr, cost, purpose, status, notes = row
                con.execute(
                    """INSERT OR IGNORE INTO marketing_connections
                    (connection_id,platform,capability,read_available,write_available,publish_available,
                     analytics_available,auth_state,approval_required,cost,business_purpose,status,last_verified,notes)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (_uid("conn"), platform, capability, r, w, pub, an, auth, appr, cost, purpose, status, None, notes),
                )
    try:
        os.chmod(db_path, 0o600)
    except OSError:
        pass
    return {"status": "READY", "schema_version": SCHEMA_VERSION, "database_path": str(db_path)}


def _public(value: Any, *, include_internal_ids: bool = False) -> Any:
    hidden = {"opportunity_id", "campaign_id", "perf_id", "intel_id", "event_id", "connection_id"}
    if isinstance(value, dict):
        return {k: _public(v, include_internal_ids=include_internal_ids)
                for k, v in value.items() if include_internal_ids or k.casefold() not in hidden}
    if isinstance(value, list):
        return [_public(v, include_internal_ids=include_internal_ids) for v in value]
    if isinstance(value, str) and not include_internal_ids:
        value = re.sub(r"\b(?:camp|perf|intel|evt|conn|opp)_[a-f0-9]{32}\b", "[internal reference]", value)
    return value


def _history(con: sqlite3.Connection, campaign_id: str | None, opportunity_id: str | None,
             event_type: str, *, previous: str = "", new: str = "", reason: str = "",
             metadata: dict | None = None, actor: str = "marketing") -> None:
    con.execute(
        """INSERT INTO marketing_history
        (event_id,campaign_id,opportunity_id,event_type,previous_state,new_state,actor,reason,metadata_json,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (_uid("evt"), campaign_id, opportunity_id, event_type, previous or None, new or None,
         actor, _clean_text(reason, 500) or None, _json(metadata or {}), now()),
    )


# --------------------------------------------------------------------------
# Handoff consumption + plan derivation (Layer 2: funnel / distribution).
# Marketing READS the certified handoff; it never recomputes the commercial case.
# --------------------------------------------------------------------------

def _pull_handoff(opportunity_id: str) -> dict[str, Any]:
    """Consume the certified Business Opportunities -> Marketing handoff."""
    from scripts.opportunities import engine as bo_engine
    return bo_engine.marketing_handoff(opportunity_id, include_internal_ids=True)


def _channels_from_handoff(handoff: dict) -> tuple[str, list[str], list[str]]:
    """Derive organic-first channel selection without redoing BO's work.

    Uses handoff-provided channels when present; otherwise a conservative
    organic default set, with the assumption explicitly labeled.
    """
    provided = [str(c) for c in (handoff.get("PRIMARY_CHANNEL_OPPORTUNITIES") or []) if c]
    model = str(handoff.get("RECOMMENDED_MONETIZATION_MODEL") or "").upper()
    assumptions: list[str] = []
    if provided:
        primary, alternates = provided[0], provided[1:]
    else:
        if "AFFILIATE" in model or "REFERRAL" in model:
            ordered = ["SEO_SEARCH_CONSOLE", "YOUTUBE", "EMAIL_LEAD_CAPTURE", "PINTEREST"]
        else:
            ordered = ["SEO_SEARCH_CONSOLE", "LINKEDIN", "EMAIL_LEAD_CAPTURE", "FACEBOOK"]
        primary, alternates = ordered[0], ordered[1:]
        assumptions.append("CHANNELS assumed organic-first default; no handoff channel evidence provided [ASSUMED].")
    return primary, alternates, assumptions


def _build_plan(handoff: dict) -> dict[str, Any]:
    """Pure derivation of the Marketing-owned acquisition plan from the handoff."""
    title = str(handoff.get("WHAT_WE_ARE_MONETIZING") or UNKNOWN)
    audience = str(handoff.get("TARGET_CUSTOMER") or UNKNOWN)
    customer_problem = str(handoff.get("CUSTOMER_NEED") or UNKNOWN)
    value_prop = str(handoff.get("VALUE_PROPOSITION") or UNKNOWN)
    offer = str(handoff.get("RECOMMENDED_MONETIZATION_MODEL") or UNKNOWN)
    price = handoff.get("PRODUCT_SERVICE_PRICE", UNKNOWN)

    primary, alternates, channel_assumptions = _channels_from_handoff(handoff)

    positioning = (f"Position '{title}' to {audience} around the need: {customer_problem}."
                   if audience != UNKNOWN else f"Positioning pending audience evidence for '{title}'.")

    funnel = {
        "STAGES": ["ATTENTION", "INTEREST", "LANDING_PAGE_VISIT", "CTA_CLICK", "LEAD_OR_SALE"],
        "FUNNEL_TYPE": "ORGANIC_LEAD_OR_DIRECT_OFFER",
        "TOP_OF_FUNNEL": f"Organic {primary} content capturing existing demand.",
        "MIDDLE": "Landing page communicating offer + proof.",
        "BOTTOM": "Single primary CTA to lead capture or supported affiliate/sale link.",
    }
    landing_requirements = {
        "OBJECTIVE": "Convert a qualified visitor into one tracked lead or sale.",
        "REQUIRED_SECTIONS": ["Headline matching channel hook", "Problem/value proposition", "Offer + price",
                              "Proof/compliance note", "Single primary CTA", "Attribution + tracking"],
        "COMPLIANCE": ["Honest claims only", "Required disclosures", "No fabricated affiliation/endorsement"],
        "GENERATION": "Requirements only; actual page generation is a later gated Creative/deployment step.",
    }
    cta = "Request/Buy via the single tracked primary CTA."

    organic_strategy = {
        "POLICY": "ORGANIC_FIRST -> PROVE_INTEREST -> SMALL_PAID_TEST_IF_JUSTIFIED -> SCALE_ONLY_WITH_EVIDENCE",
        "PRIMARY_CHANNEL": primary,
        "ALTERNATIVE_CHANNELS": alternates,
        "APPROACH": "Publish supported organic content + SEO/comparison/buyer-guide assets to capture existing attention.",
        "CASH_REQUIRED": 0,
        "APPROVAL_REQUIRED": True,
        "APPROVAL_NOTE": "Organic content *generation* is autonomous; public *publishing/scheduling* is Ray-gated.",
    }

    lct = handoff.get("LOW_CAPITAL_TEST") or {}
    paid_limit = handoff.get("PAID_TEST_LIMIT", UNKNOWN)
    paid_test = {
        "OBJECTIVE": "Validate paid acquisition only after organic proves interest.",
        "MAXIMUM_SPEND": paid_limit,
        "DURATION": lct.get("TEST_DURATION", "14-30 days [ASSUMED]") if isinstance(lct, dict) else UNKNOWN,
        "AUDIENCE": audience,
        "CHANNEL": primary if primary in {"GOOGLE_ADS", "META_ADS", "TIKTOK_ADS"} else "GOOGLE_ADS_or_META_ADS (bounded)",
        "TRAFFIC_TARGET": lct.get("TRAFFIC_TARGET", UNKNOWN) if isinstance(lct, dict) else UNKNOWN,
        "LEAD_TARGET": UNKNOWN,
        "CONVERSION_TARGET": lct.get("CONVERSION_TARGET", UNKNOWN) if isinstance(lct, dict) else UNKNOWN,
        "SUCCESS_METRIC": "Positive or breakeven ROAS at or below MAXIMUM_SPEND",
        "FAILURE_METRIC": "Spend reaches MAXIMUM_SPEND with no qualified conversions",
        "STOP_CONDITION": "Reach MAXIMUM_SPEND or DURATION without meeting SUCCESS_METRIC",
        "APPROVAL_REQUIRED": True,
        "APPROVAL_NOTE": "Any paid spend requires explicit Ray approval before activation.",
    }

    attribution_plan = {
        "KEYS": ["OPPORTUNITY_ID", "CAMPAIGN_ID", "CHANNEL", "CONTENT_ID", "CREATIVE_ID",
                 "LANDING_PAGE_ID", "OFFER_ID_OR_AFFILIATE_ID"],
        "MECHANISMS": ["UTM parameters", "affiliate sub-IDs", "platform campaign IDs",
                       "conversion callbacks", "analytics APIs", "commission reports", "CRM lead IDs"],
        "UTM_TEMPLATE": "utm_source={channel}&utm_medium={organic|paid}&utm_campaign={campaign_id}&utm_content={content_id}",
        "RULE": "Use only platform-supported attribution; do not invent attribution a platform does not provide.",
    }

    forecast = {
        "EXPECTED_30_DAY_REVENUE": (handoff.get("30_DAY_REVENUE_SCENARIO") or {}).get("REVENUE_RANGE", UNKNOWN),
        "EXPECTED_60_DAY_REVENUE": (handoff.get("60_DAY_REVENUE_SCENARIO") or {}).get("REVENUE_RANGE", UNKNOWN),
        "EXPECTED_90_DAY_REVENUE": (handoff.get("90_DAY_REVENUE_SCENARIO") or {}).get("REVENUE_RANGE", UNKNOWN),
        "EXPECTED_TIME_TO_FIRST_REVENUE": (handoff.get("ESTIMATED_TIME_TO_FIRST_REVENUE") or {}).get("ESTIMATED_RANGE_DAYS", UNKNOWN),
        "EXPECTED_TEST_COST": paid_limit,
        "SOURCE": "Business Opportunities handoff (authoritative; not recomputed by Marketing).",
    }

    measurement_plan = {
        "TRACKED_METRICS": ["IMPRESSIONS", "REACH", "CLICKS", "CTR", "LANDING_PAGE_VISITS", "CTA_CLICKS",
                            "AFFILIATE_CLICKS", "LEADS", "CONVERSIONS", "CONVERSION_RATE", "CPC", "CPL",
                            "CAC", "AD_SPEND", "COMMISSIONS", "REVENUE", "NET_REVENUE", "ROAS"],
        "FORECAST_VS_ACTUAL_WINDOWS": ["30_DAY", "60_DAY", "90_DAY"],
        "DEFINITION_OF_DONE": "Acquisition system is LIVE, MEASURABLE, and producing enough data for the next "
                              "commercial decision (SCALE/CONTINUE/MODIFY/HOLD/STOP).",
        "NOTE": "Only metrics the connected platform supports are recorded; unsupported stay UNKNOWN.",
    }

    creative_request = _build_creative_request(handoff, title, audience, customer_problem,
                                               value_prop, offer, primary, positioning, cta)

    missing = list(handoff.get("MISSING_INPUTS") or [])
    approval_required = True  # publishing + any paid activity are gated; organic generation is autonomous.

    return {
        "title": title, "audience": audience, "customer_problem": customer_problem,
        "positioning": positioning, "offer": offer, "value_proposition": value_prop,
        "price": price, "primary_channel": primary, "alternative_channels": alternates,
        "funnel_type": funnel["FUNNEL_TYPE"], "funnel": funnel,
        "landing_page_objective": landing_requirements["OBJECTIVE"],
        "landing_page_requirements": landing_requirements, "cta": cta,
        "organic_strategy": organic_strategy, "paid_test": paid_test,
        "attribution_plan": attribution_plan, "measurement_plan": measurement_plan,
        "creative_request": creative_request, "forecast": forecast,
        "missing_inputs": missing, "expected_test_cost": paid_limit,
        "approval_required": approval_required,
        "channel_assumptions": channel_assumptions,
        "commercial_recommendation": handoff.get("COMMERCIAL_RECOMMENDATION", "RESEARCH_MORE"),
        "primary_risks": handoff.get("PRIMARY_RISKS", []),
        "external_boundaries": handoff.get("EXTERNAL_BOUNDARIES", []),
    }


def _build_creative_request(handoff, title, audience, customer_problem, value_prop, offer,
                            channel, positioning, cta) -> dict[str, Any]:
    """Marketing -> Creative contract. CREATIVE CREATES; MARKETING DEPLOYS/MEASURES/OPTIMIZES."""
    return {
        "AUDIENCE": audience,
        "CUSTOMER_PROBLEM": customer_problem,
        "EMOTIONAL_DRIVER": UNKNOWN if customer_problem == UNKNOWN else f"Relief from: {customer_problem}",
        "POSITIONING": positioning,
        "OFFER": offer,
        "CHANNEL": channel,
        "CONTENT_FORMAT": "Channel-native short content + landing page copy",
        "HOOK": UNKNOWN if customer_problem == UNKNOWN else f"Lead with the cost of unsolved: {customer_problem}",
        "MESSAGE": value_prop,
        "CTA": cta,
        "ASSET_REQUIREMENTS": list(handoff.get("CREATIVE_REQUIREMENTS") or ["TBD by Creative engine"]),
        "LANDING_PAGE_REQUIREMENTS": "See campaign landing_page_requirements.",
        "CAMPAIGN_OBJECTIVE": f"Acquire tracked leads/sales for '{title}' via {channel}.",
        "SUCCESS_METRIC": "Qualified conversions at or above the break-even signal.",
        "HARD_RULE": "CREATIVE CREATES. MARKETING DEPLOYS, MEASURES, AND OPTIMIZES.",
        "MARKETING_REQUIREMENTS_FROM_HANDOFF": list(handoff.get("MARKETING_REQUIREMENTS") or []),
    }


def intake(opportunity_id: str, *, handoff: dict | None = None,
           database_path: str | Path | None = None) -> dict[str, Any]:
    """Consume the certified handoff and create/refresh the Marketing campaign plan.

    Autonomous planning only (bounded internal write; no external effect, no spend,
    no publishing). Idempotent per opportunity: re-intake refreshes the plan on the
    same campaign record.
    """
    initialize(database_path)
    if handoff is None:
        handoff = _pull_handoff(opportunity_id)
    if not isinstance(handoff, dict) or not handoff:
        return {"status": "REJECTED", "reason": "EMPTY_OR_INVALID_HANDOFF"}
    oid = str(handoff.get("OPPORTUNITY_ID") or opportunity_id or "").strip()
    if not oid:
        return {"status": "REJECTED", "reason": "OPPORTUNITY_ID_REQUIRED"}

    plan = _build_plan(handoff)
    rec, reason = _recommend(plan, [])
    timestamp = now()
    with _connect(database_path) as con:
        existing = con.execute("SELECT campaign_id,status FROM marketing_campaigns WHERE opportunity_id=?",
                               (oid,)).fetchone()
        campaign_id = existing["campaign_id"] if existing else _uid("camp")
        status = "PLANNED" if not plan["approval_required"] else "AWAITING_APPROVAL"
        approval_state = "AUTONOMOUS_PLAN_READY" if not plan["approval_required"] else "RAY_APPROVAL_REQUIRED_FOR_GATED_ACTIONS"
        fields = (
            campaign_id, oid, plan["title"], status, "MONETIZE_NEXUS",
            plan["audience"], plan["customer_problem"], plan["positioning"], plan["offer"], plan["value_proposition"],
            plan["primary_channel"], _json(plan["alternative_channels"]),
            plan["funnel_type"], _json(plan["funnel"]),
            plan["landing_page_objective"], _json(plan["landing_page_requirements"]), plan["cta"],
            _json(plan["organic_strategy"]), _json(plan["paid_test"]),
            1 if plan["approval_required"] else 0, approval_state,
            _json(plan["attribution_plan"]), _json(plan["measurement_plan"]), _json(plan["creative_request"]),
            _json(plan["forecast"]), _json(_condense_handoff(handoff)), _json(plan["missing_inputs"]),
            str(plan["expected_test_cost"]),
            rec, reason, "CAMPAIGN_WORKING", None, 0, 0, 0, timestamp, timestamp,
        )
        if existing:
            con.execute(
                """UPDATE marketing_campaigns SET title=?,status=?,company_purpose=?,audience=?,customer_problem=?,
                positioning=?,offer=?,value_proposition=?,primary_channel=?,alternative_channels_json=?,funnel_type=?,
                funnel_json=?,landing_page_objective=?,landing_page_requirements_json=?,cta=?,organic_strategy_json=?,
                paid_test_json=?,approval_required=?,approval_state=?,attribution_plan_json=?,measurement_plan_json=?,
                creative_request_json=?,forecast_json=?,handoff_snapshot_json=?,missing_inputs_json=?,expected_test_cost=?,
                recommended_next_action=?,recommendation_reason=?,updated_at=? WHERE opportunity_id=?""",
                (plan["title"], status, "MONETIZE_NEXUS", plan["audience"], plan["customer_problem"],
                 plan["positioning"], plan["offer"], plan["value_proposition"], plan["primary_channel"],
                 _json(plan["alternative_channels"]), plan["funnel_type"], _json(plan["funnel"]),
                 plan["landing_page_objective"], _json(plan["landing_page_requirements"]), plan["cta"],
                 _json(plan["organic_strategy"]), _json(plan["paid_test"]), 1 if plan["approval_required"] else 0,
                 approval_state, _json(plan["attribution_plan"]), _json(plan["measurement_plan"]),
                 _json(plan["creative_request"]), _json(plan["forecast"]), _json(_condense_handoff(handoff)),
                 _json(plan["missing_inputs"]), str(plan["expected_test_cost"]), rec, reason, timestamp, oid),
            )
            _history(con, campaign_id, oid, "CAMPAIGN_REPLANNED", previous=existing["status"], new=status,
                     reason="Re-intake refreshed plan from current handoff.")
        else:
            con.execute(
                """INSERT INTO marketing_campaigns
                (campaign_id,opportunity_id,title,status,company_purpose,audience,customer_problem,positioning,offer,
                 value_proposition,primary_channel,alternative_channels_json,funnel_type,funnel_json,
                 landing_page_objective,landing_page_requirements_json,cta,organic_strategy_json,paid_test_json,
                 approval_required,approval_state,attribution_plan_json,measurement_plan_json,creative_request_json,
                 forecast_json,handoff_snapshot_json,missing_inputs_json,expected_test_cost,recommended_next_action,
                 recommendation_reason,retention_class,retain_until,legal_hold,promoted_to_long_term,deletion_eligible,
                 created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                fields,
            )
            _history(con, campaign_id, oid, "CAMPAIGN_INTAKE", new=status,
                     reason="Consumed certified Business Opportunities -> Marketing handoff.")
    return get_campaign(opportunity_id=oid, database_path=database_path, include_internal_ids=True)


def _condense_handoff(handoff: dict) -> dict[str, Any]:
    """Store only a condensed snapshot for lineage; raw evidence stays in BO/local only."""
    keep = ("OPPORTUNITY_ID", "WHAT_WE_ARE_MONETIZING", "RECOMMENDED_MONETIZATION_MODEL",
            "COMMERCIAL_RECOMMENDATION", "HANDOFF_READY", "MISSING_INPUTS", "PAID_TEST_LIMIT")
    return {k: handoff.get(k) for k in keep}


# --------------------------------------------------------------------------
# Layer 3: measurement / optimization + recommendation.
# --------------------------------------------------------------------------

def _recommend(plan_or_row: dict, perf_rows: list[dict]) -> tuple[str, str]:
    """Deterministic SCALE/CONTINUE/MODIFY/HOLD/STOP over recorded actuals only."""
    if not perf_rows:
        return "CONTINUE", ("Plan ready; execute ORGANIC_FIRST and measure. No actuals recorded yet, so no "
                            "data-driven scale/stop decision is possible.")
    totals = {k: 0.0 for k in ("impressions", "clicks", "leads", "conversions", "ad_spend",
                               "gross_revenue", "net_revenue")}
    roas_vals = []
    for r in perf_rows:
        for k in totals:
            v = r.get(k)
            if isinstance(v, (int, float)):
                totals[k] += v
        if isinstance(r.get("roas"), (int, float)):
            roas_vals.append(r["roas"])
    roas = (sum(roas_vals) / len(roas_vals)) if roas_vals else (
        (totals["gross_revenue"] / totals["ad_spend"]) if totals["ad_spend"] > 0 else None)
    if totals["impressions"] == 0 and totals["clicks"] == 0 and totals["conversions"] == 0:
        return "HOLD", "No measured traffic yet; awaiting deployment/approval before a decision."
    if totals["conversions"] > 0:
        if roas is not None and roas >= _ROAS_SCALE:
            return "SCALE", f"Positive conversions with ROAS {round(roas, 2)} >= {_ROAS_SCALE}."
        if roas is None or roas >= _ROAS_CONTINUE:
            return "CONTINUE", f"Converting; ROAS {('n/a' if roas is None else round(roas,2))} >= {_ROAS_CONTINUE} or organic (no spend)."
        return "MODIFY", f"Converting but ROAS {round(roas, 2)} below {_ROAS_CONTINUE}; adjust offer/targeting/cost."
    if totals["clicks"] > 0:
        return "MODIFY", "Traffic arriving but zero conversions; revise landing page/offer/CTA."
    return "MODIFY", "Impressions without clicks; revise hook/creative/channel."


def record_performance(opportunity_id: str, window: str, metrics: dict[str, Any], *,
                       source: str = "", attribution: dict | None = None,
                       database_path: str | Path | None = None) -> dict[str, Any]:
    """Record measured actuals for already-authorized activity (autonomous).

    Never fabricates: only the numeric fields actually supplied are stored.
    """
    initialize(database_path)
    numeric_fields = ("impressions", "reach", "clicks", "ctr", "landing_page_visits", "cta_clicks",
                      "affiliate_clicks", "leads", "conversions", "conversion_rate", "cpc", "cpl",
                      "cac", "ad_spend", "content_cost", "commissions", "gross_revenue", "net_revenue", "roas")
    with _connect(database_path) as con:
        row = con.execute("SELECT campaign_id,status FROM marketing_campaigns WHERE opportunity_id=?",
                          (opportunity_id,)).fetchone()
        if not row:
            return {"status": "NOT_FOUND", "reason": "NO_CAMPAIGN_FOR_OPPORTUNITY"}
        cid = row["campaign_id"]
        values = {}
        for f in numeric_fields:
            v = metrics.get(f)
            values[f] = float(v) if isinstance(v, (int, float)) else None
        perf_id = _uid("perf")
        con.execute(
            f"""INSERT INTO marketing_performance
            (perf_id,campaign_id,opportunity_id,window,{','.join(numeric_fields)},attribution_json,source,notes,
             retention_class,retain_until,recorded_at)
            VALUES ({','.join(['?'] * (4 + len(numeric_fields) + 6))})""",
            (perf_id, cid, opportunity_id, _clean_text(window, 20) or "LIVE",
             *[values[f] for f in numeric_fields], _json(attribution or {}), _clean_text(source, 120) or None,
             None, "EVENT_DETAIL", None, now()),
        )
        perf_rows = [dict(r) for r in con.execute(
            "SELECT * FROM marketing_performance WHERE campaign_id=?", (cid,))]
        rec, reason = _recommend({}, perf_rows)
        new_status = "MEASURING" if row["status"] in {"PLANNED", "AWAITING_APPROVAL", "INTAKE"} else row["status"]
        con.execute("UPDATE marketing_campaigns SET recommended_next_action=?,recommendation_reason=?,status=?,updated_at=? WHERE campaign_id=?",
                    (rec, reason, new_status, now(), cid))
        _history(con, cid, opportunity_id, "PERFORMANCE_RECORDED", new=new_status,
                 reason=f"Actuals recorded for window {window}; recommendation={rec}.",
                 metadata={"window": window, "recommendation": rec})
    return {"status": "RECORDED", "recommended_next_action": rec, "recommendation_reason": reason}


def performance(opportunity_id: str, *, database_path: str | Path | None = None,
                include_internal_ids: bool = False) -> dict[str, Any]:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        row = con.execute("SELECT * FROM marketing_campaigns WHERE opportunity_id=?", (opportunity_id,)).fetchone()
        if not row:
            return {"status": "NOT_FOUND"}
        perf_rows = [dict(r) for r in con.execute(
            "SELECT * FROM marketing_performance WHERE campaign_id=? ORDER BY recorded_at", (row["campaign_id"],))]
    forecast = json.loads(row["forecast_json"] or "{}")
    actual = _aggregate_actuals(perf_rows)
    result = {
        "OPPORTUNITY_ID": row["opportunity_id"], "CAMPAIGN_ID": row["campaign_id"],
        "FORECAST": forecast, "ACTUAL": actual,
        "FORECAST_VS_ACTUAL": {
            "EXPECTED_30_DAY_REVENUE": forecast.get("EXPECTED_30_DAY_REVENUE", UNKNOWN),
            "ACTUAL_30_DAY_REVENUE": actual.get("ACTUAL_30_DAY_REVENUE", UNKNOWN),
            "EXPECTED_60_DAY_REVENUE": forecast.get("EXPECTED_60_DAY_REVENUE", UNKNOWN),
            "ACTUAL_60_DAY_REVENUE": actual.get("ACTUAL_60_DAY_REVENUE", UNKNOWN),
            "EXPECTED_90_DAY_REVENUE": forecast.get("EXPECTED_90_DAY_REVENUE", UNKNOWN),
            "ACTUAL_90_DAY_REVENUE": actual.get("ACTUAL_90_DAY_REVENUE", UNKNOWN),
            "EXPECTED_TEST_COST": forecast.get("EXPECTED_TEST_COST", UNKNOWN),
            "ACTUAL_TEST_COST": actual.get("ACTUAL_TEST_COST", UNKNOWN),
        },
        "LEDGER_ROWS": len(perf_rows),
        "RECOMMENDED_NEXT_ACTION": row["recommended_next_action"],
        "RECOMMENDATION_REASON": row["recommendation_reason"],
    }
    return _public(result, include_internal_ids=include_internal_ids)


def _aggregate_actuals(perf_rows: list[dict]) -> dict[str, Any]:
    if not perf_rows:
        return {"RECORDS": 0, "NOTE": "No actuals recorded; all actual fields UNKNOWN."}
    def total(field):
        vals = [r[field] for r in perf_rows if isinstance(r.get(field), (int, float))]
        return round(sum(vals), 4) if vals else UNKNOWN
    def window_rev(win):
        vals = [r["gross_revenue"] for r in perf_rows
                if str(r.get("window")) == win and isinstance(r.get("gross_revenue"), (int, float))]
        return round(sum(vals), 2) if vals else UNKNOWN
    return {
        "RECORDS": len(perf_rows),
        "TOTAL_IMPRESSIONS": total("impressions"), "TOTAL_CLICKS": total("clicks"),
        "TOTAL_LEADS": total("leads"), "TOTAL_CONVERSIONS": total("conversions"),
        "TOTAL_AD_SPEND": total("ad_spend"), "TOTAL_GROSS_REVENUE": total("gross_revenue"),
        "TOTAL_NET_REVENUE": total("net_revenue"), "ACTUAL_TEST_COST": total("ad_spend"),
        "ACTUAL_30_DAY_REVENUE": window_rev("30_DAY"), "ACTUAL_60_DAY_REVENUE": window_rev("60_DAY"),
        "ACTUAL_90_DAY_REVENUE": window_rev("90_DAY"),
    }


# --------------------------------------------------------------------------
# Market intelligence feedback.
# --------------------------------------------------------------------------

def record_feedback(intel_type: str, observation: str, *, opportunity_id: str = "", campaign_id: str = "",
                    structured: dict | None = None, source: str = "",
                    database_path: str | Path | None = None) -> dict[str, Any]:
    initialize(database_path)
    with _connect(database_path) as con:
        intel_id = _uid("intel")
        con.execute(
            """INSERT INTO marketing_intelligence
            (intel_id,opportunity_id,campaign_id,intel_type,observation,structured_json,source,
             retention_class,retain_until,promoted_to_long_term,deletion_eligible,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (intel_id, opportunity_id or None, campaign_id or None, _clean_text(intel_type, 60),
             _clean_text(observation, 2000), _json(structured or {}), _clean_text(source, 160) or None,
             "EVENT_DETAIL", None, 0, 0, now()),
        )
    return {"status": "RECORDED", "intel_type": intel_type}


def market_feedback(*, opportunity_id: str = "", limit: int = 50,
                    database_path: str | Path | None = None,
                    include_internal_ids: bool = False) -> dict[str, Any]:
    initialize(database_path)
    clause = "WHERE opportunity_id=?" if opportunity_id else ""
    params: tuple = (opportunity_id,) if opportunity_id else ()
    with _connect(database_path, readonly=True) as con:
        rows = [dict(r) for r in con.execute(
            f"SELECT intel_type,observation,source,created_at,structured_json FROM marketing_intelligence "
            f"{clause} ORDER BY created_at DESC LIMIT ?", (*params, max(1, min(int(limit), 200))))]
    for r in rows:
        r["structured"] = json.loads(r.pop("structured_json") or "{}")
    return {"status": "OK", "items": _public(rows, include_internal_ids=include_internal_ids), "count": len(rows)}


# --------------------------------------------------------------------------
# Reads: campaign, creative request, connections, status, Nova summary.
# --------------------------------------------------------------------------

def _row_to_campaign(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    for key in ("alternative_channels", "funnel", "landing_page_requirements", "organic_strategy",
                "paid_test", "attribution_plan", "measurement_plan", "creative_request", "forecast",
                "handoff_snapshot", "missing_inputs"):
        raw = d.pop(key + "_json", None)
        d[key] = json.loads(raw) if raw else None
    return d


def get_campaign(opportunity_id: str = "", campaign_id: str = "", *,
                 database_path: str | Path | None = None,
                 include_internal_ids: bool = False) -> dict[str, Any]:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        if campaign_id:
            row = con.execute("SELECT * FROM marketing_campaigns WHERE campaign_id=?", (campaign_id,)).fetchone()
        else:
            row = con.execute("SELECT * FROM marketing_campaigns WHERE opportunity_id=?", (opportunity_id,)).fetchone()
        if not row:
            return {"status": "NOT_FOUND"}
        campaign = _row_to_campaign(row)
    return {"status": "OK", "campaign": _public(campaign, include_internal_ids=include_internal_ids)}


def creative_request(opportunity_id: str = "", campaign_id: str = "", *,
                     database_path: str | Path | None = None,
                     include_internal_ids: bool = False) -> dict[str, Any]:
    result = get_campaign(opportunity_id, campaign_id, database_path=database_path, include_internal_ids=True)
    if result["status"] != "OK":
        return result
    campaign = result["campaign"]
    payload = {"OPPORTUNITY_ID": campaign["opportunity_id"], "CAMPAIGN_ID": campaign["campaign_id"],
               "CREATIVE_REQUEST": campaign["creative_request"],
               "LANDING_PAGE_REQUIREMENTS": campaign["landing_page_requirements"]}
    return {"status": "OK", "creative_request": _public(payload, include_internal_ids=include_internal_ids)}


def connections(*, database_path: str | Path | None = None) -> dict[str, Any]:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        rows = [dict(r) for r in con.execute(
            "SELECT platform,capability,read_available,write_available,publish_available,analytics_available,"
            "auth_state,approval_required,cost,business_purpose,status,last_verified,notes "
            "FROM marketing_connections ORDER BY platform,capability")]
    summary = {}
    for r in rows:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    return {"status": "OK", "count": len(rows), "status_summary": summary, "connections": rows}


def status(*, database_path: str | Path | None = None) -> dict[str, Any]:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        total = int(con.execute("SELECT count(*) FROM marketing_campaigns").fetchone()[0])
        by_status = {r[0]: r[1] for r in con.execute(
            "SELECT status,count(*) FROM marketing_campaigns GROUP BY status")}
        by_action = {r[0]: r[1] for r in con.execute(
            "SELECT recommended_next_action,count(*) FROM marketing_campaigns "
            "WHERE recommended_next_action IS NOT NULL GROUP BY recommended_next_action")}
        conns = int(con.execute("SELECT count(*) FROM marketing_connections").fetchone()[0])
        intel = int(con.execute("SELECT count(*) FROM marketing_intelligence").fetchone()[0])
    return {"status": "OK", "engine_version": ENGINE_VERSION, "mission": "MONETIZE_NEXUS",
            "campaigns": total, "campaigns_by_status": by_status, "campaigns_by_next_action": by_action,
            "connections": conns, "market_intelligence_records": intel,
            "policy": "ORGANIC_FIRST -> PROVE_INTEREST -> SMALL_PAID_TEST_IF_JUSTIFIED -> SCALE_ONLY_WITH_EVIDENCE"}


def list_campaigns(*, limit: int = 20, database_path: str | Path | None = None,
                   include_internal_ids: bool = False) -> dict[str, Any]:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        rows = [dict(r) for r in con.execute(
            "SELECT opportunity_id,campaign_id,title,status,primary_channel,recommended_next_action,approval_state,updated_at "
            "FROM marketing_campaigns ORDER BY updated_at DESC LIMIT ?", (max(1, min(int(limit), 100)),))]
    return {"status": "OK", "items": _public(rows, include_internal_ids=include_internal_ids), "count": len(rows)}


def nova_summary(opportunity_id: str = "", campaign_id: str = "", *,
                 database_path: str | Path | None = None,
                 include_internal_ids: bool = False) -> dict[str, Any]:
    """Nova-readable Marketing summary + next-action recommendation (logic stays here, not in Nova)."""
    result = get_campaign(opportunity_id, campaign_id, database_path=database_path, include_internal_ids=True)
    if result["status"] != "OK":
        return result
    c = result["campaign"]
    perf = performance(c["opportunity_id"], database_path=database_path, include_internal_ids=True)
    approval = []
    if c.get("approval_required"):
        approval.append("Public publishing/scheduling requires Ray approval.")
    pt = c.get("paid_test") or {}
    if pt.get("APPROVAL_REQUIRED"):
        approval.append(f"Paid test spend (max {pt.get('MAXIMUM_SPEND', UNKNOWN)}) requires Ray approval.")
    summary = {
        "OPPORTUNITY_ID": c["opportunity_id"], "CAMPAIGN_ID": c["campaign_id"],
        "WHAT_WE_ARE_MONETIZING": c["title"], "STATUS": c["status"],
        "PRIMARY_CHANNEL": c["primary_channel"], "ALTERNATIVE_CHANNELS": c["alternative_channels"],
        "AUDIENCE": c["audience"], "OFFER": c["offer"],
        "ORGANIC_FIRST": True, "APPROVAL_REQUIRED": bool(c.get("approval_required")),
        "APPROVAL_ITEMS": approval,
        "EXPECTED_TEST_COST": c["expected_test_cost"],
        "CREATIVE_REQUEST_READY": bool(c.get("creative_request")),
        "ATTRIBUTION_PLAN_READY": bool(c.get("attribution_plan")),
        "MEASUREMENT_PLAN_READY": bool(c.get("measurement_plan")),
        "FORECAST_VS_ACTUAL": perf.get("FORECAST_VS_ACTUAL") if perf.get("status") != "NOT_FOUND" else UNKNOWN,
        "MISSING_INPUTS": c.get("missing_inputs") or [],
        "COMMERCIAL_RECOMMENDATION_FROM_BO": (c.get("handoff_snapshot") or {}).get("COMMERCIAL_RECOMMENDATION", UNKNOWN),
        "RECOMMENDED_NEXT_ACTION": c["recommended_next_action"],
        "RECOMMENDATION_REASON": c["recommendation_reason"],
    }
    return {"status": "OK", "nova_summary": _public(summary, include_internal_ids=include_internal_ids)}


def health(*, database_path: str | Path | None = None) -> dict[str, Any]:
    db_path = _db_path(database_path)
    try:
        initialize(db_path)
        with _connect(db_path, readonly=True) as con:
            integrity = str(con.execute("PRAGMA quick_check").fetchone()[0])
            version = int(con.execute("PRAGMA user_version").fetchone()[0])
            campaigns = int(con.execute("SELECT count(*) FROM marketing_campaigns").fetchone()[0])
            conns = int(con.execute("SELECT count(*) FROM marketing_connections").fetchone()[0])
    except (sqlite3.Error, OSError, RuntimeError) as exc:
        return {"status": "DEGRADED", "error_class": type(exc).__name__, "database_path": str(db_path)}
    bo_status = "UNKNOWN"
    try:
        from scripts.opportunities import engine as bo_engine
        bo_status = "AVAILABLE" if hasattr(bo_engine, "marketing_handoff") else "MISSING_HANDOFF"
    except Exception:
        bo_status = "UNAVAILABLE"
    return {"status": "PASS" if integrity == "ok" and version == SCHEMA_VERSION else "DEGRADED",
            "engine_version": ENGINE_VERSION, "sqlite_integrity": integrity, "schema_version": version,
            "campaign_count": campaigns, "connection_count": conns,
            "business_opportunities_handoff": bo_status,
            "authority": {"LOCAL_SQLITE_IS_AUTHORITATIVE": "YES", "SUPABASE_IS_COORDINATION_LAYER": "YES",
                          "SUPABASE_IS_RAW_DATA_WAREHOUSE": "NO"},
            "database_path": str(db_path)}
