#!/usr/bin/env python3
"""Deterministic research scoring helpers for CLI use."""
from __future__ import annotations

import argparse
import json

from common import score_research_text


def scoring_profile(text: str, topic: str) -> dict:
    blob = f"{text} {topic}".lower()
    base = score_research_text(text, topic)
    # Domain phrases outrank ambiguous words such as "strategy" or "market".
    # Credit/funding videos often discuss a business strategy without being trading research.
    credit_domain = sum(x in blob for x in ("credit repair", "business credit", "business funding", "funding company", "loan", "lender")) >= 2
    trading_domain = any(x in blob for x in ("crypto", "forex", "backtest", "drawdown", "trading system", "broker execution", "open positions"))
    if trading_domain and not credit_domain:
        return {
            "profile": "trading_paper_research",
            "paper_strategy_potential": base["money_potential"],
            "clarity_of_rules": base["testability"],
            "backtestability": base["testability"],
            "risk_reward_discussion": max(0, 100 - base["compliance_risk"]),
            "drawdown_risk_caution": max(0, 100 - base["compliance_risk"]),
            "market_specificity": base["uniqueness"],
            "educational_value": base["content_potential"],
            "compliance_safety_risk": base["compliance_risk"],
            "overall_score": base["overall_score"],
            "paper_only": True,
            "live_trading_blocked": True,
        }
    if any(x in blob for x in ("ai", "automation", "online business", "marketing", "product", "offer")) and not credit_domain:
        return {
            "profile": "ai_online_business_marketing",
            "offer_potential": base["money_potential"],
            "product_strategy_value": base["money_potential"],
            "content_potential": base["content_potential"],
            "automation_leverage": base["implementation_difficulty"],
            "seo_potential": base["seo_potential"],
            "affiliate_potential": base["affiliate_potential"],
            "implementation_speed": max(0, 100 - base["implementation_difficulty"]),
            "uniqueness": base["uniqueness"],
            "testability": base["testability"],
            "risk": base["compliance_risk"],
            "overall_score": base["overall_score"],
        }
    return {
        "profile": "credit_business_funding",
        **base,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default="")
    parser.add_argument("--topic", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    print(json.dumps({"ok": True, "scores": scoring_profile(args.text, args.topic)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
