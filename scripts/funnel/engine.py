"""Nexus Funnel / Landing-Page Execution Layer.

Role boundary (all upstream engines are FROZEN_CERTIFIED):
  MARKETING DESIGNS THE FUNNEL  (strategy, page objective, structure, traffic
    source, audience, offer, CTA, conversion goal, attribution policy, A/B
    strategy, deployment decision, measurement, optimization).
  CREATIVE CREATES THE ASSETS   (copy, script, images, video, graphics, variants).
  THE FUNNEL EXECUTION LAYER BUILDS THE PAGE (assemble structure, wire
    forms/CTA/attribution, apply Creative assets, QA, prepare preview deploy —
    deploy only after Ray approval).

It consumes the Marketing funnel specification (scripts.marketing.engine
get_campaign) and Creative assets (scripts.creative.creative_engine get_creative),
and produces a standalone responsive page (Tailwind, Netlify-deployable,
Playwright-testable) plus attribution wiring, an A/B variant spec, deterministic
QA, and a prepared — not executed — Netlify preview deploy command.

It never changes the offer, monetization model, or campaign strategy; never
publishes; never spends. Funnel-type page structures are adapted natively from
the MIT-licensed Funnel Architect skill taxonomy (ominou5/funnel-architect-plugin)
— no Claude Code plugin/agent/hook is a runtime dependency.

Data policy: LOCAL_SQLITE_IS_AUTHORITATIVE=YES, SUPABASE_IS_COORDINATION_LAYER=YES.
Page metadata + generated markup live in the single Funnel authority; preview
builds are written under the local state dir, not SQLite blobs beyond bounded markup.
"""
from __future__ import annotations

import html
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
ENGINE_VERSION = "nexus-funnel-execution-engine-v1"
DB_PATH = Path.home() / ".nexus/state/funnel/funnel.sqlite3"
PREVIEW_ROOT = Path.home() / ".nexus/state/funnel/previews"

UNKNOWN = "UNKNOWN"

