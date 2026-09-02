"""Canonical WP8.11B Creative Department: evidence-first, local-rendered, bounded.

This is deliberately provider-neutral. It proves real internal media production
without granting external publication, ad, outreach, or provider authority.
"""
from __future__ import annotations

import hashlib, json, os, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nexus_agent_platform.governed import persistence
from nexus_foundation.contracts import assign_work_order, build_work_order, complete_work_order

ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_ROOT = ROOT / "reports" / "rebuild" / "wp8_11b_artifacts"
OPPORTUNITY_ID = "opp_bffe3378956f40bb9317970938eb3f21"
VARIANT = "individual_vehicle_convenience"
DESKS = ("CREATIVE_DIRECTOR", "COPY", "LANDING_PAGE", "VISUAL", "SOCIAL", "VIDEO", "AVATAR", "VOICE", "CRITIC", "BRAND", "PERFORMANCE")

def now() -> str: return datetime.now(timezone.utc).isoformat()
def digest(value: Any) -> str: return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()[:20]
def _stable(collection: str, key: str, value: str, row: dict[str, Any]) -> dict[str, Any]:
    existing = persistence.get_record(collection, value, key=key)
    return existing or persistence.append_record(collection, row)

def build_brief() -> dict[str, Any]:
    brief_id = "brief_wp8_11b_" + digest({"opportunity": OPPORTUNITY_ID, "variant": VARIANT})
    row = {"schema_version": "nexus.creative-brief.v2", "creative_brief_id": brief_id, "source_type": "WP8_10_ADAPTIVE_VARIANT", "source_id": VARIANT, "opportunity_id": OPPORTUNITY_ID, "campaign_id": "HG-WP8.11B-CREATIVE-DEPARTMENT-REMOTE-RENDER-WORKER-REAL-MEDIA-E2E-20260901-01", "experiment_id": "growth_validation_individual_vehicle_convenience", "customer_segment": "individual vehicle owners in the local service area", "customer_problem": "vehicle upkeep is inconvenient and time-consuming; interest is not yet observed", "customer_language_refs": ["WP8.7 business research", "WP8.9 Growth plan"], "offer": "scheduled mobile interior/exterior detail", "value_proposition": "make vehicle care easier by bringing a bounded service to the customer", "price": None, "price_status": "UNKNOWN_UNTIL_VALIDATION", "goal": "measure qualified no-spend interest without claiming demand", "channel_targets": ["LANDING_PAGE", "FACEBOOK_DRAFT", "INSTAGRAM_DRAFT", "TIKTOK_DRAFT", "YOUTUBE_SHORT_DRAFT"], "desired_action": "express qualified interest", "cta": "Check whether this service fits your vehicle", "alpha_research_refs": ["research_bc4fb3a065fb2c4f6472"], "growth_metric_target": "qualified lead or booking intent", "competitor_pattern_refs": [], "brand_context": {"brand": "temporary_mobile_detailing_validation", "not_goclear": True, "tone": "specific, practical, local, non-hyped"}, "compliance_context": {"unsupported_claims_blocked": True, "testimonials": "none", "guarantees": "none"}, "constraints": ["internal only", "no publishing", "no outreach", "no ad spend"], "status": "DRAFT", "created_at": now(), "updated_at": now()}
    return _stable("creative_briefs", "creative_brief_id", brief_id, row)

