#!/usr/bin/env python3

import argparse
import json
import os
import glob as globmod
from datetime import datetime

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports", "runtime")


def _load_json_file(path: str) -> dict | None:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _score_item(data: dict, query_words: list) -> int:
    text = json.dumps(data).lower()
    score = 0
    for word in query_words:
        if len(word) > 2 and word in text:
            score += text.count(word)
    return score


def _extract_preview(data: dict, query_words: list, context_len: int = 150) -> str:
    text = json.dumps(data).lower()
    idx = -1
    for word in query_words:
        pos = text.find(word)
        if pos != -1:
            idx = pos
            break
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


def _extract_title(data: dict) -> str:
    for key in ("title", "name", "opportunity", "description", "label"):
        if key in data and isinstance(data[key], str):
            return data[key][:100]
    return "Business item"


def _search_opportunities(query_words: list) -> list:
    results = []
    patterns = [
        os.path.join(DATA_DIR, "opportunities", "*.json"),
        os.path.join(DATA_DIR, "research", "*.json"),
        os.path.join(REPORTS_DIR, "research_*.json"),
    ]
    for pattern in patterns:
        for path in globmod.glob(pattern):
            data = _load_json_file(path)
            if not data:
                continue
            items = data if isinstance(data, list) else [data]
            for item in items:
                score = _score_item(item, query_words)
                if score > 0:
                    results.append({
                        "title": _extract_title(item),
                        "source": os.path.basename(path),
                        "category": "opportunity",
                        "score": score,
                        "preview": _extract_preview(item, query_words),
                    })
    return results


def _search_credit_data(query_words: list) -> list:
    results = []
    patterns = [
        os.path.join(DATA_DIR, "credit", "*.json"),
        os.path.join(DATA_DIR, "funding", "*.json"),
        os.path.join(DATA_DIR, "financial", "*.json"),
        os.path.join(REPORTS_DIR, "revenue_*.json"),
    ]
    for pattern in patterns:
        for path in globmod.glob(pattern):
            data = _load_json_file(path)
            if not data:
                continue
            items = data if isinstance(data, list) else [data]
            for item in items:
                score = _score_item(item, query_words)
                if score > 0:
                    results.append({
                        "title": _extract_title(item),
                        "source": os.path.basename(path),
                        "category": "credit",
                        "score": score,
                        "preview": _extract_preview(item, query_words),
                    })
    return results


def _search_monetization_data(query_words: list) -> list:
    results = []
    patterns = [
        os.path.join(DATA_DIR, "monetization", "*.json"),
        os.path.join(DATA_DIR, "revenue", "*.json"),
        os.path.join(DATA_DIR, "pricing", "*.json"),
        os.path.join(REPORTS_DIR, "revenue_*.json"),
    ]
    for pattern in patterns:
        for path in globmod.glob(pattern):
            data = _load_json_file(path)
            if not data:
                continue
            items = data if isinstance(data, list) else [data]
            for item in items:
                score = _score_item(item, query_words)
                if score > 0:
                    results.append({
                        "title": _extract_title(item),
                        "source": os.path.basename(path),
                        "category": "monetization",
                        "score": score,
                        "preview": _extract_preview(item, query_words),
                    })
    return results


def search_business_context(query: str) -> dict:
    query_words = query.lower().split()
    all_results = []

    all_results.extend(_search_opportunities(query_words))
    all_results.extend(_search_credit_data(query_words))
    all_results.extend(_search_monetization_data(query_words))

    all_results.sort(key=lambda r: r["score"], reverse=True)

    total_score = sum(r["score"] for r in all_results)
    confidence = min(total_score / 10.0, 1.0) if total_score > 0 else 0.0

    return {
        "query": query,
        "results": all_results[:15],
        "total_matches": len(all_results),
        "confidence": round(confidence, 3),
        "categories_found": list(set(r["category"] for r in all_results)),
        "searched_at": datetime.utcnow().isoformat() + "Z",
    }


def main():
    parser = argparse.ArgumentParser(description="Search business context")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    args = parser.parse_args()

    try:
        result = search_business_context(args.query)
    except Exception as e:
        result = {
            "query": args.query,
            "results": [],
            "total_matches": 0,
            "confidence": 0,
            "error": str(e),
        }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Query: {result['query']}")
        print(f"Total matches: {result['total_matches']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Categories: {', '.join(result.get('categories_found', []))}")
        for r in result["results"][:5]:
            print(f"  - [{r['category']}] {r['title']} (score: {r['score']})")


if __name__ == "__main__":
    main()
