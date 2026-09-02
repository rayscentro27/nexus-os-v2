#!/usr/bin/env python3
"""Build one evidence-backed, zero-spend commercial mission package."""
from __future__ import annotations
import hashlib, json, subprocess
from datetime import datetime, timezone
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts"))
from nexus_agent_platform.governed.persistence import append_record, read_records  # noqa: E402

OUT = ROOT / "reports" / "runtime" / "commercial"
PREVIEW = ROOT / "public" / "marketing-previews" / "wp93-commercial-readiness.html"
AFFILIATE_SOURCES = {
    "Mercury": "https://mercury.com/for/accountants",
    "Relay": "https://relayfi.com/hc/en-us/articles/23382126147988-Onboarding-your-clients-to-Relay/",
    "Bluevine": "https://support.bluevine.com/s/article/How-can-I-earn-rewards-from-the-Accountant-Partner-Program",
}

def now(): return datetime.now(timezone.utc).isoformat()
def fp(value): return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:20]
def write(name, value):
    OUT.mkdir(parents=True, exist_ok=True); (OUT / name).write_text(json.dumps(value, indent=2) + "\n")

def direct_source(url):
    p = subprocess.run(["curl", "-L", "--fail", "--max-time", "20", "-A", "NexusCommercialResearch/1.0", "-sS", url], capture_output=True, timeout=25, check=False)
    text = p.stdout.decode("utf-8", "replace") if p.returncode == 0 else ""
    return {"url": url, "retrieved_at": now(), "status": "RETRIEVED" if text else "UNAVAILABLE", "content_hash": fp(text[:30000]), "excerpt": " ".join(text.split())[:1200] if text else None}