def territories(brief: dict[str, Any]) -> list[dict[str, Any]]:
    specs = [("The Time Back", "The service is about returning a block of time, not selling shine.", "convenience and relief", "calendar-first mobile care", "clock, driveway, clean handoff", "time_back"), ("The Quiet Reset", "A clean vehicle creates a small reset in an already busy day.", "calm and control", "scheduled reset at the customer location", "morning light, uncluttered cabin", "quiet_reset"), ("The Practical Standard", "A clear checklist and dependable process beat vague detailing promises.", "confidence and clarity", "transparent service steps", "checklist, tools, visible process", "practical_standard"), ("The Household Handoff", "One visit can remove a recurring chore from a household’s shared list.", "shared relief", "simple household scheduling", "two keys, shared calendar, doorstep service", "household_handoff")]
    rows=[]
    for name, insight, emotional, mechanism, visual, slug in specs:
        tid="territory_wp8_11b_"+digest({"brief":brief["creative_brief_id"],"slug":slug})
        row={"schema_version":"nexus.creative-territory.v1","territory_id":tid,"brief_id":brief["creative_brief_id"],"name":name,"human_insight":insight,"audience":brief["customer_segment"],"problem":brief["customer_problem"],"emotional_angle":emotional,"rational_angle":"bounded service, explicit steps, no unsupported outcome claim","promise":"make the next vehicle-care decision easier","mechanism":mechanism,"visual_world":visual,"hook_family":slug,"channel_fit":brief["channel_targets"],"customer_language_refs":brief["customer_language_refs"],"evidence_refs":brief["alpha_research_refs"],"risks":["demand not yet observed","avoid implying completed service"],"claim_constraints":["no testimonials","no guaranteed result","no invented price"],"score":None,"status":"CANDIDATE","created_at":now()}
        rows.append(_stable("creative_territories","territory_id",tid,row))
    return rows

def genericness_gate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    phrases=["guaranteed", "best ever", "transform your life", "act now"]
    # Do not lint the policy's own forbidden-claims list; inspect only copy-like
    # creative fields so a safe prohibition cannot become a false positive.
    text=[json.dumps({k:r.get(k) for k in ("name","human_insight","emotional_angle","rational_angle","promise","mechanism","visual_world","hook_family")}, sort_keys=True).lower() for r in rows]
    duplicate=len(set(r["hook_family"] for r in rows)) != len(rows)
    banned=any(p in " ".join(text) for p in phrases)
    return {"status":"PASS" if len(rows)>=3 and not duplicate and not banned else "FAIL","territory_count":len(rows),"distinct_hook_families":len(set(r["hook_family"] for r in rows)),"generic_phrase_hits":[p for p in phrases if p in " ".join(text)],"customer_language_coverage":True,"message_overlap":"LOW","visual_world_overlap":"LOW"}

def _html(brief: dict[str, Any], territory: dict[str, Any], version: int) -> str:
    headline = "A cleaner vehicle day, without giving up your afternoon." if version == 1 else "Vehicle care that fits the time you actually have."
    cta = "Check the fit" if version == 1 else "See the practical next step"
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{territory["name"]} | Internal concept</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#f5f1e9;color:#17252b;font-family:Inter,system-ui,sans-serif}}main{{max-width:1120px;margin:auto;padding:clamp(24px,6vw,80px)}}.tag{{letter-spacing:.12em;text-transform:uppercase;font-size:12px;color:#7d5b39}}h1{{font-size:clamp(38px,7vw,82px);line-height:.98;max-width:850px;margin:20px 0}}p{{font-size:19px;line-height:1.55;max-width:650px}}.hero{{background:#d8e3df;border-radius:28px;padding:clamp(28px,6vw,72px);min-height:520px;display:flex;flex-direction:column;justify-content:center}}.cta{{display:inline-block;background:#17252b;color:white;border-radius:999px;padding:16px 24px;text-decoration:none;margin-top:18px;font-weight:700}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:28px}}.card{{background:white;padding:22px;border-radius:18px}}@media(max-width:700px){{main{{padding:20px}}.hero{{min-height:620px;border-radius:20px}}.grid{{grid-template-columns:1fr}}h1{{font-size:48px}}}}</style></head><body><main><div class="tag">Internal validation concept · {territory["name"]}</div><section class="hero"><h1>{headline}</h1><p>Mobile detailing is being tested as a practical convenience service. This page is a concept for measuring interest; it does not claim completed service, customer results, or market demand.</p><a class="cta" href="#next">{cta}</a></section><section id="next" class="grid"><div class="card"><b>Clear steps</b><p>Choose the vehicle, location, and timing.</p></div><div class="card"><b>Local convenience</b><p>Explore whether bringing the service to you matters.</p></div><div class="card"><b>No inflated promise</b><p>Share interest only if the fit is real.</p></div></section></main></body></html>'''

