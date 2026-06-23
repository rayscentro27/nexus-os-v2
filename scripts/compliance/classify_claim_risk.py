#!/usr/bin/env python3
"""Nexus OS v2 — deterministic claim-risk classifier (reusable, offline).

Classifies text for compliance risk in high-stakes domains (credit/funding/lending/debt/tax/
legal/health/investing/trading/options/crypto/income/government-benefits). No external calls.

Classes: safe_educational | needs_source_verification | needs_compliance_review |
         do_not_use_client_facing | misleading_or_hype

    python3 scripts/compliance/classify_claim_risk.py --text "..."
    python3 scripts/compliance/classify_claim_risk.py --self-test
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DOMAINS = {
    "credit_repair": r"credit repair|dispute|delete (items|accounts)|inquir(y|ies)",
    "business_funding": r"business funding|funding stack|0% (business )?credit|capital",
    "lending": r"lender|underwrit|loan approval|bank approval",
    "debt_collections": r"debt|collections|charge[- ]?off",
    "tax": r"\btax(es)?\b|irs|write[- ]?off",
    "legal": r"\blegal\b|lawsuit|sue|attorney|fcra|fdcpa",
    "health": r"health|medical|cure|treatment",
    "investing": r"invest(ing|ment)|portfolio|robo[- ]?advisor|wealth",
    "trading": r"trad(e|ing)|forex|prop firm",
    "options": r"\boption(s)?\b|covered call|cash[- ]secured put",
    "crypto": r"crypto|bitcoin|token|defi",
    "income_claims": r"\$\d[\d,]*\s*(\/|per )?(day|week|month|mo)|make \$?\d|income",
    "gov_benefits_workforce": r"government (pay|grant|benefit)|workforce|eligibility|free money",
    "real_estate": r"real estate|listing|fair housing|tenant|property",
}

# (flag, regex, severity) — severity 3 = hype/misleading, 2 = compliance, 1 = verify
FLAGS = [
    ("guarantee", r"(?<!no )guarantee[ds]?\b", 2),
    ("guaranteed_approval", r"(?<!no )guarantee[ds]?\s+(\w+\s+){0,2}?(funding|approval|loan|approved)", 3),
    ("guaranteed_deletion", r"(?<!no )guaranteed (deletion|removal)|(?<!won't )will (be )?delete", 3),
    ("guaranteed_score", r"(score|points?) (increase|boost) guaranteed|(?<!no )guaranteed \d+ points", 3),
    ("no_choice", r"they have no choice|legally must|forced to delete", 3),
    ("secret_loophole", r"secret|hack|loophole|trick the (bank|lender|system)", 3),
    ("both_ways", r"make money both ways|win either way|can'?t lose", 3),
    ("gov_pays_everyone", r"government will pay everyone|free money for everyone|everyone qualifies", 3),
    ("exact_income_no_proof", r"\$\d[\d,]*\s*(\/|per )?(day|week|month)", 2),
    ("live_trading", r"live trad(e|ing)|execute (a )?trade|go live", 2),
    ("approval_claim", r"(get|guarantee) (you )?(approved|funding|the loan)", 2),
    ("no_docs", r"no doc(s|ument)?|stated income", 2),
    ("inquiry_wipe", r"wipe (inquir|hard pull)|remove (all )?inquiries", 3),
    ("debt_hype", r"deploy (debt|capital)|use debt to get rich|stack (cards|debt)", 2),
    ("fair_housing", r"steer|only rent to|prefer (families|no kids|nationality)", 3),
]


def classify(text: str) -> dict:
    t = (text or "").lower()
    domains = [d for d, rx in DOMAINS.items() if re.search(rx, t)]
    flags = [(name, sev) for name, rx, sev in FLAGS if re.search(rx, t)]
    flag_names = [f[0] for f in flags]
    max_sev = max([f[1] for f in flags], default=0)
    high_risk_domain = bool(set(domains) & {"credit_repair", "business_funding", "lending", "debt_collections",
                                            "tax", "legal", "health", "investing", "trading", "options", "crypto",
                                            "income_claims", "gov_benefits_workforce"})
    has_disclaimer = bool(re.search(r"no guarantee|not (a )?guarantee|outcomes? (vary|are not guaranteed)|education only", t))

    if max_sev >= 3:
        risk_class = "misleading_or_hype"
    elif high_risk_domain and max_sev >= 2:
        risk_class = "do_not_use_client_facing"
    elif high_risk_domain:
        risk_class = "needs_compliance_review" if not has_disclaimer else "safe_educational"
    elif re.search(r"\d+%|\bstud(y|ies)\b|statistic|average|\d+ out of \d+", t):
        risk_class = "needs_source_verification"
    else:
        risk_class = "safe_educational"

    return {"risk_class": risk_class, "domains": domains, "flags": flag_names,
            "max_severity": max_sev, "has_disclaimer": has_disclaimer,
            "client_facing_safe": risk_class in ("safe_educational",)}


def _self_test() -> int:
    cases = [
        "This guarantees funding approval in 30 days.",
        "There's a secret loophole to wipe all inquiries — they have no choice.",
        "Credit utilization under 30% can help your score over time. No guarantees.",
        "Make $5,000 per day with this trading bot, you can't lose.",
        "The government will pay everyone over 50 to learn AI.",
        "Studies show 70% of applicants miss a step before applying.",
    ]
    for c in cases:
        r = classify(c)
        print(f"- {c[:54]!r:56} -> {r['risk_class']:24} flags={r['flags']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if not args.text:
        print("provide --text or --self-test"); return 1
    result = classify(args.text)
    # workflow mode: log to ledger if Supabase is reachable
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "social"))
        from _supabase import configured, event
        if configured():
            event("system", "claim_risk_classified", "success",
                  f"Claim risk: {result['risk_class']}", f"flags: {', '.join(result['flags']) or 'none'}")
    except Exception:
        pass
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
