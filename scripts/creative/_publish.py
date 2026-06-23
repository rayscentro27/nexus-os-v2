"""Nexus OS v2 — Manual Publish Readiness core (Day 10). Deterministic; NO real publishing,
NO Facebook/Instagram API, NO external model/image calls.

Turns a winning creative_design_variant into an approval-gated, manual publish-ready package
(final copy + image prompt/design notes + CTA + compliance footer + risk flags + manual posting
instructions + dry-run receipt). Credit/funding copy is compliance-enforced.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "social"))
sys.path.insert(0, str(HERE.parent / "compliance"))
from _supabase import get, insert, update, event, q  # noqa: E402
import classify_claim_risk as claim  # noqa: E402
import _design  # noqa: E402

FOOTER = ("Results vary. No guaranteed credit score increase, deletion, funding approval, or "
          "financing outcome — education and readiness only.")
SAMPLE_KEY = "goclear_credit_readiness_pub"
HASHTAGS = ["#FundingReadiness", "#BusinessCredit", "#GoClear"]


def _is_credit_funding(text: str) -> bool:
    return any(w in (text or "").lower() for w in ("credit", "funding", "loan", "lender", "readiness", "score"))


def _sample_winning_variant():
    """Day 9 GoClear sample brief → its comparison winner (fall back to a copy variant)."""
    brief = _design.get_or_create_sample_brief()
    st, cmps = get("creative_asset_comparisons", f"design_brief_id=eq.{q(brief['id'])}&select=id,winning_variant_id&order=created_at.desc&limit=1")
    comparison_id = cmps[0]["id"] if isinstance(cmps, list) and cmps else None
    win_id = cmps[0]["winning_variant_id"] if isinstance(cmps, list) and cmps else None
    variant = None
    if win_id:
        st, v = get("creative_design_variants", f"id=eq.{q(win_id)}&select=*&limit=1")
        variant = v[0] if isinstance(v, list) and v else None
    # prefer a variant that actually has post copy
    if not variant or not variant.get("post_copy"):
        st, v = get("creative_design_variants", f"design_brief_id=eq.{q(brief['id'])}&route_key=eq.compliance_safe_text_overlay&select=*&limit=1")
        if isinstance(v, list) and v:
            variant = v[0]
    return brief, variant, comparison_id


def build_package(*, design_variant_id=None, comparison_id=None, platform="facebook", sample=False) -> dict:
    brief = None
    variant = None
    if sample or (not design_variant_id and not comparison_id):
        brief, variant, comparison_id = _sample_winning_variant()
    elif design_variant_id:
        st, v = get("creative_design_variants", f"id=eq.{q(design_variant_id)}&select=*&limit=1")
        variant = v[0] if isinstance(v, list) and v else None
    elif comparison_id:
        st, c = get("creative_asset_comparisons", f"id=eq.{q(comparison_id)}&select=winning_variant_id&limit=1")
        wid = c[0]["winning_variant_id"] if isinstance(c, list) and c else None
        if wid:
            st, v = get("creative_design_variants", f"id=eq.{q(wid)}&select=*&limit=1")
            variant = v[0] if isinstance(v, list) and v else None
    if not variant:
        return {"ok": False, "blocker": "no source variant found"}

    brief_id = variant.get("design_brief_id")
    if not brief:
        st, b = get("creative_design_briefs", f"id=eq.{q(brief_id)}&select=*&limit=1")
        brief = b[0] if isinstance(b, list) and b else {}

    # final copy: prefer variant copy; otherwise compose a safe line from the brief.
    copy = variant.get("post_copy") or (
        f"Getting funding-ready starts before you apply. {brief.get('visual_metaphor') or 'An open path forward'} — "
        "organize your business profile, documents, and credit readiness first.")
    credit = _is_credit_funding(copy + " " + (brief.get("offer") or ""))
    footer = FOOTER if credit else None
    if footer and footer.lower() not in copy.lower():
        copy = copy.rstrip() + "\n\n" + footer

    risk = claim.classify(copy)
    risk_high = risk["risk_class"] in ("misleading_or_hype", "do_not_use_client_facing")
    compliance_status = "needs_revision" if risk_high else ("ok" if credit and footer else "needs_review")
    cta = (brief.get("required_text") or {}).get("cta") or variant.get("cta") or "Start your funding readiness review."

    instructions = (
        f"MANUAL POSTING (no auto-publish):\n"
        f"1) Review and approve this package in the dashboard first.\n"
        f"2) On {platform}: create a new post on the Clear Credentials page.\n"
        f"3) Paste the final post copy exactly (it already includes the compliance footer).\n"
        f"4) Use the image prompt/design notes to create the visual separately; do not bake text claims into the image.\n"
        f"5) Add the CTA and hashtags. Post manually. Nexus does not auto-post.\n"
        f"6) Optionally paste the live post URL back via create_manual_publish_receipt for proof.")
    dry_receipt = {"dry_run": True, "published": False, "platform": platform,
                   "note": "Publish readiness only — no API call, no post created."}

    pkg = {
        "design_brief_id": brief_id, "design_variant_id": variant["id"], "comparison_id": comparison_id,
        "platform": platform, "package_title": (brief.get("title") or "Publish package") + " — manual package",
        "final_post_copy": copy, "image_prompt": variant.get("image_prompt"),
        "design_notes": variant.get("layout_notes") or variant.get("background_concept"),
        "cta": cta, "compliance_footer": footer, "hashtags": HASHTAGS if credit else [],
        "risk_flags": risk["flags"], "compliance_status": compliance_status,
        "approval_status": "pending", "manual_posting_instructions": instructions,
        "dry_run_receipt": dry_receipt, "status": "draft",
        "metadata": {"sample_key": SAMPLE_KEY if sample else None, "claim_risk": risk["risk_class"], "credit_funding": credit},
    }

    # idempotent for the sample
    if sample:
        st, ex = get("publish_readiness_packages", f"metadata->>sample_key=eq.{SAMPLE_KEY}&select=id&limit=1")
        if isinstance(ex, list) and ex:
            return {"ok": True, "package_id": ex[0]["id"], "existed": True, "compliance_status": compliance_status}

    st, row = insert("publish_readiness_packages", pkg)
    pid = row[0]["id"] if isinstance(row, list) and row else None

    # approval (pending) — required before any real publish
    st, arow = insert("approvals", {
        "lane": "creative", "item_type": "publish_package", "item_id": pid, "status": "pending",
        "title": f"Approve manual publish package: {pkg['package_title']}",
        "summary": "Manual publish readiness only — no real post. Approve before any future real publish.",
        "payload": {"package_id": pid, "platform": platform, "caption": copy[:240],
                    "compliance_status": compliance_status, "risk_flags": risk["flags"]}})
    appr_id = arow[0]["id"] if isinstance(arow, list) and arow else None
    if pid and appr_id:
        update("publish_readiness_packages", f"id=eq.{q(pid)}", {"approval_id": appr_id})

    event("monetization", "publish_package_created", "success",
          f"Publish package: {pkg['package_title']}",
          f"compliance={compliance_status} risk_flags={', '.join(risk['flags']) or 'none'} (no real publish)",
          payload={"package_id": pid, "approval_id": appr_id})
    return {"ok": True, "package_id": pid, "approval_id": appr_id, "compliance_status": compliance_status,
            "risk_flags": risk["flags"], "footer": footer is not None}


def _resolve_pkg(package_id=None, sample=False):
    if sample or not package_id:
        st, rows = get("publish_readiness_packages", f"metadata->>sample_key=eq.{SAMPLE_KEY}&select=*&order=created_at.desc&limit=1")
        if not (isinstance(rows, list) and rows):
            r = build_package(sample=True)
            return _resolve_pkg(r.get("package_id"))
        return rows[0]
    st, rows = get("publish_readiness_packages", f"id=eq.{q(package_id)}&select=*&limit=1")
    return rows[0] if isinstance(rows, list) and rows else None


def review_package(package_id=None, sample=False) -> dict:
    pkg = _resolve_pkg(package_id, sample)
    if not pkg:
        return {"ok": False, "blocker": "package not found"}
    text = " ".join(str(pkg.get(k) or "") for k in ("final_post_copy", "cta", "image_prompt", "design_notes"))
    risk = claim.classify(text)
    has_footer = bool(pkg.get("compliance_footer"))
    credit = (pkg.get("metadata") or {}).get("credit_funding")
    compliance = 20 if risk["risk_class"] in ("misleading_or_hype", "do_not_use_client_facing") else (
        95 if (has_footer or not credit) else 60)
    clarity = 88 if 20 <= len(text.split()) <= 220 else 70
    cta_strength = 85 if pkg.get("cta") else 50
    score = round((compliance + clarity + cta_strength + 85) / 4)  # +85 brand/platform baseline
    notes = []
    if compliance < 80:
        notes.append("Remove guarantee/claim language; keep the no-guarantee footer.")
        decision = "compliance_review_required" if risk["risk_class"] != "misleading_or_hype" else "reject"
    elif not has_footer and credit:
        notes.append("Add the compliance footer for credit/funding content."); decision = "revise_copy"
    elif score >= 80:
        decision = "approve_manual_use"
    else:
        decision = "revise_copy"

    insert("publish_package_reviews", {"package_id": pkg["id"], "review_type": "compliance", "score": score,
           "decision": decision, "reason": f"claim_risk={risk['risk_class']}", "revision_notes": notes,
           "risk_flags": risk["flags"]}, prefer="return=minimal")
    update("publish_readiness_packages", f"id=eq.{q(pkg['id'])}",
           {"compliance_status": "ok" if compliance >= 80 else "needs_revision",
            "status": "ready_for_approval" if decision == "approve_manual_use" else "needs_revision"})
    event("monetization", "publish_package_reviewed", "success", f"Publish review: {decision} ({score}/100)",
          f"compliance={compliance}", payload={"package_id": pkg["id"]})
    return {"ok": True, "package_id": pkg["id"], "decision": decision, "score": score, "compliance": compliance}


def create_receipt(package_id=None, platform="facebook", dry_run=True, posted_url=None, proof_notes=None, sample=False) -> dict:
    pkg = _resolve_pkg(package_id, sample)
    if not pkg:
        return {"ok": False, "blocker": "package not found"}
    rtype = "manual_proof" if (posted_url and not dry_run) else "dry_run"
    summary = ("Dry-run receipt — publish readiness only, no post created."
               if rtype == "dry_run" else f"Manual proof of a post Ray published himself: {posted_url}")
    insert("manual_publish_receipts", {"package_id": pkg["id"], "platform": platform, "receipt_type": rtype,
           "summary": summary, "external_url": posted_url, "proof_notes": proof_notes,
           "metadata": {"dry_run": dry_run, "approval_status": pkg.get("approval_status")}}, prefer="return=minimal")
    event("social", "manual_publish_receipt", "success", f"Manual publish receipt ({rtype})",
          summary, payload={"package_id": pkg["id"]})
    return {"ok": True, "package_id": pkg["id"], "receipt_type": rtype}


def export_markdown(package_id=None, output="/tmp/nexus_publish_package.md", sample=False) -> dict:
    pkg = _resolve_pkg(package_id, sample)
    if not pkg:
        return {"ok": False, "blocker": "package not found"}
    rr = pkg.get("dry_run_receipt") or {}
    md = f"""# {pkg['package_title']}

- Platform: **{pkg['platform']}**
- Approval status: **{pkg['approval_status']}** · Compliance: **{pkg['compliance_status']}**
- Risk flags: {', '.join(pkg.get('risk_flags') or []) or 'none'}

## Final post copy
{pkg['final_post_copy']}

## CTA
{pkg.get('cta') or '—'}

## Hashtags
{' '.join(pkg.get('hashtags') or []) or '—'}

## Image prompt / design notes
{pkg.get('image_prompt') or pkg.get('design_notes') or '—'}

## Compliance footer
{pkg.get('compliance_footer') or '(none required)'}

## Manual posting instructions
{pkg.get('manual_posting_instructions') or '—'}

## Dry-run receipt
{json.dumps(rr)}

> Manual publish readiness only. No real post was created. Approval is required before any real publish.
"""
    Path(output).write_text(md)
    event("monetization", "publish_package_exported", "success", "Publish package exported",
          f"-> {output}", payload={"package_id": pkg["id"]})
    return {"ok": True, "package_id": pkg["id"], "output": output}