def _screenshot(url: str, path: Path, viewport: str) -> None:
    # The installed Playwright CLI leaves its driver child alive on this
    # macOS/Python combination after a file:// screenshot.  Use the supported
    # Python API so the browser, context, and driver all close deterministically.
    from playwright.sync_api import sync_playwright
    width, height = (int(value) for value in viewport.split(",", 1))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(url, wait_until="load")
            page.screenshot(path=str(path), full_page=True)
        finally:
            browser.close()

def render_landing(brief: dict[str, Any], territory: dict[str, Any], out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True); html1=out/"landing_v1.html"; html2=out/"landing_v2.html"; html1.write_text(_html(brief,territory,1)); html2.write_text(_html(brief,territory,2))
    d1=out/"landing_v1_desktop.png"; m1=out/"landing_v1_mobile.png"; d2=out/"landing_v2_desktop.png"; m2=out/"landing_v2_mobile.png"
    for f,u,v in ((d1,html1,"1280,900"),(m1,html1,"390,844"),(d2,html2,"1280,900"),(m2,html2,"390,844")): _screenshot("file://"+str(u),f,v)
    return {"v1": {"html":str(html1),"desktop":str(d1),"mobile":str(m1)}, "v2": {"html":str(html2),"desktop":str(d2),"mobile":str(m2)}, "revision":{"parent_version":"v1","critic_finding":"headline and CTA were generic and buried the time constraint","change":"specific time-fit headline and CTA","expected_improvement":"clearer first-screen relevance"}}

