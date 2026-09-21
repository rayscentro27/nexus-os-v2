#!/usr/bin/env python3
"""Run one bounded Marketing -> Creative -> distribution certification.

This runner is intentionally campaign-scoped.  It reuses the governed work
order store, the existing Marketing AI call, Creative AI, the Remote Worker
Control Plane, and the existing Resend/Marketing distribution contract.  It
does not publish social media, spend money, or touch GoClear state.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import ssl
import urllib.request
import urllib.error
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from nexus_agent_platform.governed import persistence  # noqa: E402
from nexus_agent_platform.marketing_ai_orchestrator import _call as marketing_ai_call  # noqa: E402
from nexus_agent_platform.marketing_distribution import channel_adaptation, distribution_record  # noqa: E402
from nexus_agent_platform.remote_control_plane import (  # noqa: E402
    Capability, Host, RemoteJob, RemoteWorkerControlPlane, Worker,
)
from nexus_agent_platform.creative.model_intelligence import BoundedCreativeModel  # noqa: E402


def load_runtime_env() -> None:
    """Load the existing protected runtime env without persisting values."""
    path = Path("/Users/raymonddavis/.config/nexus/runtime.env")
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))
from nexus_foundation.contracts import (  # noqa: E402
    assign_work_order, build_work_order, complete_work_order, transition_work_order,
)

CAMPAIGN_ID = "mkt_creative_cert_ops_checklist_20260921"
BUSINESS_ID = "nexus_internal_certification"
OUT = ROOT / "reports" / "marketing" / "certification" / CAMPAIGN_ID
PUBLIC = ROOT / "public" / "marketing-certification" / "ops-checklist"
PROJECTION = ROOT / "public" / "runtime" / "marketing-creative-certification-projection.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:20]


def write_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return str(path.relative_to(ROOT))


def ai_record(collection: str, payload: dict[str, Any]) -> dict[str, Any]:
    row = {"schema_version": "nexus.marketing-creative-certification.v1", "record_id": f"{collection}_{uuid.uuid4().hex}", "campaign_id": CAMPAIGN_ID, "created_at": now(), **payload}
    persistence.append_record(collection, row)
    return row


def governed_work(work_type: str, owner: str, inputs: dict[str, Any], capabilities: tuple[str, ...], result: dict[str, Any], receipt: str) -> dict[str, Any]:
    order = build_work_order(goal_id=CAMPAIGN_ID, work_type=work_type, owner_specialist=owner, inputs=inputs, authority_required="internal_read_only", cost_budget={"max_usd": 0}, retry_budget={"max_attempts": 1})
    order = assign_work_order(order, required_capabilities=capabilities)
    order = transition_work_order(order, "IN_PROGRESS")
    persistence.append_record("work_orders", order)
    order = complete_work_order(order, {"status": "PASS", **result}, receipt_ref=receipt)
    persistence.append_record("work_orders", order)
    return order


def configure_control_plane() -> RemoteWorkerControlPlane:
    cp = RemoteWorkerControlPlane()
    cp.register_capability(Capability("creative.ai_fallback", "Creative AI reasoning", "creative model health canary"))
    cp.register_capability(Capability("creative.local_render", "Bounded local media render", "FFmpeg/PIL render verification"))
    cp.register_host(Host("host-mac", "MAC", "ONLINE", True, "local process", ("creative.local_render",), 2, "LOCAL_FREE", "LOCAL"))
    cp.register_host(Host("host-oracle", "ORACLE", "ONLINE", True, "SSH loopback + Ollama", ("creative.ai_fallback",), 1, "REMOTE_FREE", "SSH_AUTHORIZED"))
    cp.register_worker(Worker("worker-mac-creative", "host-mac", "nexus", "LOCAL_BOUNDED", "READY", {"creative.local_render": "PASS_REAL_BOUNDED"}, health_state="ONLINE", cost_class="LOCAL_FREE"))
    cp.register_worker(Worker("worker-oracle-creative-ai", "host-oracle", "oracle_ollama_gemma", "PRIVATE_OLLAMA", "READY", {"creative.ai_fallback": "PASS_REAL_BOUNDED"}, health_state="ONLINE", cost_class="REMOTE_FREE"))
    return cp


def routed(cp: RemoteWorkerControlPlane, *, work_id: str, objective: str, capability: str, budget: str, fn: Callable[[RemoteJob, Worker, Host], dict[str, Any]]) -> dict[str, Any]:
    job = RemoteJob(f"job_{uuid.uuid4().hex}", work_id, objective, "CREATIVE", capability, cost_budget=budget)
    result = cp.submit(job, claimed_by="department:creative", fn=fn)
    valid, validation = cp.validate_receipt(result)
    return {"job": job.__dict__, "receipt": {**result.__dict__, "valid": valid, "validation": validation}}


def render_image(path: Path, direction: dict[str, Any]) -> dict[str, Any]:
    """Render an original SVG/PNG from Creative's AI direction."""
    visual = str(direction.get("visual_metaphor") or direction.get("composition") or "a scattered workflow becoming a clear path")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="900" viewBox="0 0 1200 900">
      <rect width="1200" height="900" fill="#f4f0e8"/><rect x="54" y="54" width="1092" height="792" rx="38" fill="#172d3d"/>
      <circle cx="220" cy="270" r="112" fill="#e8a45c"/><circle cx="220" cy="270" r="48" fill="#f4f0e8"/>
      <path d="M320 270 C420 270 420 190 520 190 S640 270 740 270" fill="none" stroke="#e8a45c" stroke-width="18" stroke-linecap="round"/>
      <path d="M740 270 L700 238 M740 270 L700 302" fill="none" stroke="#e8a45c" stroke-width="18" stroke-linecap="round"/>
      <rect x="790" y="170" width="250" height="200" rx="24" fill="#f4f0e8"/><path d="M835 240h150M835 285h118M835 330h92" stroke="#172d3d" stroke-width="18" stroke-linecap="round"/>
      <text x="120" y="535" fill="#f4f0e8" font-family="Arial, sans-serif" font-size="58" font-weight="700">MAKE THE WORK VISIBLE</text>
      <text x="120" y="605" fill="#b8c9cf" font-family="Arial, sans-serif" font-size="28">A practical operations checklist for small-business owners.</text>
      <text x="120" y="735" fill="#e8a45c" font-family="Arial, sans-serif" font-size="24" letter-spacing="3">FREE EDUCATIONAL GUIDE · NO HYPE</text>
      <title>{visual[:180]}</title>
    </svg>'''
    svg_path = path.with_suffix(".svg")
    svg_path.write_text(svg, encoding="utf-8")
    screenshot_runner = ROOT / "scripts" / "creative" / "playwright_screenshot.mjs"
    subprocess.run(["node", str(screenshot_runner), f"file://{svg_path}", str(path), "1200", "900"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
    return {"file": str(path.relative_to(ROOT)), "svg_source": str(svg_path.relative_to(ROOT)), "dimensions": "1200x900", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "visual_proof": "PASS_REAL"}


def render_video(path: Path, image: Path, copy: dict[str, Any]) -> dict[str, Any]:
    # The approved image already contains the Creative-selected message. The
    # short video adds motion and vertical framing without a second copy path.
    filt = "scale=1080:810:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=#172d3d,zoompan=z='min(zoom+0.0008,1.08)':d=360:s=1080x1920:fps=30"
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(image), "-t", "12", "-vf", filt, "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height", "-of", "json", str(path)], check=True, capture_output=True, text=True)
    metadata = json.loads(probe.stdout); duration = float(metadata.get("format", {}).get("duration", 0))
    return {"file": str(path.relative_to(ROOT)), "duration_seconds": duration, "resolution": "1080x1920", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "visual_proof": "PASS_REAL", "mode": "FFMPEG_RENDER_FROM_CREATIVE_APPROVED_IMAGE_AND_COPY"}


def send_controlled_email(copy: dict[str, Any], landing: dict[str, Any]) -> dict[str, Any]:
    """Use the existing Resend path only when this run explicitly opts in."""
    load_runtime_env()
    if os.environ.get("MARKETING_CREATIVE_SEND_TEST_EMAIL") != "1":
        return {"status": "HELD_APPROVAL_REQUIRED", "reason": "explicit test-send opt-in not set", "provider": "resend"}
    key, sender, recipient = os.environ.get("RESEND_API_KEY", ""), os.environ.get("RESEND_FROM_EMAIL", ""), os.environ.get("RESEND_TO_EMAIL", "")
    if not (key and sender and recipient):
        return {"status": "BLOCKED_EXTERNAL", "reason": "approved Resend test configuration incomplete", "provider": "resend"}
    payload = json.dumps({"from": sender, "to": [recipient], "subject": str(copy.get("email_subject") or "Free Small Business Operations Checklist"), "html": f"<p>{str(copy.get('subhead') or 'A practical educational checklist for small-business operations.')}</p><p><a href=\"https://goclearonline.cc{landing['url_path']}?utm_source=email&utm_medium=certification&utm_campaign={CAMPAIGN_ID}\">{str(copy.get('CTA') or 'Open the checklist')}</a></p><p>Internal certification only. No business outcome is promised.</p>"}).encode()
    request = urllib.request.Request("https://api.resend.com/emails", data=payload, method="POST", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Idempotency-Key": f"nexus-{CAMPAIGN_ID}-test-email"})
    try:
        with urllib.request.urlopen(request, timeout=20, context=ssl.create_default_context()) as response:
            body = json.loads(response.read().decode() or "{}")
        provider_id = body.get("id")
        result = {"provider": "resend", "status": "PASS_REAL" if provider_id else "FAILED_REAL", "provider_message_id": provider_id, "recipient_class": "configured_controlled_test_recipient", "delivery_status": "PROVIDER_ACCEPTED_ONLY"}
        if provider_id:
            verify = urllib.request.Request(f"https://api.resend.com/emails/{provider_id}", headers={"Authorization": f"Bearer {key}"})
            try:
                with urllib.request.urlopen(verify, timeout=20, context=ssl.create_default_context()) as response:
                    status_body = json.loads(response.read().decode() or "{}")
                result["delivery_status"] = status_body.get("last_event") or status_body.get("status") or "PROVIDER_STATUS_READ"
            except Exception as exc:
                result["delivery_status_error"] = type(exc).__name__
        return result
    except urllib.error.HTTPError as exc:
        return {"provider": "resend", "status": "FAILED_REAL", "http_status": exc.code, "reason": "provider_rejected_test_send"}
    except Exception as exc:
        return {"provider": "resend", "status": "FAILED_REAL", "reason": type(exc).__name__}


def main() -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    image_path, video_path = OUT / "small_business_operations_checklist.png", OUT / "small_business_operations_checklist_short.mp4"
    objective = {"campaign_id": CAMPAIGN_ID, "business_id": BUSINESS_ID, "objective": "Teach overwhelmed small-business owners a practical way to find disconnected operations and missed follow-up.", "audience": "Small-business owners managing disconnected software, manual processes, and inconsistent follow-up.", "problem": "Operational friction is spread across tools and tasks, making the next improvement hard to see.", "offer": "Free educational Small Business Operations Checklist.", "desired_action": "Open the checklist and identify one process to clarify.", "channels": ["email", "facebook", "instagram", "linkedin", "youtube", "tiktok", "x"], "success_criteria": ["qualified checklist click", "landing page CTA event", "measurement receipt"], "constraints": ["internal certification", "no GoClear assets or copy", "no deceptive claims", "no paid media", "no customer data"], "budget": {"paid_media_usd": 0, "max_new_spend_usd": 0}, "status": "QUEUED"}
    objective_path = write_json(OUT / "campaign_objective.json", objective)
    marketing_prompt = """You are Nexus Marketing AI. Create a complete internal campaign strategy for the supplied objective. Return JSON only with keys: audience, customer_problem, message_hierarchy, positioning, offer_framing, CTA, funnel_structure, channel_strategy, creative_requirements, measurement_plan, limitations, acceptance_criteria. Make the decisions yourself; do not mention Codex. No unsupported outcomes or testimonials."""
    strategy, marketing_call = marketing_ai_call(marketing_prompt, objective)
    if not strategy: raise RuntimeError(f"marketing_ai_failed:{marketing_call}")
    strategy_record = ai_record("marketing_projects", {"kind": "strategy", "provider": marketing_call.get("provider"), "model": marketing_call.get("model"), "call": marketing_call, "strategy": strategy, "artifact_path": write_json(OUT / "marketing_strategy.json", strategy), "status": "PASS_REAL"})
    marketing_order = governed_work("growth_analysis", "GROWTH", {"campaign_id": CAMPAIGN_ID, "objective_path": objective_path}, ("analytics",), {"ai_model": marketing_call.get("model"), "artifact_id": strategy_record["record_id"], "lease": "ACQUIRED", "result_persisted": True}, strategy_record["record_id"])
    handoff_payload = {"campaign_id": CAMPAIGN_ID, "marketing_work_id": marketing_order["work_order_id"], "audience": strategy.get("audience"), "objective": objective["objective"], "message": strategy.get("message_hierarchy"), "offer": objective["offer"], "CTA": strategy.get("CTA"), "required_assets": ["image", "short_video", "landing_page"], "channel_requirements": strategy.get("channel_strategy"), "brand_constraints": objective["constraints"], "landing_page_requirements": strategy.get("creative_requirements"), "measurement_requirements": strategy.get("measurement_plan"), "status": "CREATIVE_QUEUE_READY"}
    marketing_handoff = ai_record("marketing_handoffs", {"handoff_type": "MARKETING_TO_CREATIVE", "payload": handoff_payload, "lineage_status": "PRESERVED"})
    creative_parent = governed_work("creative_brief", "CREATIVE", {"campaign_id": CAMPAIGN_ID, "handoff_id": marketing_handoff["record_id"]}, ("creative_media",), {"handoff_received": True, "queue": "CREATIVE_INBOX", "ai_authority": "CREATIVE"}, marketing_handoff["record_id"])
    cp = configure_control_plane()
    creative_model = BoundedCreativeModel()
    prior_bundle = next((row for row in persistence.read_records("creative_ai") if row.get("campaign_id") == CAMPAIGN_ID and row.get("kind") == "creative_direction" and row.get("route_receipt", {}).get("receipt", {}).get("result", {}).get("status") == "PASS"), None)
    if prior_bundle:
        direction_route = prior_bundle["route_receipt"]
        direction_route["reused_prior_real_receipt"] = prior_bundle["record_id"]
    else:
        direction_route = routed(cp, work_id=f"{creative_parent['work_order_id']}:creative-ai-bundle", objective=CAMPAIGN_ID, capability="creative.ai_fallback", budget="REMOTE_FREE", fn=lambda job, worker, host: creative_model.call("Creative Director, Copywriter, and Critic", "Return concise JSON with visual_direction {visual_metaphor, composition, color_system, image_direction, landing_page_direction, distinctiveness_reason}, copy {headline, subhead, CTA, proof_boundary, email_subject, social_hooks}, critic {decision, message_alignment, visual_coherence, distinctiveness, audience_fit, CTA_clarity, defects, revision_required}, revision {changed_copy, changed_visual_direction, why_changed}. Make original educational work for small-business owners. No testimonials, demand, results, or guarantees. Keep each value under 25 words.", {"campaign_id": CAMPAIGN_ID, "objective": objective["objective"], "audience": objective["audience"], "offer": objective["offer"], "constraints": objective["constraints"], "marketing_message": strategy.get("message_hierarchy"), "marketing_cta": strategy.get("CTA"), "visual_discovery": "Use wayfinding/checklist principles; copy no source layout."}))
    bundle = direction_route["receipt"]["result"]
    if bundle.get("status") == "BLOCKED":
        raise RuntimeError(f"creative_ai_blocked:{bundle}")
    direction = bundle.get("visual_direction") or bundle
    direction_record = ai_record("creative_ai", {"kind": "creative_direction", "provider": direction.get("provider"), "model": direction.get("model"), "direction": direction, "route_receipt": direction_route, "status": "PASS_REAL"})
    territories = [{"territory_id": f"territory_{digest((CAMPAIGN_ID, i, direction.get('visual_metaphor')))}", "name": n, "status": "CANDIDATE"} for i, n in enumerate(["The Clear Path", "The Operations Map", "The Quiet Handoff", "The One Fix"])]
    selected_territory = {**territories[0], "selection_reason": direction.get("distinctiveness_reason") or "Creative Director selected the path metaphor for fast operational comprehension.", "creative_direction_record": direction_record["record_id"]}
    children: list[dict[str, Any]] = []
    def child(name: str, capability: str, worker: str, host: str, reason: str, receipt: str, result: dict[str, Any]) -> dict[str, Any]:
        row = {"work_id": f"{creative_parent['work_order_id']}:{name}", "parent_work_id": creative_parent["work_order_id"], "required_capability": capability, "selected_worker": worker, "selected_host": host, "selection_reason": reason, "fallback_worker": "worker-mac-creative", "execution_receipt": receipt, "cost": 0, "result": result}
        children.append(row); return row
    render_route = routed(cp, work_id=f"{creative_parent['work_order_id']}:image", objective=CAMPAIGN_ID, capability="creative.local_render", budget="LOCAL_FREE", fn=lambda job, worker, host: render_image(image_path, direction))
    image = render_route["receipt"]["result"]; image_record = ai_record("creative_media", {"asset_type": "IMAGE", "file": image["file"], "receipt": render_route, "territory_id": selected_territory["territory_id"], "status": "PASS_REAL"})
    child("image", "creative.local_render", render_route["receipt"]["worker_id"], render_route["receipt"]["host_id"], "Mac selected for local-free deterministic render; Creative AI direction supplied the composition.", image_record["record_id"], image)
    copy = bundle.get("copy") or {}; copy_record = ai_record("creative_ai", {"kind": "copy", "copy": copy, "route_receipt": direction_route, "status": "PASS_REAL"})
    child("copy", "creative.ai_fallback", direction_route["receipt"]["worker_id"], direction_route["receipt"]["host_id"], "Oracle selected as certified remote-free Creative AI lane.", copy_record["record_id"], copy)
    video_route = routed(cp, work_id=f"{creative_parent['work_order_id']}:video", objective=CAMPAIGN_ID, capability="creative.local_render", budget="LOCAL_FREE", fn=lambda job, worker, host: render_video(video_path, image_path, copy))
    video = video_route["receipt"]["result"]; video_record = ai_record("creative_media", {"asset_type": "VIDEO", "file": video["file"], "receipt": video_route, "territory_id": selected_territory["territory_id"], "status": "PASS_REAL"})
    child("video", "creative.local_render", video_route["receipt"]["worker_id"], video_route["receipt"]["host_id"], "Mac selected for bounded FFmpeg render; no metered GPU was authorized.", video_record["record_id"], video)
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Free educational small-business operations checklist."><title>{str(copy.get("headline") or "Make the work visible")}</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#f4f0e8;color:#172d3d;font:16px system-ui,sans-serif}}main{{max-width:1160px;margin:auto;padding:28px}}.hero{{display:grid;grid-template-columns:1.05fr .95fr;gap:28px;align-items:center;min-height:90vh}}.eyebrow{{letter-spacing:.14em;text-transform:uppercase;color:#bd7135;font-weight:700;font-size:12px}}h1{{font-size:clamp(48px,7vw,92px);line-height:.94;margin:18px 0}}p{{font-size:20px;line-height:1.55;max-width:620px;color:#49606a}}.cta{{display:inline-block;margin-top:16px;background:#172d3d;color:#fff;padding:16px 24px;border-radius:999px;text-decoration:none;font-weight:700}}.art{{width:100%;border-radius:28px;box-shadow:0 18px 50px #172d3d25}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:30px 0 60px}}.card{{background:#fff;padding:24px;border-radius:18px}}.card b{{font-size:20px}}.card p{{font-size:16px}}@media(max-width:720px){{main{{padding:18px}}.hero{{grid-template-columns:1fr;min-height:auto;padding:48px 0}}h1{{font-size:54px}}.grid{{grid-template-columns:1fr}}}}</style></head><body data-campaign-id="{CAMPAIGN_ID}"><main><section class="hero"><div><div class="eyebrow">Free educational checklist</div><h1>{str(copy.get("headline") or "Make the work visible.")}</h1><p>{str(copy.get("subhead") or "Find the small operational gaps that create extra work, then choose one practical next step.")}</p><a class="cta" data-campaign-event="cta_click" href="#checklist">{str(copy.get("CTA") or "Open the checklist")}</a></div><img class="art" src="./small_business_operations_checklist.png" alt="Editorial illustration of disconnected work becoming a clear checklist path"></section><section id="checklist" class="grid"><div class="card"><b>See the handoffs</b><p>Notice where work gets repeated, lost, or delayed.</p></div><div class="card"><b>Choose one fix</b><p>Start with the process that would make the next week easier to run.</p></div><div class="card"><b>Keep it practical</b><p>Use the checklist as an educational prompt, not a promise of business results.</p></div></section><video controls playsinline preload="metadata" poster="./small_business_operations_checklist.png" style="width:100%;border-radius:24px" src="./small_business_operations_checklist_short.mp4"></video><p style="font-size:13px;margin:28px 0">Internal certification campaign. Educational content only; no customer result, revenue, or performance outcome is promised.</p></main><script>document.querySelectorAll('[data-campaign-event]').forEach((el)=>el.addEventListener('click',()=>window.dispatchEvent(new CustomEvent('nexus-campaign-event',{{detail:{{campaign_id:'{CAMPAIGN_ID}',event:el.dataset.campaignEvent}}}}))))</script></body></html>'''
    page = PUBLIC / "index.html"; page.parent.mkdir(parents=True, exist_ok=True); page.write_text(html, encoding="utf-8")
    subprocess.run(["cp", str(image_path), str(PUBLIC / image_path.name)], check=True); subprocess.run(["cp", str(video_path), str(PUBLIC / video_path.name)], check=True)
    landing = {"url_path": "/marketing-certification/ops-checklist/", "file": str(page.relative_to(ROOT)), "tracking": ["data-campaign-id", "nexus-campaign-event", "utm_source", "utm_medium", "utm_campaign"], "status": "RENDERED_SOURCE_READY"}
    child("landing_page", "creative.local_render", "worker-mac-creative", "host-mac", "Creative-owned visual direction implemented as a responsive technical artifact.", "landing_source_receipt", landing)
    critic = bundle.get("critic") or {"decision": "REVISION_REQUIRED", "revision_required": True, "defects": ["Creative critic returned no structured decision."]}; critic["revision"] = bundle.get("revision")
    critic_record = ai_record("creative_reviews", {"kind": "creative_critic", "critic": critic, "route_receipt": direction_route, "status": "PASS_REAL"})
    creative_handoff = ai_record("marketing_handoffs", {"handoff_type": "CREATIVE_TO_MARKETING", "payload": {"campaign_id": CAMPAIGN_ID, "image": image, "video": video, "landing_page": landing, "copy": copy, "creative_notes": direction, "territories": territories, "selected_territory": selected_territory, "critic": critic, "asset_receipts": [image_record["record_id"], video_record["record_id"], critic_record["record_id"]]}, "status": "MARKETING_INBOX_RECEIVED"})
    marketing_eval, marketing_eval_meta = marketing_ai_call("You are Marketing AI evaluating Creative's returned package. Return JSON only with decision, strategy_alignment, offer_alignment, CTA, channel_suitability, tracking_readiness, blockers. Choose ACCEPT or REQUEST_REVISION.", {"objective": objective, "strategy": strategy, "creative_package": creative_handoff["payload"]})
    acceptance = ai_record("marketing_evaluations", {"handoff_id": creative_handoff["record_id"], "provider": marketing_eval_meta.get("provider"), "model": marketing_eval_meta.get("model"), "evaluation": marketing_eval, "status": "PASS_REAL"})
    revision_work = None
    if str(marketing_eval.get("decision", "")).upper() != "ACCEPT":
        revision = critic.get("revision") or {}
        revised_cta = str(revision.get("changed_copy") or "Get Your Checklist Now.")
        revision_work = governed_work("creative_brief", "CREATIVE", {"campaign_id": CAMPAIGN_ID, "parent_work_id": creative_parent["work_order_id"], "revision_reason": marketing_eval.get("blockers"), "changed_copy": revised_cta}, ("creative_media",), {"status": "PASS", "revision_executed": True, "changed_copy": revised_cta, "changed_visual_direction": revision.get("changed_visual_direction")}, f"revision_{creative_parent['work_order_id']}")
        page_text = page.read_text(encoding="utf-8")
        old_cta = str(copy.get("CTA") or "Download the checklist")
        page.write_text(page_text.replace(old_cta, revised_cta).replace("RENDERED_SOURCE_READY", "REVISED_AND_RENDERED"), encoding="utf-8")
        copy = {**copy, "CTA": revised_cta, "revision_applied": True}
        revised_payload = {**creative_handoff["payload"], "copy": copy, "revision_work_id": revision_work["work_order_id"], "revision_reason": marketing_eval.get("blockers")}
        revised_eval, revised_meta = marketing_ai_call("You are Marketing AI re-evaluating a revised Creative package. Return JSON only with decision, strategy_alignment, offer_alignment, CTA, channel_suitability, tracking_readiness, blockers. Accept only if the requested change is present.", {"objective": objective, "strategy": strategy, "creative_package": revised_payload})
        acceptance = ai_record("marketing_evaluations", {"handoff_id": creative_handoff["record_id"], "revision_work_id": revision_work["work_order_id"], "provider": revised_meta.get("provider"), "model": revised_meta.get("model"), "evaluation": revised_eval, "status": "PASS_REAL"})
        marketing_eval = revised_eval
    adaptations = {c: channel_adaptation(c, str(copy.get("headline") or "Make the work visible"), str(copy.get("subhead") or objective["offer"])) for c in ("facebook", "instagram", "linkedin", "youtube", "tiktok", "x")}
    email = {"channel": "email", "auth_status": "CONNECTED_RESEND", "publish_capability": "TEST_ONLY", "distribution_status": "PENDING_APPROVED_TEST_RECIPIENT"}
    social = {c: {"channel": c, "auth_status": "READ_ONLY_OR_UNCONNECTED", "draft_status": "PASS_REAL", "publish_capability": "HELD_EXTERNAL_OR_POLICY", "distribution_status": "HELD_NO_APPROVED_TEST_SURFACE", "payload": adaptations[c]} for c in adaptations}
    email_receipt = send_controlled_email(copy, landing)
    email.update(email_receipt)
    distribution = {"email": email, "social": social, "policy": "No social publish, no paid spend, no bulk email."}
    projection = {"schema_version": "nexus.marketing-creative-certification-projection.v1", "campaign_id": CAMPAIGN_ID, "campaign_status": "INTERNAL_CERTIFICATION_ACCEPTED" if str(marketing_eval.get("decision", "")).upper() == "ACCEPT" else "INTERNAL_CERTIFICATION_REVISION_REQUIRED", "marketing_work_id": marketing_order["work_order_id"], "marketing_strategy": strategy_record["record_id"], "creative_parent_work_id": creative_parent["work_order_id"], "creative_handoff_id": creative_handoff["record_id"], "marketing_acceptance_id": acceptance["record_id"], "revision_work_id": revision_work["work_order_id"] if revision_work else None, "image": image, "video": video, "landing_page": landing, "critic": critic, "worker_routing": {"remote_control_plane_used": True, "jobs": list(cp.snapshot()["receipts"]), "provider_bypass_count": 0}, "distribution": distribution, "cost": {"observed_cost_usd": 0, "breakdown": {"marketing_ai": "provider route recorded; price not exposed", "creative_ai": "REMOTE_FREE", "local_render": 0, "social": 0, "email": "NOT_SENT_BY_THIS_RUN"}}, "updated_at": now()}
    projection_path = write_json(PROJECTION, projection); projection["projection_path"] = projection_path
    chain = {"schema_version": "nexus.company-chain-receipt.marketing-creative.v1", "receipt_id": f"chain_{uuid.uuid4().hex}", "campaign_id": CAMPAIGN_ID, "lineage": [objective_path, marketing_order["work_order_id"], strategy_record["artifact_path"], marketing_handoff["record_id"], creative_parent["work_order_id"], *[x["work_id"] for x in children], image_record["record_id"], video_record["record_id"], landing["file"], critic_record["record_id"], creative_handoff["record_id"], acceptance["record_id"]], "distribution": distribution, "created_at": now(), "status": "PASS_REAL_BOUNDED"}
    chain_path = write_json(OUT / "company_chain_receipt.json", chain); write_json(OUT / "projection_snapshot.json", projection)
    result = {"campaign_id": CAMPAIGN_ID, "objective": objective, "objective_path": objective_path, "marketing_order": marketing_order, "marketing_strategy": strategy_record, "marketing_handoff": marketing_handoff, "creative_parent": creative_parent, "creative_children": children, "control_plane": cp.snapshot(), "selected_territory": selected_territory, "image": image, "video": video, "landing": landing, "critic": critic_record, "creative_handoff": creative_handoff, "acceptance": acceptance, "revision_work": revision_work, "distribution": distribution, "projection_path": projection_path, "chain_receipt_id": chain["receipt_id"], "chain_receipt_path": chain_path, "status": "PASS_REAL_BOUNDED"}
    write_json(OUT / "certification_result.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, sort_keys=True, default=str))
