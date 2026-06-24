#!/usr/bin/env python3
"""Manual Nexus activation loop.

Bounded, operator-run command. It does not install a scheduler, run forever, print
secrets, buy ads, mass email, or trade live funds.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "social"))
import _supabase as sb  # noqa: E402

REPORT_DIR = ROOT / "reports" / "runtime"
MANUAL_DIR = ROOT / "reports" / "manual_publish"
LANDING_PAGE = ROOT / "public" / "goclear-apex-readiness.html"
LOCK_FILE = REPORT_DIR / "nexus_watch.lock"
CAMPAIGN_KEY = "goclear_apex_97_readiness_activation"
DISCLAIMER = "Education/readiness only. No guaranteed funding, approval, score change, or deletion outcome."


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def env_present(*names: str) -> list[str]:
    return [name for name in names if sb.ENV.get(name)]


def env_missing(*names: str) -> list[str]:
    return [name for name in names if not sb.ENV.get(name)]


def secret_post(url: str, body: dict, headers: dict, timeout: int = 30) -> tuple[bool, dict]:
    data = json.dumps(body).encode()
    headers = {"User-Agent": "nexus-os-v2/1.0", **headers}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        context = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
            raw = resp.read().decode(errors="ignore")
            return True, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="ignore")
        return False, {"status": exc.code, "error": raw[:220]}
    except Exception as exc:  # noqa: BLE001
        return False, {"error": str(exc)[:220]}


def secret_get(url: str, headers: dict, timeout: int = 30) -> tuple[bool, dict]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        context = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
            raw = resp.read().decode(errors="ignore")
            return True, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="ignore")
        return False, {"status": exc.code, "error": raw[:220]}
    except Exception as exc:  # noqa: BLE001
        return False, {"error": str(exc)[:220]}


def integration_summary() -> dict:
    netlify_required = ("NETLIFY_AUTH_TOKEN", "NETLIFY_SITE_ID")
    resend_required = ("RESEND_API_KEY", "RESEND_FROM_EMAIL")
    resend_recipients = ("RESEND_TO_EMAIL", "RAY_EMAIL", "RESEND_TEST_TO", "TO_EMAIL", "TEST_EMAIL")
    meta_names = ("META_PAGE_ACCESS_TOKEN", "FACEBOOK_PAGE_ACCESS_TOKEN", "META_PAGE_ID", "FACEBOOK_PAGE_ID", "META_INSTAGRAM_ACCOUNT_ID", "INSTAGRAM_BUSINESS_ACCOUNT_ID")
    tiktok_names = ("TIKTOK_ACCESS_TOKEN", "TIKTOK_CLIENT_KEY", "TIKTOK_OPEN_ID")
    oanda_names = ("OANDA_ENV", "OANDA_ENVIRONMENT", "OANDA_PRACTICE", "TRADING_MODE", "BROKER_ENV", "OANDA_API_KEY", "OANDA_ACCESS_TOKEN", "OANDA_ACCOUNT_ID", "PAPER_ONLY", "LIVE_TRADING", "NEXUS_DRY_RUN", "TRADING_LIVE_EXECUTION_ENABLED")
    trading_values = {
        "OANDA_ENV": sb.ENV.get("OANDA_ENV", "").lower(),
        "OANDA_ENVIRONMENT": sb.ENV.get("OANDA_ENVIRONMENT", "").lower(),
        "OANDA_PRACTICE": sb.ENV.get("OANDA_PRACTICE", "").lower(),
        "TRADING_MODE": sb.ENV.get("TRADING_MODE", "").lower(),
        "BROKER_ENV": sb.ENV.get("BROKER_ENV", "").lower(),
        "PAPER_ONLY": sb.ENV.get("PAPER_ONLY", "").lower(),
        "NEXUS_DRY_RUN": sb.ENV.get("NEXUS_DRY_RUN", "").lower(),
        "LIVE_TRADING": sb.ENV.get("LIVE_TRADING", "").lower(),
        "TRADING_LIVE_EXECUTION_ENABLED": sb.ENV.get("TRADING_LIVE_EXECUTION_ENABLED", "").lower(),
    }
    demo = any(v in {"practice", "demo", "paper", "sandbox"} for v in trading_values.values())
    demo = demo or trading_values["PAPER_ONLY"] == "true" or trading_values["NEXUS_DRY_RUN"] == "true"
    live = any(v in {"live", "real", "funded"} for v in trading_values.values())
    live = live or trading_values["LIVE_TRADING"] == "true" or trading_values["TRADING_LIVE_EXECUTION_ENABLED"] == "true"
    # Netlify is deployed via GitHub (push main → Netlify build). That path does NOT need local
    # NETLIFY_AUTH_TOKEN / NETLIFY_SITE_ID — those are only for CLI/API verification. So detect the
    # GitHub-connected mode by (a) a committed netlify.toml and (b) a configured public URL.
    netlify_url_names = ("NEXUS_NETLIFY_PUBLIC_URL", "VITE_GOCLEAR_PUBLIC_URL", "NETLIFY_SITE_URL", "URL", "DEPLOY_PRIME_URL", "DEPLOY_URL")
    netlify_public_url = first_env(*netlify_url_names).strip()
    netlify_cli_capable = not env_missing(*netlify_required)
    netlify_toml = (ROOT / "netlify.toml").exists()
    if netlify_public_url:
        netlify_connected: object = True
        netlify_mode = "github_connected_public_url"
        netlify_status = "public_url_configured_needs_live_verification"
        netlify_blocker = None
    elif netlify_toml or netlify_cli_capable:
        netlify_connected = "unknown"
        netlify_mode = "github_connected_assumed"
        netlify_status = "github_connected_assumed_no_public_url"
        netlify_blocker = "missing_public_url_in_repo_or_env"
    else:
        netlify_connected = False
        netlify_mode = "not_configured"
        netlify_status = "not_configured"
        netlify_blocker = "missing_public_url_in_repo_or_env"
    return {
        "netlify": {
            "connected": netlify_connected,
            "deploy_mode": netlify_mode,
            "public_url": netlify_public_url or None,
            "status": netlify_status,
            "blocker": netlify_blocker,
            "cli_capable": netlify_cli_capable,
            "present_names": env_present(*netlify_required, *netlify_url_names),
            "missing_names": env_missing(*netlify_required),
            "netlify_toml": netlify_toml,
        },
        "resend": {
            "connected": not env_missing(*resend_required) and bool(first_env(*resend_recipients)),
            "present_names": env_present(*resend_required, *resend_recipients),
            "missing_names": env_missing(*resend_required),
            "recipient_missing_names": list(resend_recipients) if not first_env(*resend_recipients) else [],
            "ray_email_configured": bool(first_env(*resend_recipients)),
        },
        "meta": {
            "connected": bool(env_present("META_PAGE_ACCESS_TOKEN", "FACEBOOK_PAGE_ACCESS_TOKEN")),
            "present_names": env_present(*meta_names),
            "missing_names": env_missing(*meta_names),
        },
        "tiktok": {
            "connected": bool(env_present("TIKTOK_ACCESS_TOKEN")),
            "present_names": env_present(*tiktok_names),
            "missing_names": env_missing(*tiktok_names),
        },
        "oanda": {
            "connected": bool(env_present("OANDA_API_KEY", "OANDA_ACCESS_TOKEN") and env_present("OANDA_ACCOUNT_ID")),
            "present_names": env_present(*oanda_names),
            "missing_names": env_missing(*oanda_names),
            "demo_or_paper": demo,
            "live_signal": live,
        },
        "supabase": {
            "connected": sb.configured(),
            "present_names": env_present("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "VITE_SUPABASE_URL", "VITE_SUPABASE_ANON_KEY"),
        },
        "openrouter_hermes": {
            "connected": bool(env_present("OPENROUTER_API_KEY", "VITE_HERMES_CHAT_ENABLED")),
            "present_names": env_present("OPENROUTER_API_KEY", "HERMES_MODEL", "HERMES_FALLBACK_MODEL", "VITE_HERMES_CHAT_ENABLED", "VITE_HERMES_SEARCH_ENABLED"),
            "missing_names": env_missing("OPENROUTER_API_KEY", "HERMES_MODEL", "HERMES_FALLBACK_MODEL"),
        },
        "oracle": {
            "connected": bool(env_present("ORACLE_HOST", "ORACLE_VM_IP")) or (Path.home() / ".ssh" / "oracle_vm").exists(),
            "present_names": env_present("ORACLE_HOST", "ORACLE_USER", "ORACLE_SSH_KEY", "ORACLE_VM_IP", "OCI_CLI_PROFILE", "OCI_CONFIG_FILE", "OCI_COMPARTMENT_ID"),
            "missing_names": env_missing("ORACLE_HOST", "ORACLE_USER", "ORACLE_SSH_KEY", "ORACLE_VM_IP"),
        },
    }


def first_env(*names: str) -> str:
    for name in names:
        if sb.ENV.get(name):
            return sb.ENV[name]
    return ""


def score_text(text: str, platform: str) -> dict:
    low = text.lower()
    banned_patterns = [
        r"(?<!no )guaranteed funding",
        r"(?<!no )guaranteed approval",
        r"\b100% approval\b",
        r"\bdelete all\b",
        r"\berase your debt\b",
        r"\bwe guarantee\b",
        r"\bwill get approved\b",
    ]
    risk = [pattern for pattern in banned_patterns if re.search(pattern, low)]
    has_disclaimer = bool(re.search(r"no guarantee|education|readiness", low))
    has_cta = bool(re.search(r"\b(dm|request|book|reply|comment|tap|email|start|review)\b", low))
    specifics = sum(1 for word in ["readiness", "credit", "funding", "business", "lender", "entity", "profile", "checklist"] if word in low)
    hook_strength = min(95, 66 + specifics * 4 + (8 if len(text) < 900 else 0))
    clarity = 92 if 40 <= len(text.split()) <= 180 else 82
    compliance_safety = 25 if risk else (96 if has_disclaimer else 82)
    money_alignment = min(96, 68 + specifics * 4)
    goclear_fit = min(95, 70 + specifics * 3)
    cta_strength = 90 if has_cta else 58
    uniqueness = min(90, 66 + specifics * 3)
    platform_fit = 90 if platform in {"facebook", "instagram", "tiktok", "email", "landing_page"} else 82
    overall = round((hook_strength + clarity + compliance_safety + money_alignment + goclear_fit + cta_strength + uniqueness + platform_fit) / 8)
    return {
        "hook_strength": hook_strength,
        "clarity": clarity,
        "compliance_safety": compliance_safety,
        "money_alignment": money_alignment,
        "goclear_apex_fit": goclear_fit,
        "cta_strength": cta_strength,
        "uniqueness": uniqueness,
        "lead_generation_potential": min(96, round((cta_strength + money_alignment + clarity) / 3)),
        "platform_fit": platform_fit,
        "overall_score": overall,
        "risk_flags": risk,
    }


def creative_drafts() -> list[dict]:
    drafts = [
        {
            "type": "facebook_post",
            "platform": "facebook",
            "title": "Apply-ready before applying",
            "copy": (
                "Small business owners: before you apply for funding, make sure your credit and "
                "business profile are actually ready.\n\n"
                "GoClear/Apex now has a $97 Credit & Funding Readiness Review to help identify gaps "
                "before you waste time applying.\n\n"
                "Start here:\n"
                "https://nexusv20.netlify.app/goclear-apex-readiness.html\n\n"
                "No funding guarantees. This is a readiness review to help you understand what needs "
                "to be fixed or prepared first.\n\n"
                f"{DISCLAIMER}"
            ),
        },
        {
            "type": "instagram_caption",
            "platform": "instagram",
            "title": "Funding prep caption",
            "copy": (
                "Before you apply, check readiness.\n\n"
                "A funding conversation can get messy when the business profile, credit picture, entity details, and documents do not tell the same story. "
                "The $97 GoClear/Apex Readiness Review gives you a plain-language snapshot and next-step checklist.\n\n"
                "DM \"READY\" to ask about the review.\n\n"
                f"{DISCLAIMER}"
            ),
        },
        {
            "type": "tiktok_script",
            "platform": "tiktok",
            "title": "Three checks before applying",
            "copy": (
                "Hook: Stop applying for funding before you check these three things.\n"
                "Scene 1: Show a checklist: credit picture, business profile, documents.\n"
                "Scene 2: Explain that lenders may look for consistency before they care about the story.\n"
                "Scene 3: Offer the $97 GoClear/Apex Readiness Review for a simple prep snapshot.\n"
                "CTA: Comment READY or message Ray for the review.\n"
                f"{DISCLAIMER}"
            ),
        },
        {
            "type": "landing_page_variants",
            "platform": "landing_page",
            "title": "Hero/headline variants",
            "copy": (
                "1. Get your credit and funding profile application-ready before you apply.\n"
                "2. The $97 readiness review for business owners who want fewer surprises.\n"
                "3. Know the gaps in your funding story before a lender sees them.\n"
                f"{DISCLAIMER}"
            ),
        },
        {
            "type": "lead_magnet",
            "platform": "lead_magnet",
            "title": "Readiness checklist",
            "copy": (
                "Lead magnet idea: Business Funding Readiness Checklist. Sections: entity consistency, business address and phone, website and email, bank relationship, credit profile, basic documents, and application timing notes. "
                "CTA: Use the checklist, then request the $97 review for a personalized readiness snapshot. "
                f"{DISCLAIMER}"
            ),
        },
        {
            "type": "dm_script",
            "platform": "direct_message",
            "title": "Warm DM response",
            "copy": (
                "Thanks for reaching out. The $97 GoClear/Apex Readiness Review is an education-first snapshot of your credit/funding preparation: what looks ready, what may need cleanup, and what to organize before you apply. "
                "It does not guarantee funding or approvals. If that works, send your best email and Ray can share the next step."
            ),
        },
        {
            "type": "newsletter_email",
            "platform": "email",
            "title": "Test newsletter draft",
            "copy": (
                "Subject: TEST - GoClear/Apex $97 readiness review\n\n"
                "Ray,\n\n"
                "This is a test email for the GoClear/Apex activation loop.\n\n"
                "The offer: a $97 Credit & Funding Readiness Review for business owners who want to understand application readiness before they apply. The review focuses on business profile consistency, credit/funding preparation, documentation basics, and a short next-action checklist.\n\n"
                f"{DISCLAIMER}\n\n"
                "CTA: Reply to request the review path."
            ),
        },
        {
            "type": "carousel_outline",
            "platform": "instagram",
            "title": "Readiness carousel",
            "copy": (
                "Slide 1: Before you apply, check readiness.\n"
                "Slide 2: Is your business profile consistent?\n"
                "Slide 3: Does your credit picture match your funding goal?\n"
                "Slide 4: Are your documents organized?\n"
                "Slide 5: Do you know what to fix first?\n"
                "Slide 6: $97 GoClear/Apex Readiness Review.\n"
                f"{DISCLAIMER}"
            ),
        },
    ]
    for draft in drafts:
        draft["score"] = score_text(draft["copy"], draft["platform"])
    return drafts


def write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def write_manual_packages(drafts: list[dict], integrations: dict) -> dict:
    hashtags = ["#BusinessCredit", "#FundingReadiness", "#SmallBusiness", "#GoClear", "#ApexReadiness"]
    cta = "Request the $97 GoClear/Apex Readiness Review."
    compliance = DISCLAIMER
    packages = {
        "status": "manual_publish_required",
        "reason": "Social publishing tokens/config are not connected locally, or no approved adapter exists.",
        "cta": cta,
        "hashtags": hashtags,
        "compliance_disclaimer": compliance,
        "facebook": {
            "copy": next(d for d in drafts if d["type"] == "facebook_post")["copy"],
            "hashtags": hashtags[:4],
            "asset_prompt": "A clean desk with a small business funding readiness checklist, laptop, and organized documents. Professional, trustworthy, no cash piles, no approval guarantee text.",
            "posting_checklist": [
                "Paste the copy exactly.",
                "Attach one readiness/checklist image.",
                "Confirm the disclaimer is present.",
                "Do not boost or run ads.",
                "After posting, save the URL as a manual publish receipt.",
            ],
        },
        "instagram": {
            "caption": next(d for d in drafts if d["type"] == "instagram_caption")["copy"],
            "hashtags": hashtags,
            "asset_prompt": "4:5 carousel cover reading 'Before you apply, check readiness' with three checklist items: profile, credit picture, documents. Modern business style.",
            "posting_checklist": [
                "Use a 4:5 checklist graphic or carousel.",
                "Paste the caption and hashtags.",
                "Keep the disclaimer in the caption.",
                "Do not imply approval, score change, or deletion results.",
                "Save the live URL or screenshot after posting.",
            ],
        },
        "tiktok": {
            "script": next(d for d in drafts if d["type"] == "tiktok_script")["copy"],
            "caption": f"Before you apply, check readiness. {cta} {compliance}",
            "hashtags": ["#BusinessFunding", "#CreditReadiness", "#SmallBusinessTips", "#GoClear"],
            "asset_prompt": "Talking-head video with a checklist overlay: credit picture, business profile, documents. Calm advisory tone.",
            "posting_checklist": [
                "Record the script as a short talking-head or screen checklist.",
                "Paste the caption with disclaimer.",
                "Do not mention guaranteed approvals or funding.",
                "Do not promote paid ads.",
                "Save the post URL or screenshot after publishing.",
            ],
        },
        "asset_instructions": {
            "facebook": "Use a clean founder-readiness image or short checklist graphic. Do not include income, approval, deletion, or score-change claims.",
            "instagram": "Use a 4:5 checklist graphic with three checks: profile, credit picture, documents.",
            "tiktok": "Record a simple talking-head or checklist screen recording. Keep the disclaimer in caption or spoken close.",
        },
        "integration_status": {
            "meta_connected": integrations["meta"]["connected"],
            "tiktok_connected": integrations["tiktok"]["connected"],
        },
    }
    write_json(MANUAL_DIR / "goclear_apex_social_manual_publish_package.json", packages)
    return packages


def write_netlify_deploy_package(integrations: dict) -> dict:
    net = integrations["netlify"]
    public_url = net.get("public_url")
    if public_url:
        status = "github_connected_public_url_configured"
    elif net.get("deploy_mode") == "github_connected_assumed":
        status = "github_connected_assumed_provide_public_url"
    else:
        status = "deploy_ready_manual_netlify_required"
    public_page_url = f"{public_url.rstrip('/')}/goclear-apex-readiness.html" if public_url else None
    package = {
        "status": status,
        "deploy_mode": net.get("deploy_mode"),
        "public_url": public_url,
        "public_page_url": public_page_url,
        "landing_page_source": "public/goclear-apex-readiness.html",
        "built_file": "dist/goclear-apex-readiness.html",
        "public_path": "/goclear-apex-readiness.html",
        "missing_env_names": net.get("missing_names", []),
        "netlify_toml": net.get("netlify_toml", False),
        "auto_deploy_assumption": (
            "GitHub-connected deploy: pushing main builds on Netlify using netlify.toml "
            "(command npm run build, publish dir dist). Local NETLIFY_AUTH_TOKEN / NETLIFY_SITE_ID "
            "are NOT required for this path — they are only for CLI/API verification."
        ),
        "next_value_needed": None if public_url else "public Netlify domain/URL (set NEXUS_NETLIFY_PUBLIC_URL or VITE_GOCLEAR_PUBLIC_URL)",
        "manual_steps": [
            "Preferred: push main to GitHub; Netlify builds and deploys automatically (netlify.toml present).",
            "Provide the public URL to Nexus by setting NEXUS_NETLIFY_PUBLIC_URL (or VITE_GOCLEAR_PUBLIC_URL).",
            "CLI/API verification (optional): set NETLIFY_AUTH_TOKEN and NETLIFY_SITE_ID locally.",
            "Manual deploy is only needed if the GitHub-connected deploy fails: netlify deploy --prod --dir=dist.",
        ],
    }
    md = [
        "# GoClear/Apex Landing Page Deploy Package",
        "",
        f"- Status: {package['status']}",
        f"- Deploy mode: {package['deploy_mode']}",
        f"- Public URL: {public_url or 'not provided yet (set NEXUS_NETLIFY_PUBLIC_URL or VITE_GOCLEAR_PUBLIC_URL)'}",
        f"- Public landing page: {public_page_url or 'pending public URL'}",
        f"- Source: `{package['landing_page_source']}`",
        f"- Built file: `{package['built_file']}`",
        f"- Public path after deploy: `{package['public_path']}`",
        f"- netlify.toml present: {package['netlify_toml']}",
        "",
        "## Netlify Settings (self-documented in netlify.toml)",
        "- Build command: `npm run build`",
        "- Publish directory: `dist`",
        "- Landing page path: `/goclear-apex-readiness.html`",
        "- GitHub-connected deploy does NOT need NETLIFY_AUTH_TOKEN / NETLIFY_SITE_ID.",
        "",
        "## Steps",
        *[f"{idx}. {step}" for idx, step in enumerate(package["manual_steps"], start=1)],
        "",
        "No public URL is claimed live until the URL is configured (and verified).",
    ]
    (MANUAL_DIR / "goclear_apex_netlify_deploy_package.md").write_text("\n".join(md) + "\n")
    write_json(MANUAL_DIR / "goclear_apex_netlify_deploy_package.json", package)
    return package


def insert_creative_assets(drafts: list[dict]) -> dict:
    if not sb.configured():
        return {"written": False, "reason": "supabase_not_configured"}
    written = 0
    for draft in drafts:
        payload = {
            "campaign_key": CAMPAIGN_KEY,
            "activation_run": True,
            "score": draft["score"],
            "compliance_footer": DISCLAIMER,
        }
        st, existing = sb.get("creative_assets", f"payload->>campaign_key=eq.{sb.q(CAMPAIGN_KEY)}&asset_type=eq.{sb.q(draft['type'])}&select=id&limit=1")
        if isinstance(existing, list) and existing:
            sb.update("creative_assets", f"id=eq.{sb.q(existing[0]['id'])}", {
                "score": draft["score"]["overall_score"],
                "status": "scored" if not draft["score"]["risk_flags"] else "blocked_compliance",
                "payload": payload,
            })
            continue
        st, row = sb.insert("creative_assets", {
            "asset_type": draft["type"],
            "title": draft["title"],
            "content": draft["copy"],
            "platform": draft["platform"],
            "offer": "GoClear/Apex $97 Credit/Funding Readiness Review",
            "score": draft["score"]["overall_score"],
            "status": "scored" if not draft["score"]["risk_flags"] else "blocked_compliance",
            "payload": payload,
        })
        if 200 <= st < 300:
            written += 1
    sb.event("monetization", "activation_creative_drafts_generated", "success", "GoClear/Apex creative drafts generated", f"{len(drafts)} drafts, {written} new DB rows", payload={"campaign_key": CAMPAIGN_KEY})
    return {"written": True, "new_rows": written}


def social_publish_test(drafts: list[dict], integrations: dict) -> dict:
    result = {"published": [], "manual_publish_required": [], "blocked": []}
    if not integrations["tiktok"]["connected"]:
        result["manual_publish_required"].append("tiktok")
    # The current repo has a gated Facebook adapter only. Instagram stays manual until a
    # dedicated safe adapter exists, even when Meta credentials are present.
    result["manual_publish_required"].append("instagram")
    fb_token = first_env("META_PAGE_ACCESS_TOKEN", "FACEBOOK_PAGE_ACCESS_TOKEN")
    if not (integrations["meta"]["connected"] and fb_token and sb.configured()):
        result["manual_publish_required"] += ["facebook", "instagram"]
        result["manual_publish_required"] = sorted(set(result["manual_publish_required"]))
        return result

    st, accounts = sb.get("social_accounts", "platform=eq.facebook&select=id,account_name,account_id,publish_enabled,token_env_key&limit=5")
    if not isinstance(accounts, list) or not accounts:
        result["manual_publish_required"].append("facebook")
        result["blocked"].append("facebook_account_not_registered")
        result["manual_publish_required"] = sorted(set(result["manual_publish_required"]))
        return result
    account = accounts[0]
    if not account.get("publish_enabled"):
        result["manual_publish_required"].append("facebook")
        result["blocked"].append("facebook_publish_enabled_false")
        st, approvals = sb.get("approvals", "item_type=eq.facebook_publish_enablement&status=eq.pending&select=id,title&order=created_at.desc&limit=1")
        if isinstance(approvals, list) and approvals:
            result["approval_required"] = {
                "status": "pending",
                "approval_id": approvals[0]["id"],
                "title": approvals[0].get("title"),
                "next_step": "Approve this request, then set social_accounts.publish_enabled=true for the Clear Credentials Facebook row before running one real publish.",
            }
        else:
            result["approval_required"] = {
                "status": "missing",
                "next_step": "Create an approval for facebook_publish_enablement before setting social_accounts.publish_enabled=true.",
            }
        result["manual_publish_required"] = sorted(set(result["manual_publish_required"]))
        return result

    copy = next(d for d in drafts if d["type"] == "facebook_post")["copy"]
    st, approval = sb.insert("approvals", {
        "lane": "social",
        "item_type": "social_post",
        "status": "approved",
        "title": "Approved activation test post",
        "summary": "Ray-approved activation packet: one compliant GoClear/Apex test post.",
        "payload": {"campaign_key": CAMPAIGN_KEY, "no_paid_boost": True},
        "approved_by": "activation_packet",
        "decided_at": now(),
    })
    approval_id = approval[0]["id"] if isinstance(approval, list) and approval else None
    st, post = sb.insert("social_posts", {
        "platform": "facebook",
        "account_id": account["id"],
        "content": copy,
        "status": "approved",
        "approval_id": approval_id,
        "payload": {"campaign_key": CAMPAIGN_KEY, "activation_test": True},
    })
    post_id = post[0]["id"] if isinstance(post, list) and post else None
    if not post_id:
        result["blocked"].append("facebook_post_insert_failed")
        result["manual_publish_required"] = sorted(set(result["manual_publish_required"]))
        return result
    from facebook_publisher import publish  # noqa: PLC0415
    published = publish(post_id, real_publish=True)
    if published.get("ok") and published.get("published"):
        result["published"].append({"platform": "facebook", "status": "published", "url": published.get("permalink"), "receipt": published.get("post_id")})
    else:
        result["blocked"].append({"platform": "facebook", "reason": published.get("blocker") or published.get("error") or "publish_failed"})
    result["manual_publish_required"] = sorted(set(result["manual_publish_required"]))
    return result


def newsletter_test(drafts: list[dict], integrations: dict) -> dict:
    email = first_env("RESEND_TO_EMAIL", "RAY_EMAIL", "RESEND_TEST_TO", "TO_EMAIL", "TEST_EMAIL")
    draft = next(d for d in drafts if d["type"] == "newsletter_email")["copy"]
    (MANUAL_DIR / "goclear_apex_test_newsletter.txt").write_text(draft + "\n")
    if sb.configured():
        st, sent = sb.get("nexus_events", "action=eq.resend_test_email&status=eq.success&select=payload,summary,created_at&order=created_at.desc&limit=1")
        if isinstance(sent, list) and sent:
            payload = sent[0].get("payload") or {}
            return {
                "created": True,
                "sent": True,
                "status": "already_sent",
                "message_id": payload.get("message_id"),
                "recipient_configured": True,
                "path": "reports/manual_publish/goclear_apex_test_newsletter.txt",
            }
    if not integrations["resend"]["connected"]:
        missing = [*integrations["resend"].get("missing_names", []), *integrations["resend"].get("recipient_missing_names", [])]
        result = {"created": True, "sent": False, "status": "email_send_blocked_missing_resend", "missing_env_names": missing, "path": "reports/manual_publish/goclear_apex_test_newsletter.txt"}
        if sb.configured():
            sb.event("communication", "resend_test_email_blocked", "pending", "Resend test email blocked", f"missing env names: {', '.join(missing)}", payload={"missing_env_names": missing})
        return result
    if not email:
        missing = ["RESEND_TO_EMAIL", "RAY_EMAIL", "RESEND_TEST_TO", "TO_EMAIL", "TEST_EMAIL"]
        return {"created": True, "sent": False, "status": "email_send_blocked_missing_ray_email", "missing_env_names": missing, "path": "reports/manual_publish/goclear_apex_test_newsletter.txt"}

    api_key = sb.ENV["RESEND_API_KEY"]
    from_email = sb.ENV["RESEND_FROM_EMAIL"]
    ok, resp = secret_post("https://api.resend.com/emails", {
        "from": from_email,
        "to": [email],
        "subject": "TEST - GoClear/Apex $97 readiness review",
        "text": draft,
    }, {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    result = {"created": True, "sent": ok, "recipient_configured": True, "status": "sent" if ok else "failed", "message_id": resp.get("id") if ok else None, "error": None if ok else resp.get("error")}
    if sb.configured():
        sb.event("communication", "resend_test_email", "success" if ok else "failed", "Resend test email", result["status"], payload={"sent": ok, "message_id": result["message_id"]})
    return result


def trading_test(integrations: dict) -> dict:
    oanda = integrations["oanda"]
    if not oanda["connected"]:
        return {"connection_tested": False, "trade_placed": False, "status": "blocked_missing_oanda_config", "missing_env_names": oanda.get("missing_names", [])}
    if oanda["live_signal"] or not oanda["demo_or_paper"]:
        return {"connection_tested": False, "trade_placed": False, "status": "blocked_live_trade_requires_explicit_approval", "missing_env_names": oanda.get("missing_names", [])}
    token = first_env("OANDA_API_KEY", "OANDA_ACCESS_TOKEN")
    account_id = first_env("OANDA_ACCOUNT_ID")
    ok, resp = secret_get(f"https://api-fxpractice.oanda.com/v3/accounts/{urllib.parse.quote(account_id)}/summary", {"Authorization": f"Bearer {token}"})
    status = "demo_connection_ok" if ok else "demo_connection_failed"
    if sb.configured():
        sb.event("trading", "oanda_demo_connection_test", "success" if ok else "failed", "Oanda demo connection test", status, payload={"environment": "demo/paper", "trade_placed": False})
    return {"connection_tested": True, "trade_placed": False, "status": status, "demo_paper_only": True, "account_summary_seen": bool(ok and resp), "missing_env_names": []}


def oracle_status() -> dict:
    user = first_env("ORACLE_USER") or "opc"
    host = first_env("ORACLE_HOST", "ORACLE_VM_IP") or "161.153.40.41"
    key_name = first_env("ORACLE_SSH_KEY")
    key_candidates = [Path(key_name).expanduser()] if key_name else []
    key_candidates.append(Path.home() / ".ssh" / "oracle_vm")
    key = next((path for path in key_candidates if path.exists()), None)
    result = {
        "reachable": False,
        "status": "missing_key_or_host",
        "host_known": bool(host),
        "key_present": bool(key),
        "user": user if user in {"opc", "ubuntu", "ec2-user"} else "configured",
        "host_label": "documented_default_or_env",
        "summary": [],
    }
    if not key or not host:
        result["missing_config_names"] = [name for name in ("ORACLE_HOST", "ORACLE_VM_IP", "ORACLE_SSH_KEY") if not sb.ENV.get(name)]
        return result
    cmd = [
        "ssh", "-i", str(key), "-o", "BatchMode=yes", "-o", "ConnectTimeout=6",
        "-o", "StrictHostKeyChecking=accept-new", f"{user}@{host}",
        "hostname; uptime; df -h / | tail -n 1; free -m | head -n 2; pgrep -af 'nexus|ollama|python|node' | head -n 20",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
    except subprocess.TimeoutExpired:
        result["status"] = "ssh_timeout"
        return result
    result["reachable"] = proc.returncode == 0
    result["status"] = "reachable" if proc.returncode == 0 else "ssh_failed"
    if proc.stdout:
        lines = proc.stdout.splitlines()
        result["summary"] = lines[:30]
        result["hostname"] = lines[0] if lines else ""
        result["ollama_seen"] = any("ollama" in line for line in lines)
        result["nexus_process_seen"] = any("nexus" in line.lower() for line in lines)
    if proc.stderr and proc.returncode != 0:
        result["error_summary"] = proc.stderr.splitlines()[-3:]
    if sb.configured():
        sb.event("automation", "oracle_worker_status", "success" if result["reachable"] else "pending",
                 "Oracle worker status checked", result["status"],
                 payload={"reachable": result["reachable"], "status": result["status"], "hostname": result.get("hostname"), "ollama_seen": result.get("ollama_seen")})
    return result


def landing_status(integrations: dict) -> dict:
    net = integrations["netlify"]
    public_url = net.get("public_url")
    if public_url:
        status = "github_connected_public_url_configured_needs_live_verification"
    elif net.get("deploy_mode") == "github_connected_assumed":
        status = "github_connected_assumed_provide_public_url"
    elif net.get("cli_capable") and net.get("netlify_toml"):
        status = "netlify_cli_token_present_config_push_should_deploy"
    else:
        status = "deploy_ready_manual_netlify_required"
    public_page_url = f"{public_url.rstrip('/')}/goclear-apex-readiness.html" if public_url else None
    return {
        "created": LANDING_PAGE.exists(),
        "path": "public/goclear-apex-readiness.html",
        "local_url_path": "/goclear-apex-readiness.html",
        "netlify_connected": net.get("connected"),
        "deploy_mode": net.get("deploy_mode"),
        "public_url": public_url,
        "public_page_url": public_page_url,
        "missing_env_names": net.get("missing_names", []),
        "status": status,
        "form_backend": "missing_public_form_backend_manual_email_cta_used",
        "deploy_package": "reports/manual_publish/goclear_apex_netlify_deploy_package.md",
    }


def scheduler_status() -> dict:
    return {
        "installed": False,
        "started": False,
        "manual_command": "npm run nexus:watch",
        "recommended_schedule": "Every business morning and once mid-afternoon while offers are being tested; do not run more frequently than hourly without adding stronger deduplication.",
        "lock_overlap_protection": "file lock at reports/runtime/nexus_watch.lock; overlapping runs exit without starting a second pass",
        "logs_reports": "reports/runtime/nexus_watch_report_latest.md and reports/runtime/nexus_watch_report_latest.json",
        "hermes_report_access": "Hermes report-reader receives the safe report summary from the watch loop and can also summarize recent nexus_events/system_health.",
        "disabled_config_path": "docs/operations/NEXUS_WATCH_LOOP.md",
    }


def hermes_explanation(report_summary: str) -> dict:
    if not sb.configured():
        return {"ok": False, "status": "blocked_missing_supabase", "text": fallback_explanation()}
    url = (sb.URL or "").rstrip("/") + "/functions/v1/hermes-chat"
    key = sb.KEY
    if not url or not key:
        return {"ok": False, "status": "blocked_missing_hermes_endpoint", "text": fallback_explanation()}
    ok, resp = secret_post(url, {
        "message": "Read the latest Nexus Watch Report and explain what happened, what worked, what failed, and what Ray should do next.",
        "mode": "report_reader",
        "context": {"report": report_summary[:2400]},
    }, {"Authorization": f"Bearer {key}", "apikey": key, "Content-Type": "application/json"})
    text = str(resp.get("reply") or resp.get("text") or "").strip() if isinstance(resp, dict) else ""
    if ok and text:
        return {"ok": True, "status": "hermes_explained_report", "text": text[:1800]}
    return {"ok": False, "status": "hermes_unavailable_fallback_used", "text": fallback_explanation()}


def fallback_explanation() -> str:
    return (
        "Hermes fallback summary: the activation loop created the GoClear/Apex offer page, "
        "generated and scored compliant creative drafts, prepared manual publish and email packages, "
        "checked integrations, avoided live trading and mass actions, and wrote a watch report. "
        "Ray should connect Netlify/form intake, Resend, social tokens, and demo trading credentials before the next field test."
    )


def markdown_report(data: dict) -> str:
    top = data["top_draft"]
    lines = [
        "# Nexus Watch Report",
        "",
        f"- generated_at: {data['generated_at']}",
        "- mode: manual activation run",
        "- safety: no secrets printed, no paid ads, no mass email, no funded/live trades, no private customer data used",
        "",
        "## What Ran",
        "- Integration discovery without secret values",
        "- GoClear/Apex landing page readiness check",
        "- Creative draft generation and scoring",
        "- Manual publish package creation",
        "- Newsletter draft/send gate",
        "- Trading demo/paper gate",
        "- Supabase event proof write when configured",
        "- Hermes report explanation attempt",
        "",
        "## Landing Page",
        f"- created: {data['landing']['created']}",
        f"- path: {data['landing']['path']}",
        f"- url_path: {data['landing']['local_url_path']}",
        f"- status: {data['landing']['status']}",
        f"- missing_netlify_env_names: {', '.join(data['landing'].get('missing_env_names', [])) or 'none'}",
        f"- deploy_package: {data['landing']['deploy_package']}",
        f"- form_backend: {data['landing']['form_backend']}",
        "",
        "## Integrations",
    ]
    for name, info in data["integrations"].items():
        extra = ""
        if name == "oanda":
            extra = f" demo_or_paper={info['demo_or_paper']} live_signal={info['live_signal']}"
        if name == "netlify":
            extra = f" deploy_mode={info.get('deploy_mode')} public_url={info.get('public_url') or 'none'} cli_capable={info.get('cli_capable')} netlify_toml={info.get('netlify_toml')}"
        lines.append(f"- {name}: connected={info['connected']} present_names={','.join(info.get('present_names', [])) or 'none'} missing_names={','.join(info.get('missing_names', [])) or 'none'}{extra}")
    lines += [
        "",
        "## Creative Scores",
    ]
    for draft in data["drafts"]:
        s = draft["score"]
        lines.append(f"- {draft['type']} ({draft['platform']}): overall={s['overall_score']} hook={s['hook_strength']} clarity={s['clarity']} compliance={s['compliance_safety']} money={s['money_alignment']} cta={s['cta_strength']} platform={s['platform_fit']}")
    lines += [
        "",
        "## Top Draft",
        f"- type: {top['type']}",
        f"- score: {top['score']['overall_score']}",
        f"- why: strongest blend of readiness positioning, compliant CTA, money alignment, and immediate lead-generation fit.",
        "",
        "## Social",
        f"- published: {json.dumps(data['social']['published'])}",
        f"- manual_publish_required: {json.dumps(data['social']['manual_publish_required'])}",
        f"- blocked: {json.dumps(data['social']['blocked'])}",
        f"- approval_required: {json.dumps(data['social'].get('approval_required', {}))}",
        f"- manual_package: reports/manual_publish/goclear_apex_social_manual_publish_package.json",
        "",
        "## Newsletter",
        f"- created: {data['newsletter']['created']}",
        f"- sent: {data['newsletter']['sent']}",
        f"- status: {data['newsletter']['status']}",
        f"- missing_env_names: {', '.join(data['newsletter'].get('missing_env_names', [])) or 'none'}",
        f"- message_id: {data['newsletter'].get('message_id') or 'none'}",
        "",
        "## Trading",
        f"- connection_tested: {data['trading']['connection_tested']}",
        f"- demo_paper_trade_placed: {data['trading']['trade_placed']}",
        f"- status: {data['trading']['status']}",
        f"- missing_env_names: {', '.join(data['trading'].get('missing_env_names', [])) or 'none'}",
        "- funded_live_trade: false",
        "",
        "## Oracle Worker",
        f"- reachable: {data['oracle']['reachable']}",
        f"- status: {data['oracle']['status']}",
        f"- hostname: {data['oracle'].get('hostname') or 'unknown'}",
        f"- key_present: {data['oracle']['key_present']}",
        f"- ollama_seen: {data['oracle'].get('ollama_seen', False)}",
        f"- nexus_process_seen: {data['oracle'].get('nexus_process_seen', False)}",
        "- action_taken: read_only_status_check",
        "- summary:",
        *[f"  - {line}" for line in data["oracle"].get("summary", [])[:8]],
        "",
        "## Scheduler Ready",
        f"- installed: {data['scheduler']['installed']}",
        f"- started: {data['scheduler']['started']}",
        f"- manual_command: {data['scheduler']['manual_command']}",
        f"- recommended_schedule: {data['scheduler']['recommended_schedule']}",
        f"- lock_overlap_protection: {data['scheduler']['lock_overlap_protection']}",
        f"- logs_reports: {data['scheduler']['logs_reports']}",
        f"- hermes_report_access: {data['scheduler']['hermes_report_access']}",
        "",
        "## Proofs",
        f"- nexus_events_written: {data['proofs']['nexus_events_written']}",
        f"- creative_assets_db: {json.dumps(data['proofs']['creative_assets_db'])}",
        "",
        "## Hermes Explanation",
        f"- status: {data['hermes']['status']}",
        "",
        data["hermes"]["text"],
        "",
        "## Recommended Next Actions",
        "1. Connect Netlify or confirm the existing site so `/goclear-apex-readiness.html` can go live.",
        "2. Add a real intake/checkout path for the $97 review before public traffic.",
        "3. Connect one social platform token and keep the one-post gate for the next field test.",
        "4. Configure Resend with Ray's test recipient before sending any campaign email.",
        "5. Add Oanda demo credentials only if demo/paper testing is still desired.",
    ]
    return "\n".join(lines) + "\n"


@contextlib.contextmanager
def watch_lock():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    handle = LOCK_FILE.open("w")
    try:
        import fcntl  # type: ignore
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("nexus_watch_already_running")
        handle.write(now())
        handle.flush()
        yield
    finally:
        with contextlib.suppress(Exception):
            import fcntl  # type: ignore
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def run(mode: str) -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    MANUAL_DIR.mkdir(parents=True, exist_ok=True)
    integrations = integration_summary()
    deploy_package = write_netlify_deploy_package(integrations)
    drafts = creative_drafts()
    write_json(REPORT_DIR / "goclear_apex_creative_scores.json", drafts)
    manual_package = write_manual_packages(drafts, integrations)
    creative_db = insert_creative_assets(drafts)
    landing = landing_status(integrations)
    social = social_publish_test(drafts, integrations)
    newsletter = newsletter_test(drafts, integrations)
    trading = trading_test(integrations)
    oracle = oracle_status()
    if sb.configured():
        sb.event("automation", "nexus_watch_activation_run", "success", "Nexus Watch activation run completed", "GoClear/Apex activation report generated", payload={"campaign_key": CAMPAIGN_KEY, "mode": mode})
        sb.health("nexus_watch", "ok", "Manual activation loop completed; report generated.")
    top = sorted(drafts, key=lambda d: d["score"]["overall_score"], reverse=True)[0]
    scheduler = scheduler_status()
    report_probe = f"Landing {landing['status']}; top draft {top['type']} score {top['score']['overall_score']}; social {social}; newsletter {newsletter['status']}; trading {trading['status']}; oracle {oracle['status']}."
    hermes = hermes_explanation(report_probe)
    data = {
        "generated_at": now(),
        "mode": mode,
        "integrations": integrations,
        "landing": landing,
        "deploy_package": deploy_package,
        "drafts": drafts,
        "top_draft": top,
        "manual_package": manual_package,
        "social": social,
        "newsletter": newsletter,
        "trading": trading,
        "oracle": oracle,
        "scheduler": scheduler,
        "hermes": hermes,
        "proofs": {
            "nexus_events_written": sb.configured(),
            "creative_assets_db": creative_db,
        },
    }
    report_path = REPORT_DIR / f"nexus_watch_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
    report_path.write_text(markdown_report(data))
    latest = REPORT_DIR / "nexus_watch_report_latest.md"
    latest.write_text(report_path.read_text())
    data["report_path"] = str(report_path.relative_to(ROOT))
    data["latest_report_path"] = str(latest.relative_to(ROOT))
    write_json(REPORT_DIR / "nexus_watch_report_latest.json", data)
    if sb.configured():
        sb.event("communication", "nexus_watch_report_generated", "success", "Nexus Watch Report generated", data["latest_report_path"], payload={"report_path": data["latest_report_path"], "safe_report": True})
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the manual Nexus activation loop.")
    parser.add_argument("--mode", default="manual", choices=["manual"])
    args = parser.parse_args()
    try:
        with watch_lock():
            data = run(args.mode)
    except RuntimeError as exc:
        if str(exc) == "nexus_watch_already_running":
            print(json.dumps({"ok": False, "status": "blocked_overlap", "reason": "nexus_watch_already_running"}, indent=2))
            return 2
        raise
    print(json.dumps({
        "ok": True,
        "report_path": data["latest_report_path"],
        "landing_page": data["landing"],
        "deploy_package": data["deploy_package"],
        "social": data["social"],
        "newsletter": {k: v for k, v in data["newsletter"].items() if k != "error"},
        "trading": data["trading"],
        "oracle": {"reachable": data["oracle"]["reachable"], "status": data["oracle"]["status"], "hostname": data["oracle"].get("hostname"), "ollama_seen": data["oracle"].get("ollama_seen")},
        "scheduler": data["scheduler"],
        "hermes": {"status": data["hermes"]["status"], "ok": data["hermes"]["ok"]},
        "nexus_events_written": data["proofs"]["nexus_events_written"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