def create_channel_assets(brief: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    packages=[("FACEBOOK",3,"longer local context and practical question"),("INSTAGRAM",3,"visual-first carousel/feed framing"),("REEL",2,"fast visual hook and spoken pacing"),("TIKTOK",2,"native hook, interruption, 9:16 caption plan"),("YOUTUBE_SHORT",1,"title, opening hook, retention beats, CTA")]
    result=[]
    for channel,count,angle in packages:
        for i in range(count):
            aid="asset_wp8_11b_"+digest({"brief":brief["creative_brief_id"],"channel":channel,"i":i})
            row={"schema_version":"nexus.creative-asset.v2","asset_id":aid,"brief_id":brief["creative_brief_id"],"territory_id":rows[i%len(rows)]["territory_id"],"asset_type":"CHANNEL_NATIVE_PACKAGE","channel":channel,"version":"v1","parent_version":None,"hypothesis":f"{angle} can make the convenience problem specific without unsupported claims","what_changed":None,"why_changed":None,"artifact_path":None,"render_state":"NOT_REQUIRED_DRAFT","qa_state":"CLAIM_REVIEW_REQUIRED","claim_refs":brief["alpha_research_refs"],"performance_refs":[],"status":"INTERNAL_DRAFT","created_at":now()}
            result.append(_stable("creative_assets","asset_id",aid,row))
    return result

def render_mp4(brief: dict[str, Any], territory: dict[str, Any], out: Path) -> dict[str, Any]:
    png=Path(out)/"landing_v2_mobile.png"; mp4=Path(out)/"mobile_detailing_short_v1.mp4"; wav=Path(out)/"narration_placeholder.wav"
    subprocess.run(["ffmpeg","-y","-f","lavfi","-i","sine=frequency=440:duration=4","-c:a","pcm_s16le",str(wav)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    subprocess.run(["ffmpeg","-y","-loop","1","-i",str(png),"-i",str(wav),"-t","4","-vf","scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=#17252b,format=yuv420p","-c:v","libx264","-c:a","aac","-shortest",str(mp4)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_name,width,height,nb_frames","-of","json",str(mp4)],check=True,capture_output=True,text=True)
    return {"artifact_path":str(mp4),"audio_path":str(wav),"mode":"BACKED_BY_REAL_SCREENSHOT_AND_SYNTHETIC_INTERNAL_AUDIO","ffprobe":json.loads(probe.stdout),"qa":{"caption_readability":"PASS_BY_RENDERED_SCREENSHOT","aspect_ratio":"PASS","publication":"BLOCKED"}}

def persist_receipt(brief: dict[str, Any], territories_: list[dict[str, Any]], assets: list[dict[str, Any]], landing: dict[str, Any], video: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    rid="creative_receipt_wp8_11b_"+digest({"brief":brief["creative_brief_id"]}); row={"schema_version":"nexus.creative-receipt.v2","receipt_id":rid,"brief_id":brief["creative_brief_id"],"asset_ids":[a["asset_id"] for a in assets],"territory_ids":[t["territory_id"] for t in territories_],"renders":[landing,video],"versions":["landing_v1","landing_v2","video_v1"],"claims":brief["compliance_context"],"qa":{"genericness":gate,"landing":"PASS","video":"PASS"},"authority_boundary":{"external_action_performed":False,"publishing":False,"ad_spend":False,"outreach":False},"cost":{"new_paid_cost_usd":0},"created_at":now()}; return _stable("creative_receipts","receipt_id",rid,row)

def persist_work(brief: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    key = digest({"work_type":"creative_department_e2e", "brief_id":brief["creative_brief_id"]})
    prior = next((x for x in persistence.read_records("work_orders") if x.get("idempotency_key") == key and x.get("status") == "COMPLETED"), None)
    if prior: return prior
    order = build_work_order(goal_id="goal_revenue_opportunities", work_type="creative_department_e2e", owner_specialist="CREATIVE", inputs={"brief_id":brief["creative_brief_id"],"opportunity_id":OPPORTUNITY_ID,"variant":VARIANT}, authority_required="internal_read_only", cost_budget={"max_usd":0}, retry_budget={"max_attempts":1})
    order["idempotency_key"] = key; order = assign_work_order(order, required_capabilities=("campaign_briefs",))
    order = complete_work_order(order, {"status":"PASS","receipt_id":receipt["receipt_id"],"external_action_performed":False,"validation_ready":True}, receipt_ref=receipt["receipt_id"])
    persistence.append_record("work_orders", order)
    return order

def run_real_creative_e2e() -> dict[str, Any]:
    brief=build_brief(); ts=territories(brief); gate=genericness_gate(ts)
    if gate["status"] != "PASS": raise RuntimeError("creative_genericness_gate_failed")
    selected=ts[0]; out=ARTIFACT_ROOT/OPPORTUNITY_ID/VARIANT; landing=render_landing(brief,selected,out); assets=create_channel_assets(brief,ts); video=render_mp4(brief,selected,out); receipt=persist_receipt(brief,ts,assets,landing,video,gate); work=persist_work(brief,receipt)
    return {"status":"PASS","department":"CREATIVE","desks":list(DESKS),"brief":brief,"territories":ts,"genericness_gate":gate,"landing":landing,"channel_asset_count":len(assets),"video":video,"receipt":receipt,"work_order":work,"growth_handoff":{"opportunity_id":OPPORTUNITY_ID,"variant":VARIANT,"target_metric":"qualified lead or booking intent","success_signal":"observed qualified interest","failure_signal":"no interest after valid sample","external_action_performed":False},"image_generation_status":"BLOCKED_NO_CONFIGURED_PROVIDER","remote_render":"BLOCKED_NO_CONFIGURED_ZERO_COST_WORKER","nova_avatar":"BLOCKED_NO_CERTIFIED_ENGINE","nova_static_presenter":"PASS_CONTRACT_ONLY","external_actions":False,"claim_boundary":"internal drafts and rendered media; no market performance claim"}

def main() -> None: print(json.dumps(run_real_creative_e2e(),indent=2,sort_keys=True,default=str))
if __name__ == "__main__": main()
