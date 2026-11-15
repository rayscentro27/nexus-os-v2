"""Department engines for Business Loop R1 (thin adapters over existing Nexus assets).

Each engine consumes the previous structured handoff and returns
``{"output", "artifacts", "issues", "cost"}``. Engines never spend money and
never publish; approval-gated actions are emitted as approval requests.
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT  # fixed repo root for recorded paths (ROOT may be redirected for output in tests)
for p in (ROOT / "scripts", ROOT / "scripts/creative", ROOT / "scripts/distribution", ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

MANIFEST = ROOT / "dist/creative/campaign_holiday_ceramic_mug_manifest.json"
DEPLOY_RECEIPT = ROOT / "dist/creative/holiday_campaign_deployment_receipt.json"
HERO_JPG = ROOT / "dist/creative/meta_holiday_ceramic_mug_1794355016_facebook.jpg"
HERO_SOURCE = ROOT / "dist/creative/meta_holiday_ceramic_mug_1794355016.webp"
PUBLISH_RECEIPTS = ROOT / "data/governed/distribution_publish_receipts.jsonl"
ZERO_COST = {"ai_model": 0.0, "media": 0.0, "platform": 0.0, "ad_spend": 0.0, "other": 0.0}


class DepartmentFailure(RuntimeError):
    """Recoverable department failure: routed, never project-terminating."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}")
        self.code, self.detail = code, detail


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> dict:
    return json.loads(path.read_text())


def _rel(p: Path) -> str:
    return str(p.relative_to(REPO)) if p.is_relative_to(REPO) else str(p)


def _ssl_context():
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def http_status(url: str, timeout: int = 20) -> int | None:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET", headers={"User-Agent": "Nexus-BusinessLoop/1.0"}),
                                    timeout=timeout, context=_ssl_context()) as r:
            return r.status
    except Exception:  # noqa: BLE001
        return None


