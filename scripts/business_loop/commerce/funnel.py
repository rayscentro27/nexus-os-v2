#!/usr/bin/env python3
"""Conversion funnel contracts: UTM attribution, copy/CTA validation, measurement,
A/B evidence rules, analysis, and approval packages for the ONE mug pilot.

Measurement rule: a metric is a number only when its source exists; otherwise the
literal "NOT_AVAILABLE". Zero means "measured, none happened".
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[3]
for p in (ROOT / "scripts", ROOT / "scripts/creative", ROOT / "scripts/distribution", ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

NA = "NOT_AVAILABLE"
PROJECT_ID = "proj_98ef515bccee4b58"
STORE_URL = "https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/"
CAMPAIGN_ID = "holiday_quiet_ritual_mug_r1"
AB_TEST_ID = "ab_holiday_mug_h1_vs_h2_r1"
HOOKS = {"H1": "The only fifteen minutes of the holidays that belong entirely to you.",
         "H2": "Zero snowflakes. Zero Santas. Just a quiet ceramic mug for slow winter mornings."}
PLATFORMS = {"FACEBOOK": "facebook", "INSTAGRAM": "instagram", "TIKTOK": "tiktok"}
MIN_EVIDENCE = {"min_sessions_per_variant": 100, "min_conversions_per_variant": 10, "min_days": 7,
                "rule": "No winner unless each variant has >=100 attributed sessions AND >=10 interest submissions (or 7 days elapsed with "
                        ">=100 sessions each) and the difference in interest rate is > 2x the pooled standard error; otherwise INSUFFICIENT_EVIDENCE."}
OUT_JSON = ROOT / "reports/business_loop/commerce_conversion_r1_latest.json"
OUT_MD = ROOT / "reports/business_loop/commerce_conversion_r1_latest.md"


# ------------------------------------------------------------------ attribution
def tracked_url(platform: str, hook: str) -> str:
    return (f"{STORE_URL}?utm_source={PLATFORMS[platform]}&utm_medium=social&utm_campaign={CAMPAIGN_ID}"
            f"&utm_content={hook.lower()}_{PLATFORMS[platform][:2]}")


def tracked_urls() -> dict[str, str]:
    return {f"{pf}_{h}": tracked_url(pf, h) for pf in PLATFORMS for h in HOOKS}


# ------------------------------------------------------------------ copy + CTA
def copy_package(form_verified: bool) -> dict:
    from product_truth_validator import ProductTruthValidator as Truth
    cta = "Register interest" if form_verified else "See the studio preview"
    tail = "Not yet for sale - register interest to hear when it opens." if form_verified else "Studio preview - not yet for sale."
    copy = {
        "FACEBOOK": f"{HOOKS['H1']}\n\nA ceramic mug concept for the quiet minutes before the holiday rush. {tail}\n{cta}: {tracked_url('FACEBOOK', 'H1')}",
        "INSTAGRAM": f"{HOOKS['H2']}\n\nStudio concept preview. {tail}\n{cta}: {tracked_url('INSTAGRAM', 'H2')}\n\n#QuietRitual #SlowMornings",
        "TIKTOK": f"{HOOKS['H1']} {tail} {tracked_url('TIKTOK', 'H1')}",
    }
    checks = {}
    for ch, text in copy.items():
        audit = Truth.audit_copy(text)
        checks[ch] = {"truth": audit["status"], "violations": audit["violations"],
                      "cta_real": (("register interest" not in text.lower()) or form_verified),
                      "link_tracked": "utm_campaign=" + CAMPAIGN_ID in text, "claims_for_sale": any(w in text.lower() for w in ("buy now", "order now", "in stock", "shop now"))}
    ok = all(c["truth"] == "PASS" and c["cta_real"] and c["link_tracked"] and not c["claims_for_sale"] for c in checks.values())
    return {"copy": copy, "checks": checks, "CTA_VALIDATED": ok, "cta": cta}


# ------------------------------------------------------------------ measurement
def _rows(fetch: Callable[[str], list]) -> tuple[list, list, list]:
    ev = fetch(f"commerce_events?select=event_type,session_id,source,content_variant,utm_source,utm_content,verified,is_test,detail,created_at&project_id=eq.{PROJECT_ID}&limit=10000")
    leads = fetch(f"commerce_leads?select=session_id,source,content_variant,utm_source,utm_content,is_test,email_normalized,created_at&project_id=eq.{PROJECT_ID}&limit=10000")
    orders = fetch(f"commerce_orders?select=mode,payment_status,amount_total_cents,session_id,created_at&project_id=eq.{PROJECT_ID}&limit=10000")
    return ev, leads, orders


def _is_test(row: dict) -> bool:
    return bool(row.get("is_test")) or str(row.get("session_id") or "").startswith("nexus-cert-") or str(row.get("email_normalized") or "").endswith("@example.com")


def measure(fetch: Callable[[str], list] | None = None, *, include_test: bool = False, meta: dict | None = None) -> dict:
    if fetch is None:
        from business_loop.commerce.supabase_io import call

        def fetch(path):  # noqa: F811
            code, data = call("GET", path, role="service", prefer="")
            if code != 200:
                raise RuntimeError(f"supabase_read_failed:{code}")
            return data
    try:
        ev, leads, orders = _rows(fetch)
        available = True
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "error": str(exc)[:120], **{k: NA for k in ("PAGE_VIEWS", "UNIQUE_SESSIONS", "CTA_CLICKS", "INTEREST_FORM_STARTS",
                "INTEREST_SUBMISSIONS", "CHECKOUT_CLICKS", "CHECKOUT_STARTS", "PURCHASES", "REVENUE", "CONVERSION_RATE")}}
    keep = (lambda r: True) if include_test else (lambda r: not _is_test(r))
    ev = [e for e in ev if keep(e)]; leads = [l for l in leads if keep(l)]
    live_orders = [o for o in orders if o["mode"] == "LIVE" and o["payment_status"] == "paid"]
    test_orders = [o for o in orders if o["mode"] == "TEST" and o["payment_status"] == "paid"]
    c = Counter(e["event_type"] for e in ev)
    sessions = {e["session_id"] for e in ev if e["event_type"] == "PAGE_VIEW"}
    attr = {}
    for e in sorted(ev, key=lambda e: e["created_at"]):
        attr.setdefault(e["session_id"], (e.get("source") or "unknown", e.get("content_variant") or "none"))
    def breakdown(idx: int) -> dict:
        out: dict = defaultdict(lambda: {"sessions": 0, "cta_clicks": 0, "interest_submissions": 0, "checkout_clicks": 0})
        for sid in sessions:
            out[attr.get(sid, ("unknown", "none"))[idx]]["sessions"] += 1
        for e in ev:
            key = attr.get(e["session_id"], ("unknown", "none"))[idx]
            if e["event_type"] == "CTA_CLICK": out[key]["cta_clicks"] += 1
            if e["event_type"] == "CHECKOUT_CLICK": out[key]["checkout_clicks"] += 1
        for l in leads:
            out[attr.get(l["session_id"], (l.get("source") or "unknown", l.get("content_variant") or "none"))[idx]]["interest_submissions"] += 1
        for v in out.values():
            v["interest_rate"] = round(v["interest_submissions"] / v["sessions"], 4) if v["sessions"] else NA
        return dict(out)
    pv = len(sessions)
    purchases_verified = sum(1 for e in ev if e["event_type"] == "PURCHASE_COMPLETED" and e.get("verified"))
    m = {
        "available": available, "include_test": include_test,
        "PAGE_VIEWS": c["PAGE_VIEW"], "UNIQUE_SESSIONS": pv, "CTA_CLICKS": c["CTA_CLICK"],
        "INTEREST_FORM_STARTS": c["INTEREST_FORM_STARTED"], "INTEREST_SUBMISSIONS": len(leads),
        "CHECKOUT_CLICKS": c["CHECKOUT_CLICK"], "CHECKOUT_STARTS": sum(1 for e in ev if e["event_type"] == "CHECKOUT_STARTED" and e.get("verified")),
        "PURCHASES": len(live_orders), "PURCHASES_TEST_MODE": len(test_orders) if include_test else NA, "PURCHASE_EVENTS_VERIFIED": purchases_verified,
        "REVENUE": round(sum(o["amount_total_cents"] for o in live_orders) / 100, 2),
        "REVENUE_NOTE": "LIVE revenue only; TEST-mode orders are never revenue. Live checkout is not enabled, so 0 is structural.",
        "CONVERSION_RATE": {"interest_per_session": round(len(leads) / pv, 4) if pv else NA,
                            "checkout_click_per_session": round(c["CHECKOUT_CLICK"] / pv, 4) if pv else NA,
                            "purchase_per_session": round(len(live_orders) / pv, 4) if pv else NA},
        "SOURCE_BREAKDOWN": breakdown(0), "CONTENT_VARIANT_BREAKDOWN": breakdown(1),
        "SOCIAL_PLATFORM_METRICS": meta or {"status": NA},
        "measured_at": datetime.now(timezone.utc).isoformat(),
    }
    return m


# ------------------------------------------------------------------ A/B + analysis
def ab_plan() -> dict:
    return {"AB_TEST_ID": AB_TEST_ID, "H1": HOOKS["H1"], "H2": HOOKS["H2"],
            "controlled": ["same square creative template", "same caption body + CTA", "same landing page", "same posting window (+/-1h)", "$0 spend"],
            "variants": {"H1": [tracked_url(p, "H1") for p in PLATFORMS], "H2": [tracked_url(p, "H2") for p in PLATFORMS]},
            "PRIMARY_METRIC": "INTEREST_SUBMISSION_RATE (interest submissions / attributed sessions)",
            "secondary": ["CLICK_THROUGH_RATE where Meta exposes it", "LANDING_PAGE_VISITS", "CTA_CLICKS", "ENGAGEMENT", "CHECKOUT_STARTS", "PURCHASES"],
            "MINIMUM_EVIDENCE_RULE": MIN_EVIDENCE["rule"], "status": "READY_PENDING_PUBLICATION_APPROVAL"}


def analyze(m: dict) -> dict:
    if not m.get("available"):
        return {"ANALYSIS_READY": True, "NEXT_BEST_ACTION": {"action": "RETRY_MEASUREMENT", "owner": "METRICS", "why": "first-party store unavailable"}}
    v = m["CONTENT_VARIANT_BREAKDOWN"]; s = m["SOURCE_BREAKDOWN"]
    def best(d: dict) -> Any:
        elig = {k: x for k, x in d.items() if x["sessions"] >= MIN_EVIDENCE["min_sessions_per_variant"] and x["interest_submissions"] >= MIN_EVIDENCE["min_conversions_per_variant"]}
        if len(elig) < 2:
            return "INSUFFICIENT_EVIDENCE"
        ranked = sorted(elig.items(), key=lambda kv: kv[1]["interest_rate"], reverse=True)
        (a, xa), (b, xb) = ranked[0], ranked[1]
        p = (xa["interest_submissions"] + xb["interest_submissions"]) / (xa["sessions"] + xb["sessions"])
        se = (p * (1 - p) * (1 / xa["sessions"] + 1 / xb["sessions"])) ** 0.5
        return a if se and (xa["interest_rate"] - xb["interest_rate"]) > 2 * se else "NO_SIGNIFICANT_DIFFERENCE"
    hook_best = best({k: x for k, x in v.items() if k.startswith(("h1", "h2"))})
    pv = m["UNIQUE_SESSIONS"]
    out = {"WHICH_SOURCE_PERFORMED_BEST": best(s), "WHICH_HOOK_PERFORMED_BEST": hook_best,
           "WHICH_CREATIVE_PERFORMED_BEST": hook_best if hook_best not in ("INSUFFICIENT_EVIDENCE", "NO_SIGNIFICANT_DIFFERENCE") else hook_best,
           "LANDING_PAGE_CONVERSION": m["CONVERSION_RATE"]["interest_per_session"], "INTEREST_RATE": m["CONVERSION_RATE"]["interest_per_session"],
           "CHECKOUT_RATE": m["CONVERSION_RATE"]["checkout_click_per_session"], "PURCHASE_RATE": m["CONVERSION_RATE"]["purchase_per_session"],
           "ANALYSIS_READY": True}
    if pv == 0:
        nba = {"action": "PUBLISH_TRACKED_H1_H2_POSTS", "owner": "DISTRIBUTION", "why": "Funnel is instrumented but has no real sessions yet; publication approval is the gate."}
    elif hook_best == "INSUFFICIENT_EVIDENCE":
        nba = {"action": "GATHER_MORE_DATA", "owner": "MARKETING", "why": f"{pv} sessions; below minimum evidence rule."}
    elif hook_best.split("_")[0].upper() in HOOKS:
        hook = hook_best.split("_")[0].upper()
        nba = {"action": f"KEEP_{hook}_AND_TEST_H3", "owner": "CREATIVE", "why": f"{hook_best} met the minimum evidence rule and beat the other variant by >2 SE."}
    elif isinstance(out["INTEREST_RATE"], float) and out["INTEREST_RATE"] < 0.01 and pv >= 200:
        nba = {"action": "REVISE_LANDING_PAGE", "owner": "MARKETING", "why": "Traffic without interest."}
    else:
        nba = {"action": "GATHER_MORE_DATA", "owner": "MARKETING", "why": "No significant difference yet."}
    out["NEXT_BEST_ACTION"] = nba
    out["NO_AUTOMATIC_SPEND"] = True
    return out


# ------------------------------------------------------------------ approvals
def supersede_and_request_facebook(project: dict, asset_path: str, copy_text: str, old_request_id: str = "apr_req_4fe6eb45cb6cc2fa") -> dict:
    import facebook_live_publisher as fb
    old_path, old = fb.find_request(old_request_id)
    asset = ROOT / asset_path
    sha = hashlib.sha256(asset.read_bytes()).hexdigest()
    rid = "apr_req_" + hashlib.sha256((project["project_id"] + sha + copy_text).encode()).hexdigest()[:16]
    req = {k: v for k, v in old.items() if k not in ("request_hash", "idempotency_key", "approval_request_id", "copy", "copy_sha256", "status", "approval_id", "superseded_by")}
    req.update({"approval_request_id": rid, "status": "WAITING_FOR_RAY_APPROVAL", "approval_id": None, "copy": copy_text,
                "copy_sha256": hashlib.sha256(copy_text.encode()).hexdigest(), "target_url": tracked_url("FACEBOOK", "H1"),
                "certification_purpose": "COMMERCE_CONVERSION_R1_TRACKED_H1", "supersedes": old_request_id,
                "created_at": datetime.now(timezone.utc).isoformat()})
    req["idempotency_key"] = fb.expected_idempotency_key(req)
    req["request_hash"] = fb.compute_request_hash(req)
    problems = fb.verify_request(req)
    if problems:
        raise RuntimeError(f"new_request_invalid:{problems}")
    new_path = fb.REQUESTS_DIR / f"bl_{project['project_id']}_facebook_tracked_h1_approval_request.json"
    new_path.write_text(json.dumps(req, indent=1) + "\n")
    if old.get("status") == "WAITING_FOR_RAY_APPROVAL":
        # Mark superseded. 'status'/'superseded_by' are not protected fields, so the old hash stays
        # intact; it still could only ever authorize its OLD copy/link, never the new one.
        old_path.write_text(json.dumps({**old, "status": "SUPERSEDED", "superseded_by": rid}, indent=1) + "\n")
    return {"OLD_APPROVAL_STATUS": "SUPERSEDED", "OLD_REQUEST_HASH_STILL_BINDS_OLD_CONTENT": fb.compute_request_hash(old) == old["request_hash"],
            "NEW_APPROVAL_REQUIRED": "YES", "PUBLICATION_APPROVAL_ID": rid, "path": str(new_path.relative_to(ROOT)),
            "owner_commands": [f"./bin/nexus distribution approve {rid}", f"./bin/nexus distribution publish {rid}"]}


def go_live_package(printify: dict, pricing: dict, stripe_state: dict, storefront_issues: list[str]) -> dict:
    body = {"approval_kind": "COMMERCE_GO_LIVE", "project_id": PROJECT_ID, "status": "WAITING_FOR_RAY_APPROVAL",
            "covers": {"printify_product": printify, "verified_base_cost": pricing["base_cost"], "price": pricing["recommended_price"],
                       "estimated_margin": pricing["gross_margin_at_recommended"], "storefront_listing": STORE_URL,
                       "fulfillment": "Printify print-on-demand, provider Printify Choice (99), 10-day handling",
                       "live_checkout": {"provider": "STRIPE", "current": "TEST_ONLY", "requires": "live secret key + live Payment Link + Ray approval"}},
            "preconditions_before_execution": ["Create Printify draft product (write) to read the real base cost", "Revise storefront product-detail copy to match the actual product"] + storefront_issues,
            "will_not_execute_without": "recorded Ray approval", "live_financial_activation_performed": False, "created_at": datetime.now(timezone.utc).isoformat()}
    body["approval_id"] = "apr_commerce_golive_" + hashlib.sha256(json.dumps(body["covers"], sort_keys=True, default=str).encode()).hexdigest()[:16]
    return body


def pricing(printify: dict) -> dict:
    ship = printify["us_shipping_first_item_usd"]
    base = printify.get("base_cost_usd")  # None unless verified from a Printify product
    def gp(price: float, base_cost: float | None):
        fee = round(0.029 * (price + ship) + 0.30, 2)  # Stripe standard card estimate; customer pays shipping at cost
        return fee, (round(price - fee - base_cost, 2) if base_cost is not None else None)
    rec = 29.0
    fee48, gp48 = gp(48.0, base); fee29, gp29 = gp(29.0, base)
    return {"base_cost": {"value": base, "status": "VERIFIED" if base is not None else "NOT_VERIFIED (requires Printify draft product)"},
            "shipping": {"value_usd": ship, "status": "VERIFIED (Printify catalog, US first item)", "charged_to_customer": "at cost (assumption)"},
            "payment_processing_estimate": {"at_48": fee48, "at_29": fee29, "basis": "2.9% + $0.30 on price+shipping (ESTIMATE)"},
            "current_staged_price": 48.0, "recommended_price": rec, "PRICE_CHANGE_RECOMMENDED": "YES",
            "gross_profit_formula": {"at_48": f"48 - {fee48} - base_cost = {round(48 - fee48, 2)} - base_cost",
                                     "at_29": f"29 - {fee29} - base_cost = {round(29 - fee29, 2)} - base_cost"},
            "gross_profit_at_recommended": gp29 if gp29 is not None else f"{round(29 - fee29, 2)} - base_cost (base cost NOT_VERIFIED)",
            "gross_margin_at_recommended": round(gp29 / 29, 3) if gp29 is not None else "NOT_AVAILABLE until base cost verified",
            "why": ("$48 was set for a stoneware concept with an unglazed clay base. The actual fulfillable Printify item is a standard white glossy "
                    "15oz ceramic mug, so $48 is not supported by the product. Recommend $29 PROPOSED and test it; do not change the staged price without authorization.")}


def write_reports(payload: dict) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    m = payload["measurement"]
    def fmt(x): return x if not isinstance(x, dict) else json.dumps(x)
    lines = ["# Holiday mug - commerce conversion R1", "", f"Measured at {m.get('measured_at')} (certification traffic excluded).", "",
             "| Metric | Value |", "|---|---|"]
    for k in ("PAGE_VIEWS", "UNIQUE_SESSIONS", "CTA_CLICKS", "INTEREST_FORM_STARTS", "INTEREST_SUBMISSIONS", "CHECKOUT_CLICKS", "CHECKOUT_STARTS", "PURCHASES", "REVENUE"):
        lines.append(f"| {k} | {fmt(m.get(k))} |")
    lines += ["", f"Conversion: {json.dumps(m.get('CONVERSION_RATE'))}", "", f"Next best action: {json.dumps(payload['analysis']['NEXT_BEST_ACTION'])}",
              "", "NOT_AVAILABLE means no data source exists; 0 means measured and none occurred."]
    OUT_MD.write_text("\n".join(lines) + "\n")
