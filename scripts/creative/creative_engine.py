"""Nexus Creative Engine: turns certified Marketing strategy into finished,
usable assets (and production-ready asset specifications).

HARD RULE:
  MARKETING DECIDES audience, customer problem, emotional driver, positioning,
  offer, channel, format, hook, message, CTA, campaign objective, success metric,
  and landing-page requirements.
  CREATIVE CREATES video/images/graphics/scripts/copy/thumbnails/social/ad/email/
  landing-page creative and supporting media.

Creative must NOT reinvent Marketing strategy, choose a monetization model, or
redo Research. It consumes the certified Marketing downstream interface
``marketing_creative_request`` and never asks Marketing to restate it.

Governance (SOLUTION_FIRST / RAY_DECIDES): Creative may autonomously draft,
generate copy/script/direction, plan, quality-check, compliance-check, and
prepare approval packages and revisions. It must NOT autonomously publish,
schedule public content, spend money, activate paid providers, change
credentials, or deploy campaigns — those are governed and emitted as approval
cards. External paid media generation (image/video/voice render) stops at an
approval boundary.

Data policy: LOCAL_SQLITE_IS_AUTHORITATIVE=YES, SUPABASE_IS_COORDINATION_LAYER=YES,
SUPABASE_IS_RAW_MEDIA_WAREHOUSE=NO. Full engine state, raw media metadata,
intermediate work and render logs stay local. Large media files belong in the
media/storage layer, never as SQLite blobs; only final asset pointers are
coordination-eligible. If Supabase and SQLite disagree, local SQLite wins.

No fabrication: Creative never invents testimonials, reviews, customer outcomes,
scarcity, endorsements, product capabilities, affiliate relationships, or
performance claims. Evidence slots are explicit placeholders requiring real proof
before any publish.
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
ENGINE_VERSION = "nexus-creative-engine-v1"
DB_PATH = Path.home() / ".nexus/state/creative/creative.sqlite3"

UNKNOWN = "UNKNOWN"

ASSET_STATUSES = {
    "REQUESTED", "PLANNING", "GENERATING", "REVIEW_REQUIRED", "APPROVAL_REQUIRED",
    "READY_FOR_MARKETING", "REJECTED", "REVISION_REQUIRED", "ARCHIVED",
}

# Asset types that are pure-text / zero-cost and can complete autonomously.
_TEXT_ASSET_TYPES = {"COPY", "SCRIPT", "EMAIL_COPY", "LANDING_PAGE_COPY", "HEADLINES", "SOCIAL_CAPTION", "AD_COPY"}
# Asset types that need external (potentially paid) generation -> approval boundary.
_MEDIA_ASSET_TYPES = {"IMAGE", "GRAPHIC", "THUMBNAIL", "COMPARISON_GRAPHIC", "VIDEO", "VOICEOVER", "LANDING_PAGE_VISUAL"}

# Channel -> default asset plan (asset_type, format, dimensions_or_duration).
_CHANNEL_PLAN = {
    "TIKTOK": [("SCRIPT", "short_video_script", "~20-40s"), ("VIDEO", "vertical_video", "9:16 ~20-40s"), ("SOCIAL_CAPTION", "caption", "n/a")],
    "TIKTOK_ADS": [("SCRIPT", "short_video_script", "~15-30s"), ("VIDEO", "vertical_video", "9:16 ~15-30s"), ("AD_COPY", "ad_copy", "n/a")],
    "YOUTUBE": [("SCRIPT", "video_script", "as specified"), ("THUMBNAIL", "thumbnail", "1280x720"), ("COPY", "title_description", "n/a")],
    "INSTAGRAM": [("SCRIPT", "reel_script", "~15-30s"), ("VIDEO", "vertical_video", "9:16"), ("SOCIAL_CAPTION", "caption", "n/a")],
    "FACEBOOK": [("AD_COPY", "feed_copy", "n/a"), ("IMAGE", "feed_image", "1200x628"), ("SOCIAL_CAPTION", "caption", "n/a")],
    "PINTEREST": [("IMAGE", "vertical_pin", "1000x1500"), ("COPY", "pin_copy", "search-oriented")],
    "LINKEDIN": [("COPY", "professional_post", "n/a"), ("IMAGE", "feed_image", "1200x627")],
    "NEWSLETTER_BEEHIIV": [("EMAIL_COPY", "email", "subject+preview+body"), ("CTA", "cta", "n/a")],
    "EMAIL_LEAD_CAPTURE": [("EMAIL_COPY", "email", "subject+preview+body")],
    "SEO_SEARCH_CONSOLE": [("LANDING_PAGE_COPY", "landing_copy", "hero+benefits+CTA"),
                           ("COMPARISON_GRAPHIC", "buyer_guide_graphic", "spec"),
                           ("LANDING_PAGE_VISUAL", "hero_visual", "spec")],
    "X": [("COPY", "post", "n/a")],
}

# Compliance: patterns that indicate fabricated claims/scarcity/endorsement.
_FORBIDDEN_CLAIM_RE = re.compile(
    r"\b(guarantee[d]?|#1|number one|best ever|100% (?:guaranteed|results)|risk[- ]free|"
    r"as seen on|doctor recommended|clinically proven|thousands of (?:happy )?customers|"
    r"everyone is|proven to (?:cure|earn|make)|get rich)\b", re.IGNORECASE)
_SCARCITY_RE = re.compile(r"\b(only \d+ left|last chance|act now|hurry|limited time|ends tonight)\b", re.IGNORECASE)
_TESTIMONIAL_RE = re.compile(r'"[^"]{10,}"\s*[-—]\s*[A-Z][a-z]+', re.IGNORECASE)

SCHEMA = """
CREATE TABLE IF NOT EXISTS creative_requests (
 creative_request_id TEXT PRIMARY KEY,
 opportunity_id TEXT NOT NULL,
 campaign_id TEXT,
 audience TEXT, customer_problem TEXT, emotional_driver TEXT, positioning TEXT, offer TEXT,
 channel TEXT, content_format TEXT, hook TEXT, message TEXT, cta TEXT,
 asset_requirements_json TEXT, landing_page_requirements_json TEXT,
 campaign_objective TEXT, success_metric TEXT, brief_snapshot_json TEXT,
 status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(opportunity_id)
);
CREATE TABLE IF NOT EXISTS creative_assets (
 asset_id TEXT PRIMARY KEY,
 creative_request_id TEXT NOT NULL REFERENCES creative_requests(creative_request_id) ON DELETE CASCADE,
 opportunity_id TEXT NOT NULL, campaign_id TEXT,
 asset_type TEXT NOT NULL, channel TEXT, format TEXT, dimensions_or_duration TEXT,
 audience TEXT, hook TEXT, message TEXT, cta TEXT,
 script TEXT, copy_json TEXT, visual_direction_json TEXT, audio_direction TEXT,
 voice_direction TEXT, brand_direction TEXT,
 source_assets_json TEXT, generated_assets_json TEXT, final_asset_location TEXT,
 version INTEGER NOT NULL DEFAULT 1, status TEXT NOT NULL,
 quality_check_json TEXT, compliance_check_json TEXT,
 approval_required INTEGER NOT NULL DEFAULT 0, approval_reason TEXT,
 marketing_success_metric TEXT, marketing_handoff_ready INTEGER NOT NULL DEFAULT 0,
 retention_class TEXT NOT NULL DEFAULT 'CREATIVE_WORKING', retain_until TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_creative_assets_owner ON creative_assets(opportunity_id, asset_type);
CREATE TABLE IF NOT EXISTS creative_feedback (
 feedback_id TEXT PRIMARY KEY,
 opportunity_id TEXT, campaign_id TEXT, asset_id TEXT,
 winning_hook TEXT, winning_format TEXT, winning_creative TEXT,
 ctr REAL, conversion_rate REAL, revenue_attribution REAL,
 customer_response TEXT, what_worked TEXT, what_failed TEXT, lessons_learned TEXT,
 retention_class TEXT NOT NULL DEFAULT 'LONG_TERM_KNOWLEDGE', retain_until TEXT,
 created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_creative_feedback_owner ON creative_feedback(opportunity_id);
CREATE TABLE IF NOT EXISTS creative_history (
 event_id TEXT PRIMARY KEY, creative_request_id TEXT, asset_id TEXT, opportunity_id TEXT,
 event_type TEXT NOT NULL, previous_state TEXT, new_state TEXT,
 actor TEXT, reason TEXT, metadata_json TEXT, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_creative_history_owner ON creative_history(opportunity_id, created_at);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _clean_text(value: Any, limit: int = 4000) -> str:
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
            raise RuntimeError("CREATIVE_SCHEMA_NEWER_THAN_RUNTIME")
        con.executescript(SCHEMA)
        con.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    try:
        os.chmod(db_path, 0o600)
    except OSError:
        pass
    return {"status": "READY", "schema_version": SCHEMA_VERSION, "database_path": str(db_path)}


def _public(value: Any, *, include_internal_ids: bool = False) -> Any:
    hidden = {"opportunity_id", "campaign_id", "creative_request_id", "asset_id", "feedback_id", "event_id"}
    if isinstance(value, dict):
        return {k: _public(v, include_internal_ids=include_internal_ids)
                for k, v in value.items() if include_internal_ids or k.casefold() not in hidden}
    if isinstance(value, list):
        return [_public(v, include_internal_ids=include_internal_ids) for v in value]
    if isinstance(value, str) and not include_internal_ids:
        value = re.sub(r"\b(?:creq|asset|fb|evt|camp|opp)_[a-f0-9]{32}\b", "[internal reference]", value)
    return value


def _history(con, *, creative_request_id=None, asset_id=None, opportunity_id=None, event_type,
             previous="", new="", reason="", metadata=None, actor="creative") -> None:
    con.execute(
        """INSERT INTO creative_history
        (event_id,creative_request_id,asset_id,opportunity_id,event_type,previous_state,new_state,
         actor,reason,metadata_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (_uid("evt"), creative_request_id, asset_id, opportunity_id, event_type, previous or None,
         new or None, actor, _clean_text(reason, 500) or None, _json(metadata or {}), now()),
    )


# --------------------------------------------------------------------------
# Consume certified Marketing -> Creative request.
# --------------------------------------------------------------------------

def _pull_creative_request(opportunity_id: str) -> dict[str, Any]:
    from scripts.marketing import engine as marketing_engine
    result = marketing_engine.creative_request(opportunity_id=opportunity_id, include_internal_ids=True)
    if result.get("status") != "OK":
        return {}
    payload = result["creative_request"]
    cr = payload.get("CREATIVE_REQUEST", {}) or {}
    return {
        "OPPORTUNITY_ID": payload.get("OPPORTUNITY_ID", opportunity_id),
        "CAMPAIGN_ID": payload.get("CAMPAIGN_ID"),
        "LANDING_PAGE_REQUIREMENTS": payload.get("LANDING_PAGE_REQUIREMENTS"),
        **cr,
    }


# --------------------------------------------------------------------------
# Deterministic copy/script/direction generation from the brief. No fabrication.
# --------------------------------------------------------------------------

def _generate_copy(req: dict, asset_type: str) -> dict[str, Any]:
    audience = req.get("AUDIENCE", UNKNOWN)
    problem = req.get("CUSTOMER_PROBLEM", UNKNOWN)
    emotion = req.get("EMOTIONAL_DRIVER", UNKNOWN)
    hook = req.get("HOOK", UNKNOWN)
    message = req.get("MESSAGE", UNKNOWN)
    cta = req.get("CTA", UNKNOWN)
    offer = req.get("OFFER", UNKNOWN)
    # Content pattern: INTERRUPT -> CURIOSITY -> EMOTION -> EVIDENCE -> REMOVE_FRICTION -> CLEAR_ACTION.
    return {
        "INTERRUPT": hook if hook != UNKNOWN else (f"{audience}: {problem}" if audience != UNKNOWN else UNKNOWN),
        "CURIOSITY": (f"What most {audience} miss about {problem}" if audience != UNKNOWN and problem != UNKNOWN else UNKNOWN),
        "EMOTION": emotion,
        "EVIDENCE": "[EVIDENCE_PLACEHOLDER: insert only real, verifiable proof before publish; none fabricated]",
        "REMOVE_FRICTION": (f"Clear, honest next step toward: {message}" if message != UNKNOWN else UNKNOWN),
        "CLEAR_ACTION": cta,
        "HEADLINE_VARIANTS": [h for h in [hook, message, (f"{offer} for {audience}" if offer != UNKNOWN and audience != UNKNOWN else None)] if h and h != UNKNOWN][:3] or [UNKNOWN],
        "BODY": message,
        "OFFER": offer,
        "GENERATED_FROM": "marketing_brief_only",
        "FABRICATION": "none",
    }


def _script_for(req: dict, fmt: str) -> str:
    hook = req.get("HOOK", UNKNOWN)
    problem = req.get("CUSTOMER_PROBLEM", UNKNOWN)
    message = req.get("MESSAGE", UNKNOWN)
    cta = req.get("CTA", UNKNOWN)
    beats = [
        f"HOOK (0-3s): {hook}",
        f"PROBLEM: {problem}",
        f"VALUE: {message}",
        "EVIDENCE: [insert real proof only]",
        f"CTA: {cta}",
    ]
    return " | ".join(beats)


def _directions(req: dict, asset_type: str) -> dict[str, Any]:
    channel = req.get("CHANNEL", UNKNOWN)
    visual = {
        "STYLE": "Channel-native, concrete lighting/composition, authentic physical textures.",
        "FOCAL_POINT": req.get("OFFER", UNKNOWN),
        "DO_NOT": [
            "fabricated testimonials/badges", "fake scarcity", "unverified claims",
            "meaningless glowing orbs", "floating UI cards", "purple/blue AI gradients",
            "generic 3-card grid default", "glassmorphism",
        ],
        "CHANNEL": channel,
        "ANTI_SLOP_POLICY": "AI_SLOP_SCORE <= 25 required; concrete camera, lighting, and materials only.",
    }
    audio = "Clear voiceover pacing; licensed/royalty-free background only." if asset_type in {"VIDEO", "VOICEOVER"} else "n/a"
    voice = ("Natural narration; do NOT clone or imitate a real person's voice without authorization."
             if asset_type in {"VIDEO", "VOICEOVER"} else "n/a")
    brand = "Follow brand/avatar registry if one applies; disclosure where required."
    return {"visual": visual, "audio": audio, "voice": voice, "brand": brand}


def _asset_plan(req: dict) -> list[dict[str, Any]]:
    requirements = [str(r) for r in (req.get("ASSET_REQUIREMENTS") or []) if r]
    concrete = [r for r in requirements if r and not r.upper().startswith("TBD")]
    channel = str(req.get("CHANNEL") or UNKNOWN).upper()
    plan: list[dict[str, Any]] = []
    if concrete:
        for item in concrete:
            atype = _infer_asset_type(item)
            plan.append({"asset_type": atype, "format": _clean_text(item, 80),
                         "dimensions_or_duration": _dim_for(channel, atype), "source": "ASSET_REQUIREMENT"})
    else:
        for atype, fmt, dim in _CHANNEL_PLAN.get(channel, [("COPY", "generic_copy", "n/a"),
                                                            ("IMAGE", "generic_image", "spec")]):
            plan.append({"asset_type": atype, "format": fmt, "dimensions_or_duration": dim,
                         "source": "CHANNEL_DEFAULT [DERIVED]"})
    return plan


def _infer_asset_type(text: str) -> str:
    t = text.upper()
    if "VIDEO" in t:
        return "VIDEO"
    if "THUMBNAIL" in t:
        return "THUMBNAIL"
    if "COMPARISON" in t:
        return "COMPARISON_GRAPHIC"
    if "LANDING" in t and "VISUAL" in t:
        return "LANDING_PAGE_VISUAL"
    if "LANDING" in t or "PAGE COPY" in t:
        return "LANDING_PAGE_COPY"
    if "EMAIL" in t:
        return "EMAIL_COPY"
    if "IMAGE" in t or "GRAPHIC" in t or "VISUAL" in t:
        return "IMAGE"
    if "SCRIPT" in t:
        return "SCRIPT"
    if "CAPTION" in t:
        return "SOCIAL_CAPTION"
    if "AD" in t:
        return "AD_COPY"
    return "COPY"


def _dim_for(channel: str, atype: str) -> str:
    for a, fmt, dim in _CHANNEL_PLAN.get(channel, []):
        if a == atype:
            return dim
    return {"VIDEO": "9:16 or as specified", "IMAGE": "spec", "THUMBNAIL": "1280x720"}.get(atype, "n/a")


def _quality_check(asset: dict) -> dict[str, Any]:
    flags = []
    for field in ("audience", "hook", "message", "cta"):
        if not asset.get(field) or asset.get(field) == UNKNOWN:
            flags.append(f"missing_or_unknown:{field}")
    if not asset.get("channel") or asset["channel"] == UNKNOWN:
        flags.append("missing_channel")

    blob = _json({"copy": asset.get("copy"), "script": asset.get("script"),
                  "hook": asset.get("hook"), "message": asset.get("message")})
    from scripts.creative.creative_director import AntiAISlopEngine
    slop_audit = AntiAISlopEngine.audit_text(blob)
    if slop_audit["ai_slop_score"] > 25:
        flags.append(f"high_ai_slop_risk:{slop_audit['ai_slop_score']}")

    score = max(0, 100 - 20 * len(flags))
    return {
        "status": "PASS" if not flags else "FLAGGED",
        "score": score,
        "ai_slop_score": slop_audit["ai_slop_score"],
        "flags": flags,
        "note": "Quality reflects brief completeness and anti-slop standards; UNKNOWN brief fields or slop surface as flags.",
    }


def _compliance_check(asset: dict) -> dict[str, Any]:
    blob = _json({"copy": asset.get("copy"), "script": asset.get("script"),
                  "hook": asset.get("hook"), "message": asset.get("message")})
    flags = []
    if _FORBIDDEN_CLAIM_RE.search(blob):
        flags.append("forbidden_performance_or_endorsement_claim")
    if _SCARCITY_RE.search(blob):
        flags.append("scarcity_requires_real_deadline")
    if _TESTIMONIAL_RE.search(blob):
        flags.append("possible_fabricated_testimonial")

    from scripts.creative.product_truth_validator import ProductTruthValidator
    truth_audit = ProductTruthValidator.audit_copy(blob)
    if truth_audit["status"] != "PASS":
        for v in truth_audit["violations"]:
            flags.append(f"unverified_product_claim:{v['violation']}")

    return {"status": "PASS" if not flags else "FLAGGED", "flags": flags, "fabrication_detected": bool(flags),
            "truthfulness_score": truth_audit["truthfulness_score"],
            "rules": ["no fabricated testimonials/reviews/outcomes/endorsements",
                      "no fabricated scarcity or performance claims",
                      "real urgency only (actual deadlines/promotions/launches)",
                      "no unverified physical or manufacturing claims"]}


def _status_and_approval(asset_type: str, quality: dict, compliance: dict) -> tuple[str, int, str, int]:
    """Return (status, approval_required, approval_reason, marketing_handoff_ready)."""
    if compliance["status"] != "PASS":
        return "REVISION_REQUIRED", 0, "Compliance flags must be resolved before handoff.", 0
    if asset_type in _MEDIA_ASSET_TYPES:
        return ("APPROVAL_REQUIRED", 1,
                "External media generation (image/video/voice render) may require a paid provider; "
                "Ray approval required before generating/spending.", 0)
    # Text/zero-cost asset: content is produced inline and usable.
    if quality["status"] != "PASS":
        return "REVIEW_REQUIRED", 0, "Brief has UNKNOWN fields; review before marketing handoff.", 0
    return "READY_FOR_MARKETING", 0, "", 1


# --------------------------------------------------------------------------
# Intake + generation.
# --------------------------------------------------------------------------

def intake(opportunity_id: str, *, request: dict | None = None,
           database_path: str | Path | None = None) -> dict[str, Any]:
    """Consume the certified Marketing creative request and produce a structured
    asset plan with copy/script/direction, quality + compliance checks, status,
    and approval gating. Autonomous: generates text/direction only; no publish,
    no spend, no paid provider call. Idempotent per opportunity."""
    initialize(database_path)
    if request is None:
        request = _pull_creative_request(opportunity_id)
    if not isinstance(request, dict) or not request:
        return {"status": "REJECTED", "reason": "EMPTY_OR_INVALID_CREATIVE_REQUEST"}
    oid = str(request.get("OPPORTUNITY_ID") or opportunity_id or "").strip()
    if not oid:
        return {"status": "REJECTED", "reason": "OPPORTUNITY_ID_REQUIRED"}
    campaign_id = request.get("CAMPAIGN_ID")
    timestamp = now()
    plan = _asset_plan(request)

    with _connect(database_path) as con:
        existing = con.execute("SELECT creative_request_id FROM creative_requests WHERE opportunity_id=?",
                               (oid,)).fetchone()
        creq_id = existing["creative_request_id"] if existing else _uid("creq")
        fields = (
            creq_id, oid, campaign_id, request.get("AUDIENCE"), request.get("CUSTOMER_PROBLEM"),
            request.get("EMOTIONAL_DRIVER"), request.get("POSITIONING"), request.get("OFFER"),
            request.get("CHANNEL"), request.get("CONTENT_FORMAT"), request.get("HOOK"),
            request.get("MESSAGE"), request.get("CTA"), _json(request.get("ASSET_REQUIREMENTS") or []),
            _json(request.get("LANDING_PAGE_REQUIREMENTS") or {}), request.get("CAMPAIGN_OBJECTIVE"),
            request.get("SUCCESS_METRIC"), _json(_condense_brief(request)), "PLANNING", timestamp, timestamp,
        )
        if existing:
            con.execute("DELETE FROM creative_assets WHERE creative_request_id=?", (creq_id,))
            con.execute(
                """UPDATE creative_requests SET campaign_id=?,audience=?,customer_problem=?,emotional_driver=?,
                positioning=?,offer=?,channel=?,content_format=?,hook=?,message=?,cta=?,asset_requirements_json=?,
                landing_page_requirements_json=?,campaign_objective=?,success_metric=?,brief_snapshot_json=?,
                status=?,updated_at=? WHERE opportunity_id=?""",
                (campaign_id, request.get("AUDIENCE"), request.get("CUSTOMER_PROBLEM"), request.get("EMOTIONAL_DRIVER"),
                 request.get("POSITIONING"), request.get("OFFER"), request.get("CHANNEL"), request.get("CONTENT_FORMAT"),
                 request.get("HOOK"), request.get("MESSAGE"), request.get("CTA"), _json(request.get("ASSET_REQUIREMENTS") or []),
                 _json(request.get("LANDING_PAGE_REQUIREMENTS") or {}), request.get("CAMPAIGN_OBJECTIVE"),
                 request.get("SUCCESS_METRIC"), _json(_condense_brief(request)), "PLANNING", timestamp, oid),
            )
            _history(con, creative_request_id=creq_id, opportunity_id=oid, event_type="CREATIVE_REPLANNED",
                     new="PLANNING", reason="Re-intake refreshed plan from current Marketing creative request.")
        else:
            con.execute(
                """INSERT INTO creative_requests
                (creative_request_id,opportunity_id,campaign_id,audience,customer_problem,emotional_driver,positioning,
                 offer,channel,content_format,hook,message,cta,asset_requirements_json,landing_page_requirements_json,
                 campaign_objective,success_metric,brief_snapshot_json,status,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", fields)
            _history(con, creative_request_id=creq_id, opportunity_id=oid, event_type="CREATIVE_INTAKE",
                     new="PLANNING", reason="Consumed certified Marketing -> Creative request.")

        for spec in plan:
            atype = spec["asset_type"]
            copy = _generate_copy(request, atype)
            script = _script_for(request, spec["format"]) if atype in {"SCRIPT", "VIDEO"} else None
            directions = _directions(request, atype)
            asset = {
                "asset_type": atype, "channel": request.get("CHANNEL"), "format": spec["format"],
                "audience": request.get("AUDIENCE"), "hook": request.get("HOOK"),
                "message": request.get("MESSAGE"), "cta": request.get("CTA"),
                "copy": copy, "script": script,
            }
            quality = _quality_check(asset)
            compliance = _compliance_check(asset)
            status, appr_req, appr_reason, handoff_ready = _status_and_approval(atype, quality, compliance)
            final_location = "inline:creative_authority" if atype in _TEXT_ASSET_TYPES and handoff_ready else None
            asset_id = _uid("asset")
            con.execute(
                """INSERT INTO creative_assets
                (asset_id,creative_request_id,opportunity_id,campaign_id,asset_type,channel,format,
                 dimensions_or_duration,audience,hook,message,cta,script,copy_json,visual_direction_json,
                 audio_direction,voice_direction,brand_direction,source_assets_json,generated_assets_json,
                 final_asset_location,version,status,quality_check_json,compliance_check_json,approval_required,
                 approval_reason,marketing_success_metric,marketing_handoff_ready,retention_class,retain_until,
                 created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (asset_id, creq_id, oid, campaign_id, atype, request.get("CHANNEL"), spec["format"],
                 spec["dimensions_or_duration"], request.get("AUDIENCE"), request.get("HOOK"),
                 request.get("MESSAGE"), request.get("CTA"), script, _json(copy), _json(directions["visual"]),
                 directions["audio"], directions["voice"], directions["brand"], _json([]), _json([]),
                 final_location, 1, status, _json(quality), _json(compliance), appr_req, appr_reason or None,
                 request.get("SUCCESS_METRIC"), handoff_ready, "CREATIVE_WORKING", None, timestamp, timestamp),
            )
        req_status = "REVIEW_REQUIRED"
        ready = con.execute("SELECT count(*) FROM creative_assets WHERE creative_request_id=? AND marketing_handoff_ready=1",
                            (creq_id,)).fetchone()[0]
        if ready:
            req_status = "READY_FOR_MARKETING"
        con.execute("UPDATE creative_requests SET status=?,updated_at=? WHERE creative_request_id=?",
                    (req_status, now(), creq_id))
    return get_creative(opportunity_id=oid, database_path=database_path, include_internal_ids=True)


def _condense_brief(req: dict) -> dict[str, Any]:
    keep = ("OPPORTUNITY_ID", "CAMPAIGN_ID", "CHANNEL", "OFFER", "CAMPAIGN_OBJECTIVE", "SUCCESS_METRIC")
    return {k: req.get(k) for k in keep}


# --------------------------------------------------------------------------
# Reads + output contract.
# --------------------------------------------------------------------------

def _asset_contract(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    return {
        "OPPORTUNITY_ID": d["opportunity_id"], "CAMPAIGN_ID": d["campaign_id"],
        "CREATIVE_REQUEST_ID": d["creative_request_id"], "ASSET_ID": d["asset_id"],
        "ASSET_TYPE": d["asset_type"], "CHANNEL": d["channel"], "FORMAT": d["format"],
        "DIMENSIONS_OR_DURATION": d["dimensions_or_duration"], "AUDIENCE": d["audience"],
        "HOOK": d["hook"], "MESSAGE": d["message"], "CTA": d["cta"],
        "SCRIPT": d["script"], "COPY": json.loads(d["copy_json"] or "null"),
        "VISUAL_DIRECTION": json.loads(d["visual_direction_json"] or "null"),
        "AUDIO_DIRECTION": d["audio_direction"], "VOICE_DIRECTION": d["voice_direction"],
        "BRAND_DIRECTION": d["brand_direction"],
        "SOURCE_ASSETS": json.loads(d["source_assets_json"] or "[]"),
        "GENERATED_ASSETS": json.loads(d["generated_assets_json"] or "[]"),
        "FINAL_ASSET_LOCATION": d["final_asset_location"],
        "VERSION": d["version"], "STATUS": d["status"],
        "QUALITY_CHECK": json.loads(d["quality_check_json"] or "null"),
        "COMPLIANCE_CHECK": json.loads(d["compliance_check_json"] or "null"),
        "APPROVAL_REQUIRED": bool(d["approval_required"]), "APPROVAL_REASON": d["approval_reason"],
        "MARKETING_SUCCESS_METRIC": d["marketing_success_metric"],
        "MARKETING_HANDOFF_READY": bool(d["marketing_handoff_ready"]),
    }


def get_creative(opportunity_id: str = "", creative_request_id: str = "", *,
                 database_path: str | Path | None = None,
                 include_internal_ids: bool = False) -> dict[str, Any]:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        if creative_request_id:
            req = con.execute("SELECT * FROM creative_requests WHERE creative_request_id=?", (creative_request_id,)).fetchone()
        else:
            req = con.execute("SELECT * FROM creative_requests WHERE opportunity_id=?", (opportunity_id,)).fetchone()
        if not req:
            return {"status": "NOT_FOUND"}
        assets = [_asset_contract(r) for r in con.execute(
            "SELECT * FROM creative_assets WHERE creative_request_id=? ORDER BY asset_type", (req["creative_request_id"],))]
    out = {
        "status": "OK",
        "creative": {
            "OPPORTUNITY_ID": req["opportunity_id"], "CAMPAIGN_ID": req["campaign_id"],
            "CREATIVE_REQUEST_ID": req["creative_request_id"], "CHANNEL": req["channel"],
            "CAMPAIGN_OBJECTIVE": req["campaign_objective"], "SUCCESS_METRIC": req["success_metric"],
            "STATUS": req["status"], "ASSET_COUNT": len(assets), "ASSETS": assets,
        },
    }
    return _public(out, include_internal_ids=include_internal_ids)


def asset(asset_id: str, *, database_path: str | Path | None = None,
          include_internal_ids: bool = False) -> dict[str, Any]:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        row = con.execute("SELECT * FROM creative_assets WHERE asset_id=?", (asset_id,)).fetchone()
        if not row:
            return {"status": "NOT_FOUND"}
    return {"status": "OK", "asset": _public(_asset_contract(row), include_internal_ids=include_internal_ids)}


def marketing_handoff(opportunity_id: str = "", creative_request_id: str = "", *,
                      database_path: str | Path | None = None,
                      include_internal_ids: bool = False) -> dict[str, Any]:
    """Creative -> Marketing handoff: ready assets plus what remains approval-gated."""
    result = get_creative(opportunity_id, creative_request_id, database_path=database_path, include_internal_ids=True)
    if result["status"] != "OK":
        return result
    c = result["creative"]
    ready = [a for a in c["ASSETS"] if a["MARKETING_HANDOFF_READY"]]
    pending = [{"ASSET_TYPE": a["ASSET_TYPE"], "STATUS": a["STATUS"], "APPROVAL_REASON": a["APPROVAL_REASON"]}
               for a in c["ASSETS"] if not a["MARKETING_HANDOFF_READY"]]
    payload = {
        "OPPORTUNITY_ID": c["OPPORTUNITY_ID"], "CAMPAIGN_ID": c["CAMPAIGN_ID"],
        "CREATIVE_REQUEST_ID": c["CREATIVE_REQUEST_ID"], "CHANNEL": c["CHANNEL"],
        "READY_ASSETS": ready, "READY_COUNT": len(ready),
        "PENDING_APPROVAL_OR_REVIEW": pending, "PENDING_COUNT": len(pending),
        "MARKETING_HANDOFF_READY": len(ready) > 0,
        "SUCCESS_METRIC": c["SUCCESS_METRIC"],
        "NOTE": "Ready assets are copy/script/direction (zero-cost, produced inline). Media generation is "
                "approval-gated and listed under PENDING_APPROVAL_OR_REVIEW. CREATIVE CREATES; MARKETING DEPLOYS.",
    }
    return {"status": "OK", "creative_marketing_handoff": _public(payload, include_internal_ids=include_internal_ids)}


def record_feedback(opportunity_id: str, *, winning_hook: str = "", winning_format: str = "",
                    winning_creative: str = "", ctr: float | None = None, conversion_rate: float | None = None,
                    revenue_attribution: float | None = None, customer_response: str = "",
                    what_worked: str = "", what_failed: str = "", lessons_learned: str = "",
                    asset_id: str = "", campaign_id: str = "",
                    database_path: str | Path | None = None) -> dict[str, Any]:
    """Accept Marketing performance feedback; preserve durable lessons. Creative does
    not change Marketing strategy."""
    initialize(database_path)
    with _connect(database_path) as con:
        fid = _uid("fb")
        con.execute(
            """INSERT INTO creative_feedback
            (feedback_id,opportunity_id,campaign_id,asset_id,winning_hook,winning_format,winning_creative,
             ctr,conversion_rate,revenue_attribution,customer_response,what_worked,what_failed,lessons_learned,
             retention_class,retain_until,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (fid, opportunity_id or None, campaign_id or None, asset_id or None,
             _clean_text(winning_hook, 300) or None, _clean_text(winning_format, 120) or None,
             _clean_text(winning_creative, 300) or None,
             float(ctr) if isinstance(ctr, (int, float)) else None,
             float(conversion_rate) if isinstance(conversion_rate, (int, float)) else None,
             float(revenue_attribution) if isinstance(revenue_attribution, (int, float)) else None,
             _clean_text(customer_response, 1000) or None, _clean_text(what_worked, 1000) or None,
             _clean_text(what_failed, 1000) or None, _clean_text(lessons_learned, 1000) or None,
             "LONG_TERM_KNOWLEDGE", None, now()),
        )
        _history(con, opportunity_id=opportunity_id, event_type="MARKETING_FEEDBACK_RECORDED",
                 reason="Preserved durable creative lessons from Marketing performance.")
    return {"status": "RECORDED"}


def feedback(opportunity_id: str = "", limit: int = 50, *, database_path: str | Path | None = None,
             include_internal_ids: bool = False) -> dict[str, Any]:
    initialize(database_path)
    clause = "WHERE opportunity_id=?" if opportunity_id else ""
    params: tuple = (opportunity_id,) if opportunity_id else ()
    with _connect(database_path, readonly=True) as con:
        rows = [dict(r) for r in con.execute(
            f"SELECT opportunity_id,winning_hook,winning_format,ctr,conversion_rate,what_worked,what_failed,"
            f"lessons_learned,created_at FROM creative_feedback {clause} ORDER BY created_at DESC LIMIT ?",
            (*params, max(1, min(int(limit), 200))))]
    return {"status": "OK", "items": _public(rows, include_internal_ids=include_internal_ids), "count": len(rows)}


def nova_summary(opportunity_id: str = "", creative_request_id: str = "", *,
                 database_path: str | Path | None = None,
                 include_internal_ids: bool = False) -> dict[str, Any]:
    result = get_creative(opportunity_id, creative_request_id, database_path=database_path, include_internal_ids=True)
    if result["status"] != "OK":
        return result
    c = result["creative"]
    assets = c["ASSETS"]
    ready = [a for a in assets if a["MARKETING_HANDOFF_READY"]]
    pending_approval = [a for a in assets if a["APPROVAL_REQUIRED"]]
    revision = [a for a in assets if a["STATUS"] == "REVISION_REQUIRED"]
    next_action = ("HANDOFF_READY_ASSETS_TO_MARKETING" if ready and not revision
                   else "RESOLVE_REVISIONS" if revision
                   else "REQUEST_RAY_APPROVAL_FOR_MEDIA_GENERATION" if pending_approval else "AWAIT_BRIEF")
    summary = {
        "OPPORTUNITY_ID": c["OPPORTUNITY_ID"], "CAMPAIGN_ID": c["CAMPAIGN_ID"],
        "CHANNEL": c["CHANNEL"], "STATUS": c["STATUS"], "TOTAL_ASSETS": len(assets),
        "READY_FOR_MARKETING": len(ready),
        "WAITING_FOR_APPROVAL": [a["ASSET_TYPE"] for a in pending_approval],
        "NEEDS_REVISION": [a["ASSET_TYPE"] for a in revision],
        "ASSET_TYPES": [a["ASSET_TYPE"] for a in assets],
        "APPROVAL_REQUIRED": bool(pending_approval),
        "RECOMMENDED_NEXT_ACTION": next_action,
        "RULE": "CREATIVE CREATES; MARKETING DEPLOYS/MEASURES/OPTIMIZES. No publish, no spend here.",
    }
    return {"status": "OK", "nova_summary": _public(summary, include_internal_ids=include_internal_ids)}


def status(*, database_path: str | Path | None = None) -> dict[str, Any]:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        reqs = int(con.execute("SELECT count(*) FROM creative_requests").fetchone()[0])
        assets = int(con.execute("SELECT count(*) FROM creative_assets").fetchone()[0])
        by_status = {r[0]: r[1] for r in con.execute(
            "SELECT status,count(*) FROM creative_assets GROUP BY status")}
        ready = int(con.execute("SELECT count(*) FROM creative_assets WHERE marketing_handoff_ready=1").fetchone()[0])
        gated = int(con.execute("SELECT count(*) FROM creative_assets WHERE approval_required=1").fetchone()[0])
        fb = int(con.execute("SELECT count(*) FROM creative_feedback").fetchone()[0])
    return {"status": "OK", "engine_version": ENGINE_VERSION,
            "purpose": "MAKE_MARKETING_STRATEGY_EXECUTABLE_THROUGH_HIGH_QUALITY_ASSETS",
            "creative_requests": reqs, "assets": assets, "assets_by_status": by_status,
            "ready_for_marketing": ready, "approval_gated_assets": gated, "feedback_records": fb}


def list_creative(*, limit: int = 20, database_path: str | Path | None = None,
                  include_internal_ids: bool = False) -> dict[str, Any]:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        rows = [dict(r) for r in con.execute(
            "SELECT opportunity_id,creative_request_id,channel,status,updated_at FROM creative_requests "
            "ORDER BY updated_at DESC LIMIT ?", (max(1, min(int(limit), 100)),))]
    return {"status": "OK", "items": _public(rows, include_internal_ids=include_internal_ids), "count": len(rows)}


def health(*, database_path: str | Path | None = None) -> dict[str, Any]:
    db_path = _db_path(database_path)
    try:
        initialize(db_path)
        with _connect(db_path, readonly=True) as con:
            integrity = str(con.execute("PRAGMA quick_check").fetchone()[0])
            version = int(con.execute("PRAGMA user_version").fetchone()[0])
            reqs = int(con.execute("SELECT count(*) FROM creative_requests").fetchone()[0])
            assets = int(con.execute("SELECT count(*) FROM creative_assets").fetchone()[0])
    except (sqlite3.Error, OSError, RuntimeError) as exc:
        return {"status": "DEGRADED", "error_class": type(exc).__name__, "database_path": str(db_path)}
    mk_status = "UNKNOWN"
    try:
        from scripts.marketing import engine as marketing_engine
        mk_status = "AVAILABLE" if hasattr(marketing_engine, "creative_request") else "MISSING_CONTRACT"
    except Exception:
        mk_status = "UNAVAILABLE"
    return {"status": "PASS" if integrity == "ok" and version == SCHEMA_VERSION else "DEGRADED",
            "engine_version": ENGINE_VERSION, "sqlite_integrity": integrity, "schema_version": version,
            "creative_request_count": reqs, "asset_count": assets,
            "marketing_creative_request_contract": mk_status,
            "authority": {"LOCAL_SQLITE_IS_AUTHORITATIVE": "YES", "SUPABASE_IS_COORDINATION_LAYER": "YES",
                          "SUPABASE_IS_RAW_MEDIA_WAREHOUSE": "NO"},
            "database_path": str(db_path)}