# ===================================================================== RESEARCH
def research(project: dict, *, landing_check: Callable[[str], int | None] = http_status) -> dict:
    m = _json(MANIFEST)
    bo, ms, cp = m["business_objective"], m["marketing_strategy"], m["commerce_package"]
    receipts = [json.loads(l) for l in PUBLISH_RECEIPTS.read_text().splitlines() if l.strip()] if PUBLISH_RECEIPTS.exists() else []
    camp = [r for r in receipts if r.get("campaign_id") == m["campaign_id"]]
    landing_url = m["public_test_url"]
    landing_http = landing_check(landing_url)
    facts = m["product_fact_register"]
    evidence = [
        {"ref": _rel(MANIFEST), "sha256": sha256(MANIFEST), "kind": "PILOT_OPPORTUNITY_RECORD", "grade": "INTERNAL_HYPOTHESIS",
         "content": "customer insight, problem/desire, seasonal context, proposed offer (Section 31B pilot)"},
        {"ref": "data/governed/distribution_publish_receipts.jsonl", "kind": "REAL_MARKET_EXPOSURE", "grade": "OBSERVED_FACT",
         "content": [{"platform": r["platform"], "published_at": r.get("published_at"), "id": r.get("meta_post_id") or r.get("instagram_media_id"),
                      "url": r.get("public_post_url") or r.get("permalink")} for r in camp]},
        {"ref": _rel(DEPLOY_RECEIPT), "kind": "STOREFRONT_AVAILABILITY", "grade": "OBSERVED_FACT",
         "content": {"url": landing_url, "http_now": landing_http}},
        {"ref": "product_fact_register", "kind": "PRODUCT_TRUTH", "grade": "OBSERVED_FACT",
         "content": {"verified_claims": facts["verified_claims_count"], "unverified": facts["unverified_claims_count"]}},
    ]
    observed_demand = False  # no conversion/order/waitlist evidence exists in current records
    sufficiency = "SUFFICIENT_FOR_NO_SPEND_VALIDATION" if camp and landing_http == 200 else "INSUFFICIENT"
    if sufficiency == "INSUFFICIENT":
        raise DepartmentFailure("NOT_ENOUGH_EVIDENCE", "no real exposure receipts or storefront unreachable")
    handoff = {
        "OPPORTUNITY_SUMMARY": bo["summary"],
        "EVIDENCE": evidence,
        "EVIDENCE_SUFFICIENCY": sufficiency,
        "DEMAND_EVIDENCE": "NONE_OBSERVED_YET" if not observed_demand else "OBSERVED",
        "TARGET_CUSTOMER": bo["target_customer"],
        "CUSTOMER_PAIN_OR_DESIRE": {"pain": bo["customer_problem"], "desire": bo["customer_desire"]},
        "PRODUCT_IDEA": bo["lead_product_concept"],
        "PRICE_RANGE_OR_MONETIZATION": {"proposed_retail_usd": cp["proposed_retail_price_usd"], "estimated_cogs_usd": cp["estimated_cogs_usd"],
                                        "status": "PROPOSED/ESTIMATED (supplier not selected)", "model": "print-on-demand direct sale, no inventory"},
        "COMPETITOR_CONTEXT": {"stated": "Mass-market holiday novelty mugs (thin, decal-printed, seasonal).", "grade": "ASSUMPTION",
                               "gap": "No competitor price/positioning scan in current evidence."},
        "SEASONAL_CONTEXT": {"window": bo["seasonal_context"], "as_of": project["created_at"][:10],
                             "note": "~5-6 weeks to Dec 25; print-on-demand production+shipping lead time is unverified and bounds the sell window."},
        "CHANNEL_OPPORTUNITIES": [
            {"channel": "Owned storefront (Cloudflare Pages test)", "status": "LIVE_TEST" if landing_http == 200 else "UNREACHABLE", "url": landing_url},
            {"channel": "Facebook Raytestpage", "status": "CERTIFIED_PUBLISH_PATH (approval-gated)"},
            {"channel": "Instagram @the612amritual", "status": "CERTIFIED_PUBLISH_PATH (approval-gated)"},
            {"channel": "TikTok sandbox nexusaiwealth", "status": "AUTH_REQUIRED"},
        ],
        "RISKS": ["No verified product specs (0 verified claims) -> copy must stay concept-level.",
                  "No live checkout -> demand can only be measured as intent (clicks/waitlist), not orders.",
                  "Holiday window may close before supplier+fulfillment are established.",
                  "Test-page audiences (Raytestpage, new IG) are tiny; metrics will be low-n."],
        "ASSUMPTIONS": ["Design-conscious 28-48 buyers prefer non-novelty ceramic gifts.", "$48 is acceptable for a premium ritual mug.",
                        "Printify can fulfil a comparable ceramic mug at <= ~$16.50 COGS."],
        "QUESTIONS_TO_VALIDATE": ["Does organic content produce landing-page clicks?", "Which hook earns the most engagement per reach?",
                                  "What is the real Printify COGS + ship time for a comparable mug?", "Will anyone register intent at $48?"],
        "MARKETING_DIRECTIVES": ["Measure intent at $0 spend; no demand claims.", "Test >= 3 hooks against the same visual.",
                                 "Every post must carry the storefront URL as plain text (no bio link exists)."],
        "CREATIVE_DIRECTIVES": ["Reuse the certified hero visual for consistency.", "Produce square + vertical + link-card formats.",
                                "All copy must PASS the product truth validator."],
        "COMMERCE_DIRECTIVES": ["Stage one offer on the owned storefront; no checkout until supplier + fulfillment verified and approved.",
                                "Record price as PROPOSED and COGS as ESTIMATED until Printify data is captured."],
    }
    return {"output": handoff, "artifacts": [e["ref"] for e in evidence], "issues": [], "cost": dict(ZERO_COST)}