def main():
    alpha = [r for r in read_records("alpha_claims") if r.get("source_id")]
    evidence = alpha[0] if alpha else {"claim_id": "UNKNOWN", "claim": "No Alpha claim available"}
    campaign_id = "commercial_" + fp(evidence.get("claim_id"))
    brief = {"campaign_id": campaign_id, "source_claim_id": evidence.get("claim_id"), "source_claim": evidence.get("claim"), "audience": "JavaScript small-business operators who need a clearer technical SEO baseline", "pain": "Uncertainty about discoverability and technical readiness", "offer": "Evidence-led technical SEO readiness review", "desired_action": "Request an internal review / validation interest", "economics": {"cash_cost_usd": 0, "revenue": "UNKNOWN", "conversion": "UNKNOWN", "CAC": "UNKNOWN", "max_validation_cost_usd": 0, "state": "VALIDATION_READY"}, "constraints": ["draft-only", "no-publication", "no-ad-spend", "no-claims beyond evidence"], "evidence_refs": [evidence.get("claim_id")], "created_at": now()}
    territories = [
        {"id": "T1", "name": "Clarity", "angle": "Know what is blocking discoverability before investing in more content."},
        {"id": "T2", "name": "Control", "angle": "Turn technical SEO uncertainty into a prioritized owner-ready checklist."},
        {"id": "T3", "name": "Readiness", "angle": "Build a measurable baseline before choosing tools or agencies."},
    ]
    package = {"campaign_id": campaign_id, "brief": brief, "territories": territories, "selected_territory": "T2", "critic": {"genericness": "Avoid generic traffic promises; use evidence and uncertainty labels.", "prohibited": ["guaranteed rankings", "fake testimonials", "fabricated outcomes"]}, "landing_page": {"headline": "Turn Technical SEO Uncertainty Into a Prioritized Plan", "subheadline": "An evidence-led readiness review for operators who want to know what to fix before buying more tools or content.", "sections": ["problem", "evidence-led approach", "what the review covers", "what remains unknown", "FAQ", "disclosure", "request review"], "cta": "Request a readiness review", "status": "DRAFT_ONLY"}, "channel_native": {"facebook": "Before adding another SEO tool, identify the technical unknowns first. Request an evidence-led readiness review.", "instagram": "A clearer SEO baseline starts with fewer guesses. Save the checklist; request a readiness review when ready.", "short_video": "Hook: More content will not fix an unknown technical baseline. Show three checks, explain uncertainty, invite a review.", "youtube_short": "A 30-second educational walkthrough of the three readiness checks; no ranking guarantee."}, "disclosure": "Internal draft. No performance guarantee. No affiliate relationship claimed until a direct program agreement is verified.", "validation_plan": {"mode": "NO_SPEND_ORGANIC_PREPARATION", "primary_metric": "real qualified request", "secondary_metrics": ["real view", "real click", "real reply"], "sample_window": "UNKNOWN_UNTIL_AUTHORIZED", "stopping_rule": "stop after approved zero-spend window or evidence ceiling", "external_exposure": False}}
    affiliate = []
    for name, url in AFFILIATE_SOURCES.items():
        source = direct_source(url); row = {"program": name, "company": name, "url": url, "source": source, "commission": "UNKNOWN_UNTIL_AGREEMENT", "commission_type": "UNKNOWN", "recurring": "UNKNOWN", "cookie_window": "UNKNOWN", "payout_terms": "UNKNOWN", "traffic_restrictions": "REVIEW_DIRECT_TERMS", "geography": "SOURCE_DEPENDENT", "goclear_fit": "POTENTIAL_BUSINESS_BANKING_WORKFLOW", "nexus_fit": "RESEARCH_ONLY", "confidence": "MEDIUM" if source["status"] == "RETRIEVED" else "UNKNOWN"}
        affiliate.append(row); append_record("alpha_outcomes", {"outcome_id": "affiliate_" + fp(row), "route": "finance_affiliate_review", "status": "CANDIDATE", "source_url": url, "program": name, "authority": "No referral link activated", "created_at": now()})
    write("commercial_mission.json", {"package": package, "affiliate_candidates": affiliate, "lineage": {"alpha_claim": evidence.get("claim_id"), "finance": "preflight_required", "creative": campaign_id, "growth": "validation_ready"}, "real_world_test": "NOT_AUTHORIZED_NO_SPEND_CHANNEL_PROVEN", "generated_at": now()})
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    PREVIEW.write_text("""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>SEO Readiness Review</title><style>body{margin:0;background:#f4f7fb;color:#172033;font:16px system-ui,sans-serif}main{max-width:920px;margin:auto;padding:clamp(28px,7vw,80px) 22px}.eyebrow{color:#3566d4;font-weight:700;letter-spacing:.08em;text-transform:uppercase}.hero{background:#fff;border:1px solid #dce4f0;border-radius:24px;padding:clamp(26px,6vw,64px);box-shadow:0 16px 40px #17203312}h1{font-size:clamp(2.2rem,6vw,4.8rem);line-height:1.02;margin:16px 0}p{line-height:1.65;color:#536176}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:28px 0}.card{background:#eef3fb;border-radius:16px;padding:20px}.cta{display:inline-block;background:#3566d4;color:white;border-radius:12px;padding:15px 20px;text-decoration:none;font-weight:700}@media(max-width:680px){.grid{grid-template-columns:1fr}main{padding:18px}.hero{border-radius:18px}}</style></head><body><main><section class='hero'><div class='eyebrow'>Evidence-led readiness review</div><h1>Turn technical SEO uncertainty into a prioritized plan.</h1><p>Know what to check before buying more tools or producing more content. This draft explains the review without promising rankings or fabricated results.</p><div class='grid'><div class='card'><b>01</b><p>Identify technical unknowns.</p></div><div class='card'><b>02</b><p>Prioritize evidence-backed fixes.</p></div><div class='card'><b>03</b><p>Choose the next bounded test.</p></div></div><a class='cta' href='#request'>Request a readiness review</a><p id='request'><small>Internal draft only. No publication, affiliate link, or performance guarantee.</small></p></section></main></body></html>""")
    print(json.dumps({"ok": True, "campaign_id": campaign_id, "affiliate_candidates": len(affiliate), "preview": str(PREVIEW), "status": "VALIDATION_READY"}, indent=2))

if __name__ == "__main__": main()
