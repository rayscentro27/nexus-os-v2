#!/usr/bin/env python3

import argparse
import json
import os
import glob as globmod
import re
from datetime import datetime

sys_path = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(sys_path, "..", "..")

REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")


def _load_json_file(path: str) -> dict | None:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _search_reports(query: str) -> list:
    matches = []
    sources = []
    patterns = [
        os.path.join(REPORTS_DIR, "runtime", "*.json"),
        os.path.join(REPORTS_DIR, "manual_publish", "*.json"),
    ]
    for pattern in patterns:
        for path in globmod.glob(pattern):
            data = _load_json_file(path)
            if not data:
                continue
            text = json.dumps(data).lower()
            query_lower = query.lower()
            words = query_lower.split()
            score = 0
            for word in words:
                if len(word) > 2 and word in text:
                    score += text.count(word)
            if score > 0:
                matches.append({
                    "source": os.path.basename(path),
                    "score": score,
                    "preview": _extract_preview(text, query_lower),
                })
                sources.append(os.path.basename(path))
    return matches, sources


def _search_research_registry(query: str) -> list:
    matches = []
    patterns = [
        os.path.join(DATA_DIR, "research", "*.json"),
        os.path.join(REPORTS_DIR, "runtime", "research_*.json"),
    ]
    for pattern in patterns:
        for path in globmod.glob(pattern):
            data = _load_json_file(path)
            if not data:
                continue
            text = json.dumps(data).lower()
            query_lower = query.lower()
            words = query_lower.split()
            score = 0
            for word in words:
                if len(word) > 2 and word in text:
                    score += text.count(word)
            if score > 0:
                matches.append({
                    "source": os.path.basename(path),
                    "score": score,
                    "preview": _extract_preview(text, query_lower),
                })
    return matches


def _search_offer_registry(query: str) -> list:
    matches = []
    patterns = [
        os.path.join(DATA_DIR, "offers", "*.json"),
        os.path.join(DATA_DIR, "offer_registry", "*.json"),
    ]
    for pattern in patterns:
        for path in globmod.glob(pattern):
            data = _load_json_file(path)
            if not data:
                continue
            text = json.dumps(data).lower()
            query_lower = query.lower()
            words = query_lower.split()
            score = 0
            for word in words:
                if len(word) > 2 and word in text:
                    score += text.count(word)
            if score > 0:
                matches.append({
                    "source": os.path.basename(path),
                    "score": score,
                    "preview": _extract_preview(text, query_lower),
                })
    return matches


def _search_revenue_dashboard(query: str) -> list:
    matches = []
    patterns = [
        os.path.join(DATA_DIR, "revenue", "*.json"),
        os.path.join(REPORTS_DIR, "runtime", "revenue_*.json"),
    ]
    for pattern in patterns:
        for path in globmod.glob(pattern):
            data = _load_json_file(path)
            if not data:
                continue
            text = json.dumps(data).lower()
            query_lower = query.lower()
            words = query_lower.split()
            score = 0
            for word in words:
                if len(word) > 2 and word in text:
                    score += text.count(word)
            if score > 0:
                matches.append({
                    "source": os.path.basename(path),
                    "score": score,
                    "preview": _extract_preview(text, query_lower),
                })
    return matches


def _search_blocker_matrix(query: str) -> list:
    matches = []
    patterns = [
        os.path.join(DATA_DIR, "blockers", "*.json"),
        os.path.join(REPORTS_DIR, "runtime", "blocker_*.json"),
    ]
    for pattern in patterns:
        for path in globmod.glob(pattern):
            data = _load_json_file(path)
            if not data:
                continue
            text = json.dumps(data).lower()
            query_lower = query.lower()
            words = query_lower.split()
            score = 0
            for word in words:
                if len(word) > 2 and word in text:
                    score += text.count(word)
            if score > 0:
                matches.append({
                    "source": os.path.basename(path),
                    "score": score,
                    "preview": _extract_preview(text, query_lower),
                })
    return matches


def _extract_preview(text: str, query: str, context_len: int = 120) -> str:
    idx = text.find(query.split()[0] if query.split() else "")
    if idx == -1:
        idx = 0
    start = max(0, idx - context_len // 2)
    end = min(len(text), idx + context_len // 2)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def _generate_suggested_answer(all_matches: list, query: str) -> str | None:
    if not all_matches:
        return None

    sorted_matches = sorted(all_matches, key=lambda m: m.get("score", 0), reverse=True)
    top = sorted_matches[0]

    source = top.get("source", "a report")
    preview = top.get("preview", "")

    return f"Based on {source}: {preview}"


def search_context(query: str) -> dict:
    all_matches = []
    all_sources = []

    report_matches, report_sources = _search_reports(query)
    all_matches.extend(report_matches)
    all_sources.extend(report_sources)

    research_matches = _search_research_registry(query)
    all_matches.extend(research_matches)
    all_sources.extend([m["source"] for m in research_matches])

    offer_matches = _search_offer_registry(query)
    all_matches.extend(offer_matches)
    all_sources.extend([m["source"] for m in offer_matches])

    revenue_matches = _search_revenue_dashboard(query)
    all_matches.extend(revenue_matches)
    all_sources.extend([m["source"] for m in revenue_matches])

    blocker_matches = _search_blocker_matrix(query)
    all_matches.extend(blocker_matches)
    all_sources.extend([m["source"] for m in blocker_matches])

    total_score = sum(m.get("score", 0) for m in all_matches)
    max_possible = max(total_score, 1)
    confidence = min(total_score / (max_possible * 0.5), 1.0) if total_score > 0 else 0.0

    suggested_answer = _generate_suggested_answer(all_matches, query)

    return {
        "matches": all_matches[:20],
        "sources": list(set(all_sources)),
        "confidence": round(confidence, 3),
        "suggested_answer": suggested_answer,
        "note": "I can search Nexus records now; web research needs connector/tool setup.",
        "searched_at": datetime.utcnow().isoformat() + "Z",
    }


def main():
    parser = argparse.ArgumentParser(description="Search Hermes context")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    args = parser.parse_args()

    try:
        result = search_context(args.query)
    except Exception as e:
        result = {
            "matches": [],
            "sources": [],
            "confidence": 0,
            "suggested_answer": None,
            "error": str(e),
            "note": "I can search Nexus records now; web research needs connector/tool setup.",
        }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Matches: {len(result['matches'])}")
        print(f"Sources: {', '.join(result['sources'])}")
        print(f"Confidence: {result['confidence']}")
        if result.get("suggested_answer"):
            print(f"Suggested answer: {result['suggested_answer']}")
        print(f"Note: {result.get('note', '')}")


if __name__ == "__main__":
    main()