# ==================================================================== MARKETING
def marketing(project: dict, research_handoff: dict, *, ai_provider: Callable[[dict], dict] | None = None) -> dict:
    """Bounded campaign brief. AI enrichment is optional; deterministic composition is the governed fallback."""
    issues = []
    enrichment = None
    if ai_provider is not None:
        try:
            enrichment = ai_provider(research_handoff)
        except Exception as exc:  # noqa: BLE001 — provider failure is recoverable
            issues.append({"code": "AI_PROVIDER_UNAVAILABLE", "detail": type(exc).__name__, "recovery": "DETERMINISTIC_COMPOSER_FALLBACK"})
    else:
        issues.append({"code": "AI_PROVIDER_NOT_AUTHORIZED_FOR_SPEND", "detail": "no $0 model route configured for this loop",
                       "recovery": "DETERMINISTIC_COMPOSER_FROM_RESEARCH_HANDOFF"})
    m = _json(MANIFEST)
    url = m["public_test_url"]
    hooks = [
        {"id": "H1", "text": "The only fifteen minutes of the holidays that belong entirely to you.", "angle": "time/sanctuary"},
        {"id": "H2", "text": "Zero snowflakes. Zero Santas. Just a quiet ceramic mug for slow winter mornings.", "angle": "anti-novelty"},
        {"id": "H3", "text": "A gift for the person who is always up before everyone else.", "angle": "gift-giver"},
    ]
    brief = {
        "TARGET_AUDIENCE": research_handoff["TARGET_CUSTOMER"],
        "POSITIONING": "The counter-holiday gift: a calm, substantial ceramic mug for the quiet minutes before the house wakes.",
        "OFFER": "Studio concept preview of the 6:12 AM Ritual mug - register interest (proposed $48; not yet purchasable).",
        "CORE_MESSAGE": "Keep fifteen quiet minutes for yourself this season.",
        "CUSTOMER_PROMISE": "A grounding morning ritual object - not seasonal clutter.",
        "PROOF_SUPPORT": ["Design intent only (concept stage) - no performance or spec claims.", "Product truth validator enforced on all copy."],
        "PRIMARY_CHANNELS": ["Owned storefront", "Facebook Raytestpage", "Instagram @the612amritual"],
        "HOOKS": hooks,
        "CTA": "See the studio preview",
        "CONTENT_PLAN": [
            {"post": "P1", "format": "square photo (feed)", "hook": "H1", "channel": ["FACEBOOK", "INSTAGRAM"]},
            {"post": "P2", "format": "vertical 9:16 (stories/reels cover)", "hook": "H2", "channel": ["INSTAGRAM", "TIKTOK"]},
            {"post": "P3", "format": "1.91:1 link card", "hook": "H3", "channel": ["FACEBOOK"]},
        ],
        "SHORT_FORM_POST_CONCEPTS": [
            {"id": "S1", "concept": "6:12 AM - dark kitchen, single pour, steam; overlay H1.", "length_s": 7},
            {"id": "S2", "concept": "Side-by-side: novelty decal mug vs. plain ceramic; overlay H2 (no brand disparagement, no claims).", "length_s": 6},
            {"id": "S3", "concept": "Gift-tag reveal: 'for the early riser'; overlay H3.", "length_s": 6},
        ],
        "PROMOTIONAL_CONCEPT": "Early-Riser Preview: first 50 people to register interest get first notice when the studio edition opens (no discount promised).",
        "PRODUCT_PAGE_BRIEF": {"headline": "The 6:12 AM Ritual", "subhead": "A ceramic mug for the quiet minutes before the holiday rush.",
                               "sections": ["Why a ritual, not a novelty", "Design details (concept, unverified specs omitted)", "Register interest"],
                               "cta": "Register interest", "price_display": "Proposed $48 - not yet available", "must_not_claim": research_handoff.get("RISKS", [])[:1]},
        "CREATIVE_PRODUCTION_BRIEF": {"source_visual": "certified hero (asset_metaai_image_1794355016)",
                                      "formats": ["1080x1080", "1080x1920", "1200x628"], "overlay_hooks": ["H1", "H2", "H3"],
                                      "brand": "warm dark neutrals, serif headline, no holiday clipart", "url_in_copy": url},
        "TEST_HYPOTHESES": ["H1 (time/sanctuary) earns higher engagement-per-reach than H2/H3.", "Link-card format produces more storefront clicks than photo posts."],
        "MEASUREMENT_PLAN": {"primary": "storefront visits from social (UTM)", "secondary": ["reach", "engagement", "comments"],
                             "utm": {"utm_source": "{platform}", "utm_medium": "organic_social", "utm_campaign": "holiday_mug_r1", "utm_content": "{hook_id}"},
                             "note": "Storefront has no analytics yet; click measurement is a declared gap."},
        "SPEND_RECOMMENDATION": {"recommended": "$0 now; consider $20 boost test on best hook after 7 days of organic data", "authorized": False},
        "AI_ENRICHMENT": enrichment,
    }
    return {"output": brief, "artifacts": [], "issues": issues, "cost": dict(ZERO_COST)}


