"""Bounded read-only acquisition from TradingView's designated public scripts page."""
from __future__ import annotations

import html
import json
import re
import subprocess
from typing import Any

LISTING = "https://www.tradingview.com/scripts/editors-picks/"
MAX_PAGE_BYTES = 1_500_000


def _fetch(url: str) -> str:
    def fetch() -> str:
        result = subprocess.run(["curl", "-fsSL", "--max-time", "18", "-A", "Mozilla/5.0 (compatible; NexusResearch/1.0)", url],
                               capture_output=True, timeout=20, check=False)
        if result.returncode:
            raise RuntimeError(f"public_fetch_failed:{result.returncode}:{result.stderr[-180:].decode(errors='replace')}")
        return result.stdout[:MAX_PAGE_BYTES].decode("utf-8", errors="replace")
    from nexus_agent_platform.provider_enforcement import execute_public_read
    return execute_public_read("BROWSER_EXTERNAL_SERVICES", "tradingview_public_research", fetch, response_bytes=MAX_PAGE_BYTES)


def _meta(doc: str, key: str, attr: str = "property") -> str:
    m = re.search(rf'<meta[^>]+{attr}="{re.escape(key)}"[^>]+content="([^"]*)"', doc, re.I)
    return html.unescape(m.group(1)) if m else ""


def _json_value(doc: str, key: str) -> Any:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*("(?:\\.|[^"])*"|\d+(?:\.\d+)?|true|false|null)', doc)
    if not match: return None
    try: return json.loads(match.group(1))
    except ValueError: return match.group(1).strip('"')


def _classify(title: str, doc: str) -> tuple[str, str, str]:
    lower = title.lower()
    kind = "STRATEGY" if "strategy" in lower else "LIBRARY" if "library" in lower else "INDICATOR" if "indicator" in lower else "UNKNOWN"
    source_code = re.search(r'"tree"\s*:\s*"//@version', doc) is not None or "//@version" in doc
    access = "OPEN_SOURCE" if source_code else "UNKNOWN"
    if not source_code and re.search(r'\b(protected|invite.only|invite-only)\b', doc, re.I): access = "PROTECTED" if "protected" in doc.lower() else "INVITE_ONLY"
    return kind, access, "PINE_SOURCE_PRESENT" if source_code else "SOURCE_NOT_EXPOSED"


def _logic_observations(doc: str, access: str) -> dict[str, Any]:
    if access != "OPEN_SOURCE":
        return {"source_logic_inspected": False, "observations": [], "reason": "PINE_SOURCE_NOT_PUBLICLY_EXPOSED"}
    match = re.search(r'"tree"\s*:\s*"((?:\\.|[^"\\])*)"', doc)
    if not match:
        return {"source_logic_inspected": False, "observations": [], "reason": "CODE_PAYLOAD_NOT_PARSED"}
    try: code = json.loads('"' + match.group(1) + '"')
    except ValueError: code = match.group(1).replace("\\n", "\n")
    tests = [("uses_strategy_entries", r"\bstrategy\.(entry|order)\s*\("),
             ("defines_strategy_exits", r"\bstrategy\.(exit|close)\s*\("),
             ("uses_multi_timeframe_requests", r"\brequest\.security\s*\("),
             ("uses_atr_or_volatility_logic", r"\b(ta\.atr|atr\s*\(|stdev|standarddev)\b"),
             ("contains_explicit_stop_or_risk_terms", r"(?i)stop|drawdown|risk|loss"),
             ("plots_indicator_outputs", r"\b(plot|plotshape|plotchar)\s*\(" )]
    observations = [label for label, pattern in tests if re.search(pattern, code)]
    return {"source_logic_inspected": True, "source_logic_chars": len(code),
            "observations": observations, "does_not_validate_performance": True}


def discover(limit: int = 8) -> dict[str, Any]:
    """Fetch one public listing and a small number of public script detail pages."""
    listing = _fetch(LISTING)
    urls = list(dict.fromkeys(html.unescape(x).split("#", 1)[0] for x in
                              re.findall(r'href="(https://www\.tradingview\.com/script/[^\"]+)"', listing)))
    candidates = []
    errors = []
    for url in urls[:max(1, min(int(limit), 12))]:
        try:
            doc = _fetch(url)
            og = _meta(doc, "og:title")
            title = re.sub(r"\s*[—-]\s*(Indicator|Strategy|Library) by .*?$", "", og, flags=re.I).strip() or og
            description = _meta(doc, "description", "name")
            # TradingView embeds public script metadata as JSON. Do not infer
            # omitted metadata or claims from chart examples.
            kind, access, source_status = _classify(og, doc)
            logic = _logic_observations(doc, access)
            author_match = re.search(r"\bby\s+([^—-]+)$", og, re.I)
            author = author_match.group(1).strip() if author_match else None
            created = _json_value(doc, "created_at")
            updated = _json_value(doc, "updated_at")
            likes = _json_value(doc, "likes_count")
            views = _json_value(doc, "views")
            comments = _json_value(doc, "comments_count")
            script_id_match = re.search(r"/script/([A-Za-z0-9]+)-", url)
            script_id = script_id_match.group(1) if script_id_match else None
            claimed = re.findall(r"(?:\d+(?:\.\d+)?\s?%\s?(?:win|return|profit)|profit factor\s*[:=]?\s*\d+(?:\.\d+)?)", description, re.I)
            observations = logic.get("observations", [])
            risk_evidence = any(x in observations for x in ("contains_explicit_stop_or_risk_terms", "defines_strategy_exits"))
            candidates.append({"title": title, "url": url, "source_class": "TRADINGVIEW_PUBLIC_SCRIPTS",
                "script_id": script_id, "script_type": kind, "access_type": access, "source_code_status": source_status,
                "source_logic_inspection": logic,
                "market": "UNKNOWN", "timeframe": "UNKNOWN", "author": author,
                "published_at": created, "updated_at": updated, "description": description[:2400],
                "claimed_metrics": claimed, "risk_rules": "RISK_OR_EXIT_LOGIC_VISIBLE" if risk_evidence else "NOT_ESTABLISHED_FROM_VISIBLE_SOURCE",
                "novelty": "CANDIDATE_REQUIRES_COMPARISON", "engagement_signal": {"likes": likes,"comments":comments,"views":views},
                "query": "TradingView Editor's Picks public scripts", "domain": "tradingview.com",
                "snippet": description[:1000], "firsthand_or_secondary": "FIRSTHAND_SCRIPT_AUTHOR_DESCRIPTION",
                "discovered_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                "qualification_status": "UNASSESSED"})
        except Exception as exc:
            errors.append({"url": url, "error": f"{type(exc).__name__}:{exc}"[:240]})
    return {"source": LISTING, "listing_status": "PASS", "items_checked": len(candidates),
            "urls_discovered": len(urls), "items": candidates, "errors": errors,
            "access_method": "public HTML pages via bounded curl; no login or authenticated scraping"}
