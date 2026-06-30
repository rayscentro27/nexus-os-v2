#!/usr/bin/env python3

import argparse
import json
import os
import glob as globmod
from datetime import datetime


REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "reports", "runtime"
)
DATA_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "data"
)


def _load_json_file(path: str) -> dict | None:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _load_reports() -> list:
    reports = []
    pattern = os.path.join(REPORTS_DIR, "*.json")
    for path in globmod.glob(pattern):
        data = _load_json_file(path)
        if data:
            reports.append({"source": os.path.basename(path), "data": data})
    return reports


def _safe_extend(target: list, value) -> list:
    if isinstance(value, list):
        target.extend(value)
    elif isinstance(value, dict):
        target.append(value)
    return target


def _extract_ray_review_cards(data: list) -> list:
    cards = []
    for report in data:
        d = report.get("data", {})
        if "rayReviewCards" in d:
            _safe_extend(cards, d["rayReviewCards"])
        if "cards" in d:
            _safe_extend(cards, d["cards"])
    return cards


def _extract_offers(data: list) -> list:
    offers = []
    for report in data:
        d = report.get("data", {})
        if "offers" in d:
            _safe_extend(offers, d["offers"])
        if "offerRegistry" in d:
            _safe_extend(offers, d["offerRegistry"])
    return offers


def _extract_research_candidates(data: list) -> list:
    candidates = []
    for report in data:
        d = report.get("data", {})
        if "researchCandidates" in d:
            _safe_extend(candidates, d["researchCandidates"])
        if "candidates" in d:
            _safe_extend(candidates, d["candidates"])
        if "research" in d:
            _safe_extend(candidates, d["research"])
    return candidates


def _extract_blockers(data: list) -> list:
    blockers = []
    for report in data:
        d = report.get("data", {})
        if "blockers" in d:
            _safe_extend(blockers, d["blockers"])
        if "blockerMatrix" in d:
            _safe_extend(blockers, d["blockerMatrix"])
    return blockers


def _check_running_safely(data: list) -> bool:
    for report in data:
        d = report.get("data", {})
        if "runningSafely" in d:
            return d["runningSafely"]
        if "status" in d:
            if d["status"] in ("healthy", "running", "safe"):
                return True
    return True


def _extract_money_actions(data: list) -> list:
    actions = []
    for report in data:
        d = report.get("data", {})
        if "moneyActions" in d:
            _safe_extend(actions, d["moneyActions"])
        if "revenue" in d:
            actions.append(d["revenue"])
        if "financial" in d:
            actions.append(d["financial"])
    return actions


def _extract_approvals_needed(data: list) -> list:
    approvals = []
    for report in data:
        d = report.get("data", {})
        if "approvalsNeeded" in d:
            _safe_extend(approvals, d["approvalsNeeded"])
        if "approvals" in d:
            _safe_extend(approvals, d["approvals"])
        if "pendingApprovals" in d:
            _safe_extend(approvals, d["pendingApprovals"])
    return approvals


def load_context() -> dict:
    reports = _load_reports()

    if not reports:
        return {
            "proof": {
                "rayReviewCards": [],
                "offers": [],
                "researchCandidates": [],
            },
            "blockers": [],
            "runningSafely": True,
            "moneyActions": [],
            "approvalsNeeded": [],
            "reportCount": 0,
            "loadedAt": datetime.utcnow().isoformat() + "Z",
        }

    return {
        "proof": {
            "rayReviewCards": _extract_ray_review_cards(reports),
            "offers": _extract_offers(reports),
            "researchCandidates": _extract_research_candidates(reports),
        },
        "blockers": _extract_blockers(reports),
        "runningSafely": _check_running_safely(reports),
        "moneyActions": _extract_money_actions(reports),
        "approvalsNeeded": _extract_approvals_needed(reports),
        "reportCount": len(reports),
        "loadedAt": datetime.utcnow().isoformat() + "Z",
    }


def main():
    parser = argparse.ArgumentParser(description="Load Hermes context")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    try:
        result = load_context()
    except Exception as e:
        result = {
            "proof": {"rayReviewCards": [], "offers": [], "researchCandidates": []},
            "blockers": [],
            "runningSafely": True,
            "moneyActions": [],
            "approvalsNeeded": [],
            "reportCount": 0,
            "error": str(e),
            "loadedAt": datetime.utcnow().isoformat() + "Z",
        }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Reports loaded: {result['reportCount']}")
        print(f"Running safely: {result['runningSafely']}")
        print(f"Blockers: {len(result['blockers'])}")
        print(f"Approvals needed: {len(result['approvalsNeeded'])}")
        print(f"Ray review cards: {len(result['proof']['rayReviewCards'])}")


if __name__ == "__main__":
    main()
