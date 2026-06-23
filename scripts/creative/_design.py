"""Nexus OS v2 — Creative Design Department core (deterministic, no external image/model calls).

Shared by the create/generate/score/compare CLI scripts. Enforces compliance-safe copy for
credit/funding content (no guaranteed funding/approval/deletions/score increases; adds a
"results vary / no guarantees" footer).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "social"))
sys.path.insert(0, str(HERE.parent / "compliance"))
from _supabase import get, insert, event, q  # noqa: E402
import classify_claim_risk as claim  # noqa: E402

ROUTES = ["claude_design_prompt", "image_generator_prompt", "fintech_dashboard_style",
          "metaphor_background_style", "compliance_safe_text_overlay"]
FOOTER = ("Results vary. No guaranteed funding, approval, deletions, or score increases — "
          "education and readiness only.")
SAMPLE_BRIEF_KEY = "goclear_credit_readiness_fb"


def is_sensitive(brief: dict) -> bool:
    blob = " ".join(str(brief.get(k) or "") for k in ("offer", "audience", "title", "image_concept")).lower()
    return any(w in blob for w in ("credit", "funding", "loan", "lender", "readiness"))


def create_brief(fields: dict) -> str | None:
    st, row = insert("creative_design_briefs", fields)
    bid = row[0]["id"] if isinstance(row, list) and row else None
    event("monetization", "design_brief_created", "success", f"Design brief: {fields.get('title')}",
          f"platform={fields.get('platform')}", payload={"design_brief_id": bid})
    return bid


def _variant_for(route: str, brief: dict, sensitive: bool) -> dict:
    hook = brief.get("visual_metaphor") or "An open gate and an upward path"
    aud = brief.get("audience") or "small business owners getting funding-ready"
    offer = brief.get("offer") or "Funding Readiness Review"
    safe_copy = (f"Getting funding-ready starts before you apply. {hook} — organize your business "
                 f"profile, documents, and credit readiness first. {FOOTER}")
    base = {"design_brief_id": brief["id"], "route_key": route, "status": "draft",
            "metadata": {"sensitive": sensitive, "compliance_footer": sensitive}}
    if route == "claude_design_prompt":
        base.update(variant_type="design_prompt", title="Claude design prompt — premium FB post",
                    post_copy=safe_copy,
                    layout_notes="Premium dark-navy card, gold accent, single clear headline, small compliance footer, one CTA.",
                    image_prompt=None, background_concept="dark navy gradient with subtle gold path")
    elif route == "image_generator_prompt":
        base.update(variant_type="image_prompt", title="Image generator prompt — open gate / upward path",
                    image_prompt=(f"Editorial illustration: {hook}, sunrise tones, a clear path leading "
                                  "upward through an open gate; hopeful but realistic; no text baked in; "
                                  "leave space for an overlay headline. Avoid logos and real people."),
                    background_concept=hook, layout_notes="16:9 and 1:1 crops; keep top-left clear for headline.")
    elif route == "fintech_dashboard_style":
        base.update(variant_type="layout", title="Fintech dashboard style card",
                    layout_notes="Card grid, generous whitespace, trust badges, muted palette + one accent; "
                                 "readability-first typography; mobile-stacked.",
                    background_concept="clean light surface with one accent", post_copy=safe_copy)
    elif route == "metaphor_background_style":
        base.update(variant_type="background", title="Metaphor background — gate + path",
                    background_concept=f"{hook}; soft depth-of-field; calm, trustworthy",
                    image_prompt=f"Background only: {hook}, muted premium tones, copy-safe negative space.")
    else:  # compliance_safe_text_overlay
        base.update(variant_type="copy_overlay", title="Compliance-safe text overlay",
                    post_copy=safe_copy,
                    layout_notes="Headline + 1 subline + CTA + small footer; high contrast; no guarantee words.")
    return base


def generate_variants(brief: dict) -> list[str]:
    # Idempotent: if this brief already has variants, don't regenerate.
    st, existing = get("creative_design_variants", f"design_brief_id=eq.{q(brief['id'])}&select=id")
    if isinstance(existing, list) and existing:
        return [e["id"] for e in existing]
    sensitive = is_sensitive(brief)
    ids = []
    for route in ROUTES:
        v = _variant_for(route, brief, sensitive)
        # compliance guard: never ship banned claims in post copy
        if v.get("post_copy"):
            risk = claim.classify(v["post_copy"])
            if risk["risk_class"] in ("misleading_or_hype", "do_not_use_client_facing"):
                v["post_copy"] = (v["post_copy"].split(".")[0] + ". " + FOOTER)  # fall back to safe minimal
            v["metadata"] = {**v.get("metadata", {}), "claim_risk": risk["risk_class"]}
        st, row = insert("creative_design_variants", v)
        if isinstance(row, list) and row:
            ids.append(row[0]["id"])
    event("monetization", "design_variants_generated", "success",
          f"Generated {len(ids)} design variants", f"brief={brief.get('title')}",
          payload={"design_brief_id": brief["id"]})
    return ids


def score_variants(brief_id: str) -> list[dict]:
    st, variants = get("creative_design_variants", f"design_brief_id=eq.{q(brief_id)}&select=*")
    out = []
    for v in (variants if isinstance(variants, list) else []):
        st2, sc = get("creative_design_scores", f"design_variant_id=eq.{q(v['id'])}&select=id&limit=1")
        if isinstance(sc, list) and sc:
            continue  # already scored
        text = " ".join(str(v.get(k) or "") for k in ("title", "post_copy", "image_prompt", "layout_notes"))
        risk = claim.classify(text)
        compliance = 20 if risk["risk_class"] in ("misleading_or_hype", "do_not_use_client_facing") else (
            95 if "no guarantee" in text.lower() or "results vary" in text.lower() else 80)
        s = {
            "design_variant_id": v["id"],
            "hook_strength": 85 if v.get("post_copy") else 70,
            "trust_score": 90 if v["metadata"].get("compliance_footer") else 75,
            "brand_fit": 85, "readability": 88,
            "compliance_safety": compliance,
            "emotional_clarity": 84 if "path" in text.lower() or "gate" in text.lower() else 70,
            "cta_strength": 80 if "review" in text.lower() or "start" in text.lower() else 60,
            "platform_fit": 88,
            "risk_flags": risk["flags"],
        }
        s["overall_score"] = round(sum(s[k] for k in ("hook_strength", "trust_score", "brand_fit", "readability",
                                       "compliance_safety", "emotional_clarity", "cta_strength", "platform_fit")) / 8)
        s["recommendation"] = "approve_candidate" if s["overall_score"] >= 80 and compliance >= 80 else "revise"
        insert("creative_design_scores", s, prefer="return=minimal")
        out.append({"variant_id": v["id"], "route": v["route_key"], "overall": s["overall_score"], "compliance": compliance})
    event("monetization", "design_variants_scored", "success", f"Scored {len(out)} variants",
          f"brief={brief_id}", payload={"design_brief_id": brief_id})
    return out


def compare_variants(brief_id: str) -> dict:
    scored = score_variants(brief_id) if False else None  # scoring is a separate step; read existing
    st, variants = get("creative_design_variants", f"design_brief_id=eq.{q(brief_id)}&select=id,route_key")
    best = None
    for v in (variants if isinstance(variants, list) else []):
        st, sc = get("creative_design_scores", f"design_variant_id=eq.{q(v['id'])}&select=overall_score,compliance_safety&order=created_at.desc&limit=1")
        ov = sc[0]["overall_score"] if isinstance(sc, list) and sc else 0
        comp = sc[0]["compliance_safety"] if isinstance(sc, list) and sc else 0
        if comp >= 80 and (best is None or ov > best["overall"]):
            best = {"variant_id": v["id"], "route": v["route_key"], "overall": ov}
    if not best:
        summary, reason, win = "No compliant winner", "All variants failed compliance threshold", None
        action = "revise"
    else:
        summary = f"Winner: {best['route']} (overall {best['overall']})"
        reason = "Highest overall score among compliance-safe variants (>=80 compliance)."
        win = best["variant_id"]
        action = "approve" if best["overall"] >= 82 else "revise"
    st, row = insert("creative_asset_comparisons", {
        "design_brief_id": brief_id, "winning_variant_id": win, "summary": summary,
        "reason": reason, "next_action": action, "approval_required": True})
    event("monetization", "design_variants_compared", "success", summary, reason,
          payload={"design_brief_id": brief_id})
    return {"summary": summary, "winning_variant_id": win, "next_action": action}


def get_or_create_sample_brief() -> dict:
    st, rows = get("creative_design_briefs", f"metadata->>sample_key=eq.{SAMPLE_BRIEF_KEY}&select=*&limit=1")
    if isinstance(rows, list) and rows:
        return rows[0]
    bid = create_brief({
        "title": "GoClear Credit Readiness — Facebook post", "platform": "facebook",
        "audience": "small business owners getting funding-ready",
        "offer": "GoClear/Apex Funding Readiness Review", "tone": "hopeful, trustworthy, realistic",
        "visual_metaphor": "An open gate and an upward path",
        "image_concept": "Open gate at sunrise with a clear path forward; no guarantees implied",
        "compliance_rules": ["no guaranteed funding", "no guaranteed approval", "no deletions promise",
                             "no score-increase promise", "include results-vary footer"],
        "required_text": {"footer": FOOTER, "cta": "Start your funding readiness review."},
        "avoid_text": ["guaranteed", "guaranteed approval", "delete your debt", "wipe inquiries", "score increase guaranteed"],
        "status": "draft", "metadata": {"sample_key": SAMPLE_BRIEF_KEY},
    })
    st, rows = get("creative_design_briefs", f"id=eq.{q(bid)}&select=*&limit=1")
    return rows[0] if isinstance(rows, list) and rows else {"id": bid, "title": "sample"}