# ===================================================================== CREATIVE
def _font(size: int):
    from PIL import ImageFont
    for candidate in ("/System/Library/Fonts/Supplemental/Georgia.ttf", "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
                      "/Library/Fonts/Georgia.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _render(src: Path, out: Path, size: tuple[int, int], hook: str, footer: str) -> None:
    from PIL import Image, ImageDraw, ImageOps
    img = ImageOps.fit(Image.open(src).convert("RGB"), size, method=Image.LANCZOS, centering=(0.5, 0.5))
    w, h = size
    band = Image.new("RGBA", (w, int(h * 0.30)), (18, 14, 10, 170))
    img.paste(band, (0, h - band.height), band)
    d = ImageDraw.Draw(img)
    font = _font(max(28, w // 22)); small = _font(max(18, w // 45))
    words, lines, line = hook.split(), [], ""
    for wd in words:
        trial = (line + " " + wd).strip()
        if d.textlength(trial, font=font) > w * 0.86:
            lines.append(line); line = wd
        else:
            line = trial
    lines.append(line)
    y = h - band.height + int(band.height * 0.14)
    for ln in lines[:3]:
        d.text((int(w * 0.07), y), ln, font=font, fill=(245, 236, 222)); y += int(font.size * 1.25)
    d.text((int(w * 0.07), h - int(small.size * 2.2)), footer, font=small, fill=(214, 196, 170))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=90)


def creative(project: dict, brief: dict, *, renderer: Callable[..., None] = _render) -> dict:
    from product_truth_validator import ProductTruthValidator as Truth
    out_dir = ROOT / "dist/creative/business_loop" / project["project_id"]
    hooks = {h["id"]: h["text"] for h in brief["HOOKS"]}
    url = brief["CREATIVE_PRODUCTION_BRIEF"]["url_in_copy"]
    specs = [("primary_square_1080", (1080, 1080), "H1"), ("vertical_story_1080x1920", (1080, 1920), "H2"), ("link_card_1200x628", (1200, 628), "H3")]
    assets, issues = [], []
    for name, size, hook_id in specs:
        path = out_dir / f"{name}.jpg"
        try:
            renderer(HERO_JPG, path, size, hooks[hook_id], "The 6:12 AM Ritual - studio preview")
        except Exception as exc:  # noqa: BLE001 — one failed format must not stop the rest
            issues.append({"code": "CREATIVE_GENERATION_FAILURE", "asset": name, "detail": type(exc).__name__,
                           "recovery": "FALLBACK_TO_CERTIFIED_HERO_DERIVATIVE"})
            path = HERO_JPG
        assets.append({"asset_id": f"asset_bl_{project['project_id'][-8:]}_{name}", "role": "PRIMARY" if name.startswith("primary") else "VARIATION",
                       "path": _rel(path), "sha256": sha256(path), "size": f"{size[0]}x{size[1]}", "hook_id": hook_id,
                       "parent_asset_id": "asset_metaai_image_1794355016", "fallback": path == HERO_JPG})
    captions = {
        "FACEBOOK": f"{hooks['H1']}\n\nA ceramic mug concept for the quiet minutes before the holiday rush. Studio preview - register interest:\n{url}?utm_source=facebook&utm_medium=organic_social&utm_campaign=holiday_mug_r1&utm_content=H1",
        "INSTAGRAM": f"{hooks['H2']}\n\nStudio concept preview. Register interest at {url}?utm_source=instagram&utm_medium=organic_social&utm_campaign=holiday_mug_r1&utm_content=H2\n\n#QuietRitual #SlowMornings",
        "TIKTOK": f"{hooks['H3']} Studio preview: {url}",
    }
    qa = {ch: Truth.audit_copy(text) for ch, text in captions.items()}
    qa_all = {"copy": qa, "hooks": {k: Truth.audit_copy(v) for k, v in hooks.items()},
              "status": "PASS" if all(r["status"] == "PASS" for r in [*qa.values()]) else "FLAGGED",
              "brand_consistency": "same certified hero, same serif treatment, same campaign name across formats",
              "fallback_assets": sum(a["fallback"] for a in assets)}
    if qa_all["status"] != "PASS":
        issues.append({"code": "CREATIVE_QA_FLAGGED", "detail": qa, "recovery": "ROUTE_BACK_TO_MARKETING_FOR_COPY_FIX"})
    output = {"ASSETS": assets, "CAPTIONS": captions, "CTA": brief["CTA"], "CREATIVE_QA": qa_all,
              "VIDEO": {"status": "REUSED_EXISTING", "path": "dist/creative/modal_holiday_ceramic_mug_video_1794413265_instagram.mp4",
                        "note": "No new video generated in R1 (bounded); certified reel reused."}}
    return {"output": output, "artifacts": [a["path"] for a in assets], "issues": issues, "cost": dict(ZERO_COST)}


# ===================================================================== COMMERCE
def commerce(project: dict, research_handoff: dict, brief: dict, creative_out: dict | None) -> dict:
    m = _json(MANIFEST)
    cp = m["commerce_package"]
    images = [a["path"] for a in (creative_out or {}).get("ASSETS", [])] or [_rel(HERO_JPG)]
    offer = {
        "PRODUCT_ID": cp["product_id"], "OFFER_ID": f"offer_{project['project_id'][-12:]}",
        "PRODUCT_NAME": "The 6:12 AM Ritual Ceramic Mug (Studio Preview)",
        "PRODUCT_DESCRIPTION": "A ceramic mug concept for the quiet minutes before the holiday rush. Concept preview: specifications are being verified with the fulfillment partner.",
        "PRICE": {"amount_usd": cp["proposed_retail_price_usd"], "status": "PROPOSED_BUSINESS_DECISION"},
        "COST": {"amount_usd": cp["estimated_cogs_usd"], "status": "ESTIMATED_ONLY (no supplier quote)"},
        "MARGIN": {"gross_margin_estimate": round(1 - cp["estimated_cogs_usd"] / cp["proposed_retail_price_usd"], 3), "status": "ESTIMATE"},
        "IMAGES": images,
        "FULFILLMENT_METHOD": "Print-on-demand (Printify credential available; blueprint/provider not selected)",
        "PURCHASE_URL": m["public_test_url"], "STOREFRONT_LOCATION": "Cloudflare Pages nexus-campaigns (test deployment)",
        "CONVERSION_EVENT": "register interest (waitlist) - no checkout",
        "STATUS": "STAGED",
        "BLOCKERS_TO_LIVE": ["Supplier/blueprint selection + real COGS", "Checkout (only Stripe TEST credential exists)", "Ray approval to sell"],
        "PAID_LISTING_COSTS_INCURRED": 0.0,
    }
    approval = {"approval_kind": "COMMERCE_GO_LIVE", "action": "Select Printify blueprint, create draft product, enable checkout on storefront",
                "why": "Offer cannot take real orders until supplier, COGS and checkout are verified", "status": "WAITING_FOR_RAY_APPROVAL",
                "paused_action_only": True}
    return {"output": {"OFFER": offer, "APPROVAL_REQUEST": approval}, "artifacts": [], "issues": [], "cost": dict(ZERO_COST)}


# ================================================================= DISTRIBUTION
def distribution(project: dict, brief: dict, creative_out: dict, commerce_out: dict, *, request_writer: Callable[[dict], dict] | None = None) -> dict:
    """Prepare all posts; create a hash-bound Facebook approval card; publication stays paused until Ray approves."""
    import facebook_live_publisher as fb
    url = commerce_out["OFFER"]["PURCHASE_URL"]
    primary = next(a for a in creative_out["ASSETS"] if a["role"] == "PRIMARY")
    posts = [
        {"platform": "FACEBOOK", "asset": primary["path"], "copy": creative_out["CAPTIONS"]["FACEBOOK"], "status": "APPROVAL_REQUESTED"},
        {"platform": "INSTAGRAM", "asset": creative_out["ASSETS"][1]["path"], "copy": creative_out["CAPTIONS"]["INSTAGRAM"],
         "status": "PREPARED (needs public media URL + its own approval)"},
        {"platform": "TIKTOK", "asset": creative_out["ASSETS"][1]["path"], "copy": creative_out["CAPTIONS"]["TIKTOK"], "status": "BLOCKED_AUTH_REQUIRED"},
    ]
    rid = f"apr_req_{hashlib.sha256((project['project_id'] + primary['sha256']).encode()).hexdigest()[:16]}"
    req = {
        "approval_request_id": rid, "status": "WAITING_FOR_RAY_APPROVAL", "approval_id": None,
        "venture_id": project["venture_id"], "campaign_id": "camp_holiday_ceramic_mug_2026",
        "distribution_job_id": f"dist_job_bl_{project['project_id'][-12:]}_fb", "platform": "FACEBOOK", "post_format": "PHOTO_POST",
        "channel_account_id": fb.HOLIDAY_CHANNEL_ACCOUNT_ID, "target_page": "Raytestpage", "target_page_id": fb.HOLIDAY_PAGE_ID,
        "copy": posts[0]["copy"], "copy_sha256": hashlib.sha256(posts[0]["copy"].encode()).hexdigest(),
        "media": {"asset_id": primary["asset_id"], "path": primary["path"], "sha256": primary["sha256"], "format": "JPEG 1080x1080",
                  "provider_derivative": {"asset_id": primary["asset_id"] + "_fb", "path": primary["path"], "sha256": primary["sha256"],
                                          "format": "JPEG 1080x1080", "parent_asset_id": primary["asset_id"]}},
        "target_url": url, "max_external_posts": 1, "certification_purpose": "BUSINESS_LOOP_R1_CYCLE_1",
        "certification_run_id": project["project_id"], "requested_by": fb.REQUESTER, "created_at": project.get("updated_at"),
        "project_id": project["project_id"],
    }
    req["idempotency_key"] = fb.expected_idempotency_key(req)
    req["request_hash"] = fb.compute_request_hash(req)
    problems = fb.verify_request(req)
    if problems:
        raise DepartmentFailure("APPROVAL_REQUEST_INVALID", ";".join(problems))
    writer = request_writer or (lambda r: (fb.REQUESTS_DIR / f"bl_{project['project_id']}_facebook_approval_request.json").write_text(json.dumps(r, indent=1) + "\n") and r)
    writer(req)
    package = {"POSTS": posts, "CHANNELS": [p["platform"] for p in posts], "PUBLICATION_STATUS": "PAUSED_WAITING_FOR_RAY_APPROVAL",
               "APPROVAL_REQUIRED": [{"approval_request_id": rid, "platform": "FACEBOOK", "owner_command": f"./bin/nexus distribution approve {rid}",
                                      "then": f"./bin/nexus distribution publish {rid}"}],
               "PARENT_PROJECT_EFFECT": "NONE - only publication is paused"}
    issues = [{"code": "PUBLISHING_APPROVAL_MISSING", "detail": rid, "recovery": "APPROVAL_CARD_CREATED; METRICS_CONTINUE_ON_EXISTING_POSTS"},
              {"code": "CHANNEL_AUTH_REQUIRED", "detail": "TIKTOK", "recovery": "ROUTE_TO_SYSTEMS_LATER"}]
    return {"output": package, "artifacts": [_rel(fb.REQUESTS_DIR / f"bl_{project['project_id']}_facebook_approval_request.json")], "issues": issues, "cost": dict(ZERO_COST)}


# ====================================================================== METRICS
def _graph_metrics(graph, receipts: list[dict]) -> list[dict]:
    rows = []
    for r in receipts:
        if r["platform"] == "FACEBOOK":
            pid = r["meta_post_id"]
            st, base = graph.get(pid, "created_time,shares,reactions.summary(total_count),comments.summary(total_count)")
            row = {"platform": "FACEBOOK", "object_id": pid, "published_at": r.get("published_at"), "base_http": st,
                   "REACTIONS": ((base.get("reactions") or {}).get("summary") or {}).get("total_count") if st == 200 else None,
                   "COMMENTS": ((base.get("comments") or {}).get("summary") or {}).get("total_count") if st == 200 else None,
                   "SHARES": (base.get("shares") or {}).get("count", 0) if st == 200 else None}
            # Graph v23: post_impressions* are rejected/empty; media-view metrics are the supported replacements.
            for metric, key in (("post_media_view", "IMPRESSIONS"), ("post_total_media_view_unique", "REACH"), ("post_clicks", "CLICKS")):
                s2, ins = graph._request("GET", f"{pid}/insights", params={"metric": metric})
                vals = (ins.get("data") or [{}])[0].get("values") if s2 == 200 and ins.get("data") else None
                row[key] = vals[0].get("value") if vals else None
                row.setdefault("unavailable", {})[key] = None if vals else ((ins.get("error") or {}).get("message") or f"HTTP_{s2}")[:120]
            rows.append(row)
        elif r["platform"] == "INSTAGRAM":
            mid = r["instagram_media_id"]
            st, base = graph.get(mid, "like_count,comments_count,timestamp,permalink")
            row = {"platform": "INSTAGRAM", "object_id": mid, "published_at": r.get("published_at"), "base_http": st,
                   "LIKES": base.get("like_count") if st == 200 else None, "COMMENTS": base.get("comments_count") if st == 200 else None}
            for metric, key in (("reach", "REACH"), ("views", "VIEWS"), ("saved", "SAVES"), ("shares", "SHARES"), ("total_interactions", "ENGAGEMENT")):
                s2, ins = graph._request("GET", f"{mid}/insights", params={"metric": metric})
                vals = (ins.get("data") or [{}])[0].get("values") if s2 == 200 and ins.get("data") else None
                row[key] = vals[0].get("value") if vals else None
                row.setdefault("unavailable", {})[key] = None if vals else ((ins.get("error") or {}).get("message") or f"HTTP_{s2}")[:120]
            rows.append(row)
    return rows


def metrics(project: dict, *, graph_factory: Callable[[], Any] | None = None) -> dict:
    receipts = [json.loads(l) for l in PUBLISH_RECEIPTS.read_text().splitlines() if l.strip()] if PUBLISH_RECEIPTS.exists() else []
    receipts = [r for r in receipts if r.get("campaign_id") == "camp_holiday_ceramic_mug_2026" and r.get("final_job_state") == "PUBLISHED"]
    if graph_factory is None:
        import facebook_live_publisher as fb
        graph_factory = lambda: fb.MetaGraphClient(fb.resolve_holiday_page_token())  # noqa: E731
    try:
        graph = graph_factory()
        rows = _graph_metrics(graph, receipts)
    except Exception as exc:  # noqa: BLE001 — metrics outage is recoverable
        raise DepartmentFailure("METRICS_TEMPORARILY_UNAVAILABLE", type(exc).__name__) from None
    store = {"PRODUCT_PAGE_VISITS": None, "ADD_TO_CART": None, "CHECKOUT": None, "ORDERS": 0, "REVENUE": 0.0,
             "basis": "no analytics on storefront; no checkout exists -> orders/revenue are structurally 0, visits unmeasured"}
    def total(key):
        vals = [r.get(key) for r in rows if isinstance(r.get(key), (int, float))]
        return sum(vals) if vals else None
    summary = {"IMPRESSIONS": total("IMPRESSIONS"), "REACH": total("REACH"), "VIEWS": total("VIEWS"), "CLICKS": total("CLICKS"),
               "COMMENTS": total("COMMENTS"), "ENGAGEMENT": (total("REACTIONS") or 0) + (total("LIKES") or 0) + (total("COMMENTS") or 0) + (total("SHARES") or 0) + (total("SAVES") or 0)}
    summary["CTR"] = round(summary["CLICKS"] / summary["IMPRESSIONS"], 4) if summary["CLICKS"] is not None and summary["IMPRESSIONS"] else None
    issues = []
    reasons = [str(v) for r in rows for v in (r.get("unavailable") or {}).values() if v]
    if any("permission" in v.lower() for v in reasons):
        issues.append({"code": "METRIC_PERMISSION_MISSING", "detail": "instagram insights (reach/views/saves) need instagram_manage_insights",
                       "recovery": "ROUTE_TO_SYSTEMS: owner re-consent adds the scope; counts (likes/comments/clicks) still ingested"})
    if any("valid insights metric" in v for v in reasons) or any(r.get("base_http") not in (200, None) for r in rows):
        issues.append({"code": "METRIC_DEPRECATED_OR_REJECTED", "detail": "facebook impressions metric / base fields rejected by Graph v23",
                       "recovery": "ROUTE_TO_SYSTEMS: map to current Graph post metrics"})
    return {"output": {"METRIC_SOURCES": ["Meta Graph API (Facebook post + Instagram reel, read-only)", "storefront (no analytics)"],
                       "PER_OBJECT": rows, "SOCIAL_SUMMARY": summary, "STORE": store, "REAL_METRICS_AVAILABLE": any(r.get("base_http") == 200 for r in rows),
                       "objects_measured": len(rows)},
            "artifacts": [], "issues": issues, "cost": dict(ZERO_COST)}


# ===================================================================== ANALYSIS
def analysis(project: dict, metrics_out: dict | None, distribution_out: dict, commerce_out: dict) -> dict:
    """Evidence-only analysis + deterministic next best action."""
    if not metrics_out:
        return {"output": {"WHAT_HAPPENED": "Metrics unavailable this cycle.", "WHAT_WORKED": [], "WHAT_FAILED": ["metric ingestion"],
                           "WHAT_IS_UNKNOWN": ["all performance"], "WHAT_SHOULD_CHANGE": ["retry metrics next cycle"],
                           "NEXT_BEST_ACTION": {"action": "RETRY_METRICS", "owner": "METRICS", "why": "no data"}},
                "artifacts": [], "issues": [], "cost": dict(ZERO_COST)}
    s = metrics_out["SOCIAL_SUMMARY"]
    exposure = s.get("REACH") if s.get("REACH") is not None else s.get("VIEWS")
    reach = exposure or 0
    eng = s.get("ENGAGEMENT") or 0
    rate = round(eng / reach, 4) if reach else None
    reach_text = "unmeasured (insights permission/metric gap)" if exposure is None else str(exposure)
    worked, failed, unknown = [], [], []
    if metrics_out["REAL_METRICS_AVAILABLE"]:
        worked.append(f"Metric ingestion returned real counts from live posts (engagement={eng}, clicks={s.get('CLICKS')}); exposure {reach_text}.")
    if rate is not None and rate == 0:
        failed.append("Zero engagement on measured exposure.")
    if s.get("CLICKS") is None:
        unknown.append("Storefront clicks (Meta click metric unavailable and storefront has no analytics).")
    unknown += ["Purchase intent at $48 (no waitlist/checkout capture)", "Which hook performs best (only one hook published so far)"]
    pending = distribution_out["PUBLICATION_STATUS"]
    if reach < 100:
        nba = {"action": "TEST_ALTERNATE_HOOK_WITH_TRACKED_LINK", "owner": "MARKETING",
               "why": f"Cannot judge creative: exposure {reach_text}, engagement {eng}, clicks {s.get('CLICKS')}. Publish H1 tracked post (pending approval) and prepare H2 variant for an A/B read; add a storefront interest-capture + click counter so intent becomes measurable.",
               "evidence": {"reach": exposure, "engagement": eng, "clicks": s.get("CLICKS"), "engagement_rate": rate}}
    elif rate is not None and rate < 0.01:
        nba = {"action": "TEST_ALTERNATE_HOOK", "owner": "CREATIVE", "why": f"Engagement rate {rate} < 1% on reach {reach}.", "evidence": {"rate": rate}}
    else:
        nba = {"action": "CONTINUE_AND_ADD_VARIATION", "owner": "CREATIVE", "why": f"Engagement rate {rate} acceptable; extend.", "evidence": {"rate": rate}}
    out = {"WHAT_HAPPENED": f"Existing posts measured: {metrics_out['objects_measured']}; new tracked post {pending}; offer {commerce_out['OFFER']['STATUS']}.",
           "WHAT_WORKED": worked, "WHAT_FAILED": failed, "WHAT_IS_UNKNOWN": unknown,
           "WHAT_SHOULD_CHANGE": ["Measure storefront clicks/intent (UTM + interest capture)", "A/B hooks on equal formats", "Secure supplier quote to replace estimated COGS"],
           "ATTRIBUTION": "None claimed: no click or order data links exposure to commerce outcomes.",
           "NEXT_BEST_ACTION": nba}
    return {"output": out, "artifacts": [], "issues": [], "cost": dict(ZERO_COST)}
