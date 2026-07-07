#!/usr/bin/env python3
"""
Evidence Merge — Merges web search results into internal drafts.

Core principle: Brave evidence enriches the internal draft.
It must not replace Nexus/GoClear-specific reasoning with generic snippets.
"""

import re


def merge_evidence_into_draft(draft, brave_results, rubric=None):
    """
    Merge Brave search results into the internal draft.
    Returns an enriched draft dict.
    """
    if not brave_results or not brave_results.get("results"):
        return draft

    results = brave_results.get("results", [])
    if not results:
        return draft

    # Default rubric weights
    if rubric is None:
        rubric = {
            "speed_to_cash": 0.25,
            "fit_for_goclear": 0.25,
            "cost_to_execute": 0.15,
            "ease": 0.10,
            "evidence_quality": 0.15,
            "compliance_risk": 0.10,
        }

    existing_titles = {item.get("title", "").lower() for item in draft.get("items", [])}

    # --- Add web results as new items if they are concrete ---
    new_items = []
    for i, result in enumerate(results[:3], len(draft.get("items", [])) + 1):
        title = _clean_html(result.get("title", f"Web Result {i}"))
        snippet = _clean_html(result.get("snippet", ""))
        url = result.get("url", "")

        # Skip if already covered by internal draft
        if _is_duplicate(title, existing_titles):
            continue

        # Score the web result
        score = _score_web_result(title, snippet, draft.get("topic", ""), rubric)

        new_items.append({
            "index": i,
            "title": title[:100],
            "summary": snippet[:300],
            "score": score,
            "url": url,
            "source": "brave",
            "evidence": [f"Web source: {url}"] if url else [],
            "risk": ["Verify before acting on web-sourced information"],
            "next_action": f"Review {title[:40]} for fit with GoClear strategy.",
        })

    # --- Merge: add new items, re-sort by score ---
    all_items = draft.get("items", []) + new_items
    all_items.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Re-index
    for i, item in enumerate(all_items, 1):
        item["index"] = i

    # Update draft
    draft["items"] = all_items[:8]  # Cap at 8 items

    # Update top_index
    if draft["items"]:
        draft["top_index"] = draft["items"][0].get("index", 1)

    # Mark that web was used
    draft["web_enriched"] = True
    draft["web_items_added"] = len(new_items)

    # Clear evidence gaps that were filled
    filled_gaps = []
    for gap in draft.get("evidence_gaps", []):
        if any(kw in gap.lower() for kw in ["web", "fresh", "current", "external"]):
            filled_gaps.append(gap)
    for gap in filled_gaps:
        draft["evidence_gaps"].remove(gap)

    return draft


def _score_web_result(title, snippet, topic, rubric):
    """Score a web result for relevance and quality."""
    score = 5.0
    combined = (title + " " + snippet).lower()
    topic_lower = topic.lower()

    # Speed to cash
    if any(kw in combined for kw in ["today", "immediate", "instant", "same-day", "quick"]):
        score += rubric.get("speed_to_cash", 0.25) * 3
    elif any(kw in combined for kw in ["this week", "fast", "soon"]):
        score += rubric.get("speed_to_cash", 0.25) * 1.5

    # Fit for GoClear
    if any(kw in combined for kw in ["credit", "readiness", "funding", "business credit"]):
        score += rubric.get("fit_for_goclear", 0.25) * 3
    elif any(kw in combined for kw in ["goclear", "nexus"]):
        score += rubric.get("fit_for_goclear", 0.25) * 4

    # Cost
    if any(kw in combined for kw in ["free", "low-cost", "no cost", "$0"]):
        score += rubric.get("cost_to_execute", 0.15) * 3

    # Evidence quality
    if url_present(snippet):
        score += rubric.get("evidence_quality", 0.15) * 2
    if len(snippet) > 100:
        score += rubric.get("evidence_quality", 0.15) * 1

    # Penalty for generic content
    if any(kw in combined for kw in ["research core", "identify quick wins", "map competitive landscape"]):
        score -= 2.0

    return round(min(max(score, 1.0), 10.0), 1)


def _is_duplicate(new_title, existing_titles):
    """Check if a web result is already covered by the internal draft."""
    new_lower = new_title.lower()
    for existing in existing_titles:
        # Check for significant overlap
        new_words = set(new_lower.split())
        exist_words = set(existing.split())
        if len(new_words & exist_words) / max(len(new_words | exist_words), 1) > 0.6:
            return True
    return False


def url_present(text):
    """Check if text contains a URL."""
    return bool(re.search(r"https?://", text))


def _clean_html(text):
    """Remove HTML tags from text."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", str(text)).strip()
