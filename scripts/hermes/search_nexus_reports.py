#!/usr/bin/env python3

import argparse
import json
import os
import glob as globmod
from datetime import datetime

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
REPORTS_RUNTIME = os.path.join(PROJECT_ROOT, "reports", "runtime")
REPORTS_MANUAL = os.path.join(PROJECT_ROOT, "reports", "manual_publish")


def _load_json_file(path: str) -> dict | None:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _score_report(data: dict, query_words: list) -> int:
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


def search_reports(query: str) -> dict:
    query_words = query.lower().split()
    results = []

    search_dirs = []
    if os.path.isdir(REPORTS_RUNTIME):
        search_dirs.append(REPORTS_RUNTIME)
    if os.path.isdir(REPORTS_MANUAL):
        search_dirs.append(REPORTS_MANUAL)

    for search_dir in search_dirs:
        for path in globmod.glob(os.path.join(search_dir, "*.json")):
            data = _load_json_file(path)
            if not data:
                continue

            score = _score_report(data, query_words)
            if score > 0:
                results.append({
                    "file": os.path.basename(path),
                    "directory": os.path.basename(os.path.dirname(path)),
                    "path": path,
                    "score": score,
                    "preview": _extract_preview(data, query_words),
                    "keys": list(data.keys())[:10],
                })

    results.sort(key=lambda r: r["score"], reverse=True)

    return {
        "query": query,
        "results": results[:15],
        "total_matches": len(results),
        "searched_at": datetime.utcnow().isoformat() + "Z",
    }


def main():
    parser = argparse.ArgumentParser(description="Search Nexus reports")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    args = parser.parse_args()

    try:
        result = search_reports(args.query)
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
            print(f"  - {r['file']} (score: {r['score']})")


if __name__ == "__main__":
    main()