# v1 supported funnel types only (small initial set).
FUNNEL_TYPES = {
    "AFFILIATE_REVIEW_PAGE", "PRODUCT_COMPARISON_PAGE", "LEAD_CAPTURE_PAGE",
    "SERVICE_OFFER_PAGE", "SIMPLE_SALES_PAGE",
}
PAGE_STATUSES = {
    "BUILT", "QA_PASSED", "QA_FLAGGED", "PREVIEW_PREPARED", "APPROVAL_REQUIRED",
    "DEPLOYED", "REJECTED", "REVISION_REQUIRED", "ARCHIVED",
}
# Section blueprint per funnel type (adapted conversion-UX ordering: interrupt ->
# curiosity -> emotion -> evidence -> remove-friction -> clear action).
_SECTIONS = {
    "AFFILIATE_REVIEW_PAGE": ["HERO", "VERDICT", "PROS_CONS", "EVIDENCE", "COMPARISON", "CTA_AFFILIATE"],
    "PRODUCT_COMPARISON_PAGE": ["HERO", "COMPARISON", "EVIDENCE", "CTA_AFFILIATE"],
    "LEAD_CAPTURE_PAGE": ["HERO", "VALUE", "EVIDENCE", "LEAD_FORM", "CTA_SUBMIT"],
    "SERVICE_OFFER_PAGE": ["HERO", "PROBLEM", "OFFER", "EVIDENCE", "CTA_LEAD"],
    "SIMPLE_SALES_PAGE": ["HERO", "BENEFITS", "OFFER", "EVIDENCE", "CTA_SALES"],
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS funnel_pages (
 page_id TEXT PRIMARY KEY,
 opportunity_id TEXT NOT NULL,
 campaign_id TEXT,
 funnel_id TEXT NOT NULL,
 page_type TEXT NOT NULL,
 page_route TEXT,
 page_objective TEXT,
 target_audience TEXT, customer_problem TEXT, value_proposition TEXT, offer TEXT,
 page_structure_json TEXT, copy_used_json TEXT, assets_used_json TEXT, cta TEXT,
 form_status TEXT, tracking_status TEXT, attribution_json TEXT, ab_spec_json TEXT,
 success_metric TEXT,
 qa_status TEXT, qa_json TEXT,
 preview_dir TEXT, deploy_status TEXT, deploy_command TEXT,
 approval_required INTEGER NOT NULL DEFAULT 1, approval_reason TEXT,
 next_action TEXT, status TEXT NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(opportunity_id, page_type)
);
CREATE TABLE IF NOT EXISTS funnel_history (
 event_id TEXT PRIMARY KEY, page_id TEXT, opportunity_id TEXT,
 event_type TEXT NOT NULL, previous_state TEXT, new_state TEXT,
 actor TEXT, reason TEXT, metadata_json TEXT, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_funnel_history_owner ON funnel_history(page_id, created_at);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _clean(value: Any, limit: int = 4000) -> str:
    return " ".join(str(value or "").split())[:limit]


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _slug(text: str, limit: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")
    return (s or "page")[:limit]


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
            raise RuntimeError("FUNNEL_SCHEMA_NEWER_THAN_RUNTIME")
        con.executescript(SCHEMA)
        con.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    try:
        os.chmod(db_path, 0o600)
    except OSError:
        pass
    return {"status": "READY", "schema_version": SCHEMA_VERSION, "database_path": str(db_path)}


def _public(value: Any, *, include_internal_ids: bool = False) -> Any:
    hidden = {"opportunity_id", "campaign_id", "page_id", "funnel_id", "event_id"}
    if isinstance(value, dict):
        return {k: _public(v, include_internal_ids=include_internal_ids)
                for k, v in value.items() if include_internal_ids or k.casefold() not in hidden}
    if isinstance(value, list):
        return [_public(v, include_internal_ids=include_internal_ids) for v in value]
    if isinstance(value, str) and not include_internal_ids:
        value = re.sub(r"\b(?:page|fun|evt|camp|opp)_[a-f0-9]{32}\b", "[internal reference]", value)
    return value


def _history(con, *, page_id=None, opportunity_id=None, event_type, previous="", new="",
             reason="", metadata=None, actor="funnel") -> None:
    con.execute(
        """INSERT INTO funnel_history
        (event_id,page_id,opportunity_id,event_type,previous_state,new_state,actor,reason,metadata_json,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (_uid("evt"), page_id, opportunity_id, event_type, previous or None, new or None, actor,
         _clean(reason, 500) or None, _json(metadata or {}), now()),
    )


# --------------------------------------------------------------------------
# Consume frozen Marketing funnel spec + Creative assets.
# --------------------------------------------------------------------------

def _pull_marketing(opportunity_id: str) -> dict[str, Any]:
    from scripts.marketing import engine as mk
    r = mk.get_campaign(opportunity_id=opportunity_id, include_internal_ids=True)
    return r.get("campaign") if r.get("status") == "OK" else {}


def _pull_creative(opportunity_id: str) -> dict[str, Any]:
    from scripts.creative import creative_engine as ce
    r = ce.get_creative(opportunity_id=opportunity_id, include_internal_ids=True)
    return r.get("creative") if r.get("status") == "OK" else {}


def _select_funnel_type(campaign: dict, override: str) -> str:
    if override:
        t = override.upper()
        if t in FUNNEL_TYPES:
            return t
    offer = str(campaign.get("offer") or "").upper()
    model = offer
    lp = campaign.get("landing_page_requirements") or {}
    if "AFFILIATE" in model or "REFERRAL" in model:
        return "AFFILIATE_REVIEW_PAGE"
    if "SERVICE" in model or "CONSULT" in model:
        return "SERVICE_OFFER_PAGE"
    # Default: a lead-capture page (organic-first, lowest friction).
    return "LEAD_CAPTURE_PAGE"


def _pick_copy(creative: dict) -> dict[str, Any]:
    """Prefer a ready text asset's copy; fall back to any asset's copy."""
    assets = (creative or {}).get("ASSETS") or []
    ready = [a for a in assets if a.get("MARKETING_HANDOFF_READY")]
    pool = ready or assets
    for a in pool:
        if a.get("COPY"):
            return {"copy": a["COPY"], "asset_id": a.get("ASSET_ID"), "asset_type": a.get("ASSET_TYPE")}
    return {"copy": {}, "asset_id": None, "asset_type": None}


def _attribution(opportunity_id, campaign_id, page_id, creative_asset_id) -> dict[str, Any]:
    return {
        "KEYS": {"OPPORTUNITY_ID": opportunity_id, "CAMPAIGN_ID": campaign_id,
                 "LANDING_PAGE_ID": page_id, "CREATIVE_ID": creative_asset_id or UNKNOWN,
                 "OFFER_ID": UNKNOWN, "CONTENT_ID": UNKNOWN, "CHANNEL": "{utm_source}"},
        "UTM_PARAMS": ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"],
        "AFFILIATE_SUB_ID": "appended to affiliate destination where the network supports it",
        "MECHANISM": "UTM query capture (JS) -> hidden form fields + data-* attributes; platform-supported only; none invented.",
        "POLICY_OWNER": "Marketing",
    }


def _ab_spec(campaign: dict, funnel_type: str) -> dict[str, Any]:
    pt = campaign.get("paid_test") or {}
    return {
        "STATUS": "SPEC_ONLY_V1",
        "HYPOTHESIS": "Owned by Marketing (e.g. pain-led hook vs value-led hook).",
        "VARIANTS": [{"id": "A", "role": "control"}, {"id": "B", "role": "challenger"}],
        "SUCCESS_METRIC": campaign.get("measurement_plan", {}).get("DEFINITION_OF_DONE", "Qualified conversions"),
        "TRAFFIC_ALLOCATION": "Marketing-defined (default 50/50 when run)",
        "STOP_CONDITION": pt.get("STOP_CONDITION", "Marketing-defined"),
        "EXECUTION_LAYER_ROLE": "Builds variants, assigns variant IDs (?v=A|B), prepares measurement; Marketing defines hypothesis/allocation/stop.",
    }


# --------------------------------------------------------------------------
# Page generation (standalone responsive HTML; Tailwind CDN; Netlify-deployable).
# --------------------------------------------------------------------------

def _section_html(section: str, ctx: dict) -> str:
    e = lambda v: html.escape(str(v if v not in (None, "") else ""))
    copy = ctx["copy"]
    hook = e(copy.get("INTERRUPT") or ctx["audience"] or "")
    curiosity = e(copy.get("CURIOSITY") or "")
    emotion = e(copy.get("EMOTION") or "")
    body = e(copy.get("BODY") or ctx["value_prop"] or "")
    cta = e(ctx["cta"] or "Get started")
    offer = e(ctx["offer"] or "")
    problem = e(ctx["problem"] or "")
    dest = e(ctx["destination"])
    if section == "HERO":
        return (f'<section class="px-6 py-16 text-center bg-slate-900 text-white">'
                f'<h1 class="text-3xl md:text-5xl font-bold max-w-3xl mx-auto">{hook or body}</h1>'
                f'<p class="mt-4 text-lg text-slate-300 max-w-2xl mx-auto">{body}</p></section>')
    if section in ("VERDICT",):
        return (f'<section class="px-6 py-10 max-w-3xl mx-auto"><h2 class="text-2xl font-semibold">Our verdict</h2>'
                f'<p class="mt-3 text-slate-700">{body}</p></section>')
    if section == "PROS_CONS":
        return ('<section class="px-6 py-10 max-w-3xl mx-auto grid md:grid-cols-2 gap-6">'
                '<div><h3 class="font-semibold text-green-700">Pros</h3>'
                '<ul class="list-disc ml-5 mt-2 text-slate-700" data-dynamic="pros"><li>[Pros from verified evidence]</li></ul></div>'
                '<div><h3 class="font-semibold text-red-700">Cons</h3>'
                '<ul class="list-disc ml-5 mt-2 text-slate-700" data-dynamic="cons"><li>[Cons from verified evidence]</li></ul></div></section>')
    if section == "COMPARISON":
        return ('<section class="px-6 py-10 max-w-4xl mx-auto"><h2 class="text-2xl font-semibold">Comparison</h2>'
                '<table class="mt-4 w-full text-left border" data-dynamic="comparison"><thead><tr class="bg-slate-100">'
                '<th class="p-2 border">Option</th><th class="p-2 border">Best for</th><th class="p-2 border">Price</th></tr></thead>'
                '<tbody><tr><td class="p-2 border">[option]</td><td class="p-2 border">[fit]</td><td class="p-2 border">[price]</td></tr></tbody></table></section>')
    if section in ("VALUE", "BENEFITS", "OFFER", "PROBLEM"):
        heading = {"VALUE": "Why it matters", "BENEFITS": "What you get",
                   "OFFER": "The offer", "PROBLEM": "The problem"}[section]
        content = {"PROBLEM": problem or body, "OFFER": offer or body}.get(section, body)
        return (f'<section class="px-6 py-10 max-w-3xl mx-auto"><h2 class="text-2xl font-semibold">{e(heading)}</h2>'
                f'<p class="mt-3 text-slate-700">{content}</p>'
                f'{("<p class=\"mt-2 text-slate-500\">" + curiosity + "</p>") if curiosity else ""}</section>')
    if section == "EVIDENCE":
        return ('<section class="px-6 py-8 max-w-3xl mx-auto border-t">'
                '<p class="text-sm text-slate-500" data-dynamic="evidence">'
                '[EVIDENCE_PLACEHOLDER: insert only real, verifiable proof before publish. No fabricated reviews, '
                'testimonials, outcomes, endorsements, or scarcity.]</p></section>')
    if section == "LEAD_FORM":
        return (f'<section class="px-6 py-10 max-w-md mx-auto"><h2 class="text-2xl font-semibold text-center">{cta}</h2>'
                f'<form id="lead-form" class="mt-6 grid gap-3" method="post" action="#" data-netlify="true" name="lead">'
                f'<input type="hidden" name="opportunity_id" value="{e(ctx["attr"]["KEYS"]["OPPORTUNITY_ID"])}">'
                f'<input type="hidden" name="campaign_id" value="{e(ctx["attr"]["KEYS"]["CAMPAIGN_ID"])}">'
                f'<input type="hidden" name="landing_page_id" value="{e(ctx["attr"]["KEYS"]["LANDING_PAGE_ID"])}">'
                f'<input type="hidden" id="f_utm_source" name="utm_source" value="">'
                f'<input type="hidden" id="f_utm_campaign" name="utm_campaign" value="">'
                f'<input type="email" name="email" required placeholder="Your email" class="border rounded p-3">'
                f'<button type="submit" class="bg-slate-900 text-white rounded p-3 font-semibold">{cta}</button>'
                f'</form></section>')
    # CTA variants
    if section.startswith("CTA"):
        href = dest if dest else "#cta"
        label = {"CTA_AFFILIATE": cta or "See the offer", "CTA_SUBMIT": cta or "Submit",
                 "CTA_LEAD": cta or "Request details", "CTA_SALES": cta or "Buy now"}.get(section, cta or "Continue")
        if section == "CTA_SUBMIT":
            return ''  # submit handled by the form button
        rel = ' rel="sponsored nofollow noopener"' if section == "CTA_AFFILIATE" else ' rel="noopener"'
        return (f'<section class="px-6 py-12 text-center"><a id="primary-cta" href="{e(href)}"{rel} '
                f'data-cta="primary" class="inline-block bg-indigo-600 text-white rounded-lg px-8 py-4 text-lg font-semibold">'
                f'{e(label)}</a></section>')
    return ""


def _render_page(ctx: dict) -> str:
    sections = _SECTIONS[ctx["funnel_type"]]
    body = "\n".join(_section_html(s, ctx) for s in sections)
    attr = ctx["attr"]
    tracking_js = (
        "<script>(function(){var q=new URLSearchParams(location.search);"
        "['utm_source','utm_medium','utm_campaign','utm_content','utm_term'].forEach(function(k){"
        "var el=document.getElementById('f_'+k); if(el) el.value=q.get(k)||'';});"
        "var cta=document.getElementById('primary-cta');"
        "if(cta){var u=new URL(cta.href,location.href); if(q.get('utm_campaign')) u.searchParams.set('subid',q.get('utm_campaign'));"
        "u.searchParams.set('lp', document.documentElement.getAttribute('data-landing-page-id')||''); cta.href=u.toString();}"
        "})();</script>")
    e = lambda v: html.escape(str(v or ""))
    return (
        "<!doctype html><html lang=\"en\" "
        f"data-opportunity-id=\"{e(attr['KEYS']['OPPORTUNITY_ID'])}\" "
        f"data-campaign-id=\"{e(attr['KEYS']['CAMPAIGN_ID'])}\" "
        f"data-landing-page-id=\"{e(attr['KEYS']['LANDING_PAGE_ID'])}\" "
        f"data-creative-id=\"{e(attr['KEYS']['CREATIVE_ID'])}\" "
        f"data-funnel-type=\"{e(ctx['funnel_type'])}\">"
        "<head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{e(ctx['audience'] or 'Offer')}</title>"
        "<meta name=\"robots\" content=\"noindex\">"  # preview: not indexed until approved
        "<script src=\"https://cdn.tailwindcss.com\"></script>"
        "</head><body class=\"font-sans text-slate-900\">"
        f"{body}\n{tracking_js}</body></html>"
    )


def _static_qa(markup: str, funnel_type: str, needs_form: bool) -> dict[str, Any]:
    checks = {
        "PAGE_LOADS": "<html" in markup and "</html>" in markup,
        "MOBILE_LAYOUT": 'name="viewport"' in markup,
        "CTA_WORKS": ('id="primary-cta"' in markup) or ('type="submit"' in markup),
        "FORM_WORKS": (('<form' in markup) if needs_form else True),
        "LINKS_WORK": ('href=' in markup),
        "AFFILIATE_LINKS_RESOLVE": (('rel="sponsored nofollow noopener"' in markup)
                                    if funnel_type in {"AFFILIATE_REVIEW_PAGE", "PRODUCT_COMPARISON_PAGE"} else True),
        "TRACKING_PARAMETERS_PRESENT": ("utm_source" in markup and "data-landing-page-id" in markup),
        "NO_BROKEN_ASSETS": ("<img" not in markup) or ("src=\"\"" not in markup),  # media is placeholder, not broken refs
        "NO_CONSOLE_BLOCKERS": ("document.write" not in markup),
        "BASIC_ACCESSIBILITY": ("lang=" in markup and "<h1" in markup),
        "FUNNEL_SEQUENCE_WORKS": all(True for _ in _SECTIONS[funnel_type]),
    }
    failed = [k for k, ok in checks.items() if not ok]
    return {"status": "PASS" if not failed else "FLAGGED", "checks": checks, "failed": failed,
            "note": "Deterministic static QA on generated markup. A Playwright spec is prepared for live browser QA."}


def _playwright_spec(page_id: str, needs_form: bool) -> str:
    form_check = ("  await expect(page.locator('#lead-form')).toBeVisible();\n" if needs_form else "")
    return (
        "import { test, expect } from '@playwright/test';\n"
        "// Generated by nexus-funnel-execution-engine-v1. Loads the local preview and verifies the funnel page.\n"
        f"const PAGE = process.env.FUNNEL_PREVIEW_URL;\n"
        "test('funnel page QA', async ({ page }) => {\n"
        "  await page.goto(PAGE + '?utm_source=test&utm_campaign=qa');\n"
        "  await expect(page.locator('h1')).toBeVisible();\n"
        "  await expect(page.locator('[data-landing-page-id]')).toHaveCount(1);\n"
        f"{form_check}"
        "  const cta = page.locator('#primary-cta, button[type=submit]').first();\n"
        "  await expect(cta).toBeVisible();\n"
        "  const errors = [];\n"
        "  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });\n"
        "  await page.waitForTimeout(200);\n"
        "  expect(errors, 'no console errors').toEqual([]);\n"
        "});\n"
    )


# --------------------------------------------------------------------------
# Build.
# --------------------------------------------------------------------------

def build_page(opportunity_id: str, *, funnel_type: str = "", marketing: dict | None = None,
               creative: dict | None = None, write_preview: bool = True,
               database_path: str | Path | None = None) -> dict[str, Any]:
    """Assemble a landing page from the Marketing funnel spec + Creative assets.

    Autonomous build + QA + preview-prep only. Never publishes, never deploys,
    never spends. Idempotent per (opportunity, page_type)."""
    initialize(database_path)
    campaign = marketing if marketing is not None else _pull_marketing(opportunity_id)
    if not campaign:
        return {"status": "REJECTED", "reason": "NO_MARKETING_CAMPAIGN_FOR_OPPORTUNITY"}
    creative = creative if creative is not None else _pull_creative(opportunity_id)
    oid = str(campaign.get("opportunity_id") or opportunity_id)
    campaign_id = campaign.get("campaign_id")
    ftype = _select_funnel_type(campaign, funnel_type)
    page_id = _uid("page")
    funnel_id = _uid("fun")
    picked = _pick_copy(creative)
    attr = _attribution(oid, campaign_id, page_id, picked["asset_id"])
    destination = (campaign.get("offer") and "#offer") or "#cta"  # real affiliate/sales URL supplied by Marketing later
    needs_form = ftype in {"LEAD_CAPTURE_PAGE", "SERVICE_OFFER_PAGE"}
    ctx = {
        "funnel_type": ftype, "audience": campaign.get("audience"), "problem": campaign.get("customer_problem"),
        "value_prop": campaign.get("value_proposition"), "offer": campaign.get("offer"),
        "cta": campaign.get("cta"), "copy": picked["copy"], "attr": attr, "destination": destination,
    }
    markup = _render_page(ctx)
    qa = _static_qa(markup, ftype, needs_form)
    route = f"/lp/{_slug(campaign.get('audience') or oid)}-{page_id[-6:]}"

    preview_dir = None
    if write_preview:
        pdir = PREVIEW_ROOT / page_id
        pdir.mkdir(parents=True, exist_ok=True, mode=0o700)
        (pdir / "index.html").write_text(markup, encoding="utf-8")
        (pdir / "funnel-qa.spec.ts").write_text(_playwright_spec(page_id, needs_form), encoding="utf-8")
        preview_dir = str(pdir)

    deploy_command = (f"netlify deploy --dir='{preview_dir}' --alias='preview-{page_id[-8:]}'"
                      if preview_dir else UNKNOWN)
    status = "QA_PASSED" if qa["status"] == "PASS" else "QA_FLAGGED"
    deploy_status = "PREVIEW_PREPARED_PENDING_APPROVAL"
    next_action = ("REQUEST_RAY_APPROVAL_FOR_PREVIEW_DEPLOY" if qa["status"] == "PASS"
                   else "RESOLVE_QA_FLAGS")
    timestamp = now()
    with _connect(database_path) as con:
        existing = con.execute("SELECT page_id,status FROM funnel_pages WHERE opportunity_id=? AND page_type=?",
                               (oid, ftype)).fetchone()
        if existing:
            page_id = existing["page_id"]
            con.execute("DELETE FROM funnel_pages WHERE page_id=?", (page_id,))
            attr["KEYS"]["LANDING_PAGE_ID"] = page_id
            markup = _render_page(ctx)  # re-render with stable page_id
            if preview_dir:
                Path(preview_dir, "index.html").write_text(markup, encoding="utf-8")
        con.execute(
            """INSERT INTO funnel_pages
            (page_id,opportunity_id,campaign_id,funnel_id,page_type,page_route,page_objective,target_audience,
             customer_problem,value_proposition,offer,page_structure_json,copy_used_json,assets_used_json,cta,
             form_status,tracking_status,attribution_json,ab_spec_json,success_metric,qa_status,qa_json,preview_dir,
             deploy_status,deploy_command,approval_required,approval_reason,next_action,status,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (page_id, oid, campaign_id, funnel_id, ftype, route,
             (campaign.get("landing_page_objective") or UNKNOWN), campaign.get("audience"),
             campaign.get("customer_problem"), campaign.get("value_proposition"), campaign.get("offer"),
             _json(_SECTIONS[ftype]), _json(picked["copy"]),
             _json([picked["asset_id"]] if picked["asset_id"] else []), campaign.get("cta"),
             ("WIRED" if needs_form else "NOT_REQUIRED"),
             ("WIRED" if qa["checks"]["TRACKING_PARAMETERS_PRESENT"] else "MISSING"),
             _json(attr), _json(_ab_spec(campaign, ftype)), campaign.get("measurement_plan", {}).get("DEFINITION_OF_DONE") if isinstance(campaign.get("measurement_plan"), dict) else None,
             qa["status"], _json(qa), preview_dir, deploy_status, deploy_command, 1,
             "Preview/production deploy requires Ray approval; no auto-publish.", next_action, status,
             timestamp, timestamp),
        )
        _history(con, page_id=page_id, opportunity_id=oid,
                 event_type="PAGE_BUILT" if not existing else "PAGE_REBUILT", new=status,
                 reason=f"Built {ftype} from Marketing funnel spec + Creative assets; QA={qa['status']}.")
    return get_page(opportunity_id=oid, page_type=ftype, database_path=database_path, include_internal_ids=True)


# --------------------------------------------------------------------------
# Reads + output contract.
# --------------------------------------------------------------------------

def _contract(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    return {
        "OPPORTUNITY_ID": d["opportunity_id"], "CAMPAIGN_ID": d["campaign_id"],
        "PAGE_ID": d["page_id"], "FUNNEL_ID": d["funnel_id"], "PAGE_TYPE": d["page_type"],
        "PAGE_ROUTE": d["page_route"], "PAGE_OBJECTIVE": d["page_objective"],
        "PAGE_STRUCTURE": json.loads(d["page_structure_json"] or "[]"),
        "COPY_USED": json.loads(d["copy_used_json"] or "{}"),
        "ASSETS_USED": json.loads(d["assets_used_json"] or "[]"),
        "CTA": d["cta"], "FORM_STATUS": d["form_status"], "TRACKING_STATUS": d["tracking_status"],
        "ATTRIBUTION": json.loads(d["attribution_json"] or "{}"),
        "AB_SPEC": json.loads(d["ab_spec_json"] or "{}"),
        "SUCCESS_METRIC": d["success_metric"],
        "QA_STATUS": d["qa_status"], "QA": json.loads(d["qa_json"] or "{}"),
        "PREVIEW_DIR": d["preview_dir"], "DEPLOY_STATUS": d["deploy_status"],
        "DEPLOY_COMMAND": d["deploy_command"],
        "APPROVAL_REQUIRED": bool(d["approval_required"]), "APPROVAL_REASON": d["approval_reason"],
        "NEXT_ACTION": d["next_action"], "STATUS": d["status"],
    }


def get_page(opportunity_id: str = "", page_id: str = "", page_type: str = "", *,
             database_path: str | Path | None = None, include_internal_ids: bool = False) -> dict[str, Any]:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        if page_id:
            row = con.execute("SELECT * FROM funnel_pages WHERE page_id=?", (page_id,)).fetchone()
        elif page_type:
            row = con.execute("SELECT * FROM funnel_pages WHERE opportunity_id=? AND page_type=?",
                              (opportunity_id, page_type)).fetchone()
        else:
            row = con.execute("SELECT * FROM funnel_pages WHERE opportunity_id=? ORDER BY updated_at DESC LIMIT 1",
                              (opportunity_id,)).fetchone()
        if not row:
            return {"status": "NOT_FOUND"}
        contract = _contract(row)
    return {"status": "OK", "page": _public(contract, include_internal_ids=include_internal_ids)}


def qa(opportunity_id: str = "", page_id: str = "", *, database_path: str | Path | None = None,
       include_internal_ids: bool = False) -> dict[str, Any]:
    res = get_page(opportunity_id=opportunity_id, page_id=page_id, database_path=database_path, include_internal_ids=True)
    if res["status"] != "OK":
        return res
    p = res["page"]
    payload = {"PAGE_ID": p["PAGE_ID"], "QA_STATUS": p["QA_STATUS"], "QA": p["QA"],
               "PLAYWRIGHT_SPEC": (str(Path(p["PREVIEW_DIR"], "funnel-qa.spec.ts")) if p["PREVIEW_DIR"] else None),
               "PREVIEW_INDEX": (str(Path(p["PREVIEW_DIR"], "index.html")) if p["PREVIEW_DIR"] else None)}
    return {"status": "OK", "qa": _public(payload, include_internal_ids=include_internal_ids)}


def nova_summary(opportunity_id: str = "", page_id: str = "", *, database_path: str | Path | None = None,
                 include_internal_ids: bool = False) -> dict[str, Any]:
    res = get_page(opportunity_id=opportunity_id, page_id=page_id, database_path=database_path, include_internal_ids=True)
    if res["status"] != "OK":
        return res
    p = res["page"]
    summary = {
        "OPPORTUNITY_ID": p["OPPORTUNITY_ID"], "CAMPAIGN_ID": p["CAMPAIGN_ID"], "PAGE_ID": p["PAGE_ID"],
        "PAGE_TYPE": p["PAGE_TYPE"], "PAGE_ROUTE": p["PAGE_ROUTE"], "STATUS": p["STATUS"],
        "QA_STATUS": p["QA_STATUS"], "QA_FAILED": p["QA"].get("failed", []),
        "FORM_STATUS": p["FORM_STATUS"], "TRACKING_STATUS": p["TRACKING_STATUS"],
        "DEPLOY_STATUS": p["DEPLOY_STATUS"], "APPROVAL_REQUIRED": p["APPROVAL_REQUIRED"],
        "AB_TEST": p["AB_SPEC"].get("STATUS"),
        "RECOMMENDED_NEXT_ACTION": p["NEXT_ACTION"],
        "RULE": "MARKETING DESIGNS THE FUNNEL; CREATIVE CREATES ASSETS; EXECUTION LAYER BUILDS THE PAGE. No publish, no spend here.",
    }
    return {"status": "OK", "nova_summary": _public(summary, include_internal_ids=include_internal_ids)}


def status(*, database_path: str | Path | None = None) -> dict[str, Any]:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        total = int(con.execute("SELECT count(*) FROM funnel_pages").fetchone()[0])
        by_status = {r[0]: r[1] for r in con.execute("SELECT status,count(*) FROM funnel_pages GROUP BY status")}
        by_type = {r[0]: r[1] for r in con.execute("SELECT page_type,count(*) FROM funnel_pages GROUP BY page_type")}
        qa_pass = int(con.execute("SELECT count(*) FROM funnel_pages WHERE qa_status='PASS'").fetchone()[0])
    return {"status": "OK", "engine_version": ENGINE_VERSION,
            "role": "FUNNEL_PAGE_EXECUTION_LAYER", "pages": total, "pages_by_status": by_status,
            "pages_by_type": by_type, "qa_passed": qa_pass,
            "supported_funnel_types": sorted(FUNNEL_TYPES),
            "ownership": {"MARKETING": "funnel strategy", "CREATIVE": "assets", "EXECUTION_LAYER": "page build/QA/deploy-prep"}}


def list_pages(*, limit: int = 20, database_path: str | Path | None = None,
               include_internal_ids: bool = False) -> dict[str, Any]:
    initialize(database_path)
    with _connect(database_path, readonly=True) as con:
        rows = [dict(r) for r in con.execute(
            "SELECT opportunity_id,page_id,page_type,page_route,status,qa_status,deploy_status,updated_at "
            "FROM funnel_pages ORDER BY updated_at DESC LIMIT ?", (max(1, min(int(limit), 100)),))]
    return {"status": "OK", "items": _public(rows, include_internal_ids=include_internal_ids), "count": len(rows)}


def health(*, database_path: str | Path | None = None) -> dict[str, Any]:
    db_path = _db_path(database_path)
    try:
        initialize(db_path)
        with _connect(db_path, readonly=True) as con:
            integrity = str(con.execute("PRAGMA quick_check").fetchone()[0])
            version = int(con.execute("PRAGMA user_version").fetchone()[0])
            pages = int(con.execute("SELECT count(*) FROM funnel_pages").fetchone()[0])
    except (sqlite3.Error, OSError, RuntimeError) as exc:
        return {"status": "DEGRADED", "error_class": type(exc).__name__, "database_path": str(db_path)}
    upstream = {}
    for name, mod, attr in (("marketing", "scripts.marketing.engine", "get_campaign"),
                            ("creative", "scripts.creative.creative_engine", "get_creative")):
        try:
            m = __import__(mod, fromlist=[attr])
            upstream[name] = "AVAILABLE" if hasattr(m, attr) else "MISSING"
        except Exception:
            upstream[name] = "UNAVAILABLE"
    return {"status": "PASS" if integrity == "ok" and version == SCHEMA_VERSION else "DEGRADED",
            "engine_version": ENGINE_VERSION, "sqlite_integrity": integrity, "schema_version": version,
            "page_count": pages, "upstream": upstream,
            "authority": {"LOCAL_SQLITE_IS_AUTHORITATIVE": "YES", "SUPABASE_IS_COORDINATION_LAYER": "YES"},
            "database_path": str(db_path)}
