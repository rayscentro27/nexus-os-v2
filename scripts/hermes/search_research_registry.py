#!/usr/bin/env python3

import argparse
import json
import os
import glob as globmod
from datetime import datetime

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
DATA_RESEARCH = os.path.join(PROJECT_ROOT, "data", "research")
REPORTS_RUNTIME = os.path.join(PROJECT_ROOT, "reports", "runtime")


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
    for key in ("title", "name", "opportunity", "candidate", "description"):
        if key in data and isinstance(data[key], str):
            return data[key][:100]
    return "Untitled"


def search_research_registry(query: str) -> dict:
    query_words = query.lower().split()
    results = []

    search_paths = []
    if os.path.isdir(DATA_RESEARCH):
        for path in globmod.glob(os.path.join(DATA_RESEARCH, "*.json")):
            search_paths.append(path)

    if os.path.isdir(REPORTS_RUNTIME):
        for path in globmod.glob(os.path.join(REPORTS_RUNTIME, "research_*.json")):
            search_paths.append(path)

    for path in search_paths:
        data = _load_json_file(path)
        if not data:
            continue

        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            for key in ("research", "candidates", "opportunities", "items", "data"):
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break
            if not items:
                items = [data]

        for item in items:
            score = _score_item(item, query_words)
            if score > 0:
                results.append({
                    "title": _extract_title(item),
                    "source": os.path.basename(path),
                    "score": score,
                    "preview": _extract_preview(item, query_words),
                    "type": "research_candidate",
                })

    results.sort(key=lambda r: r["score"], reverse=True)

    return {
        "query": query,
        "results": results[:15],
        "total_matches": len(results),
        "searched_at": datetime.utcnow().isoformat() + "Z",
    }


def main():
    parser = argparse.ArgumentParser(description="Search research registry")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    args = parser.parse_args()

    try:
        result = search_research_registry(args.query)
    except Exception as e:
        result = {
            "query": args.query,
            "results": [],
            "total_matches": 0,
            "error": str(e),
        }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Query: {result['query']}")
        print(f"Total matches: {result['total_matches']}")
        for r in result["results"][:5]:
            print(f"  - {r['title']} (score: {r['score']}, from: {r['source']})")


if __name__ == "__main__":
    main()
