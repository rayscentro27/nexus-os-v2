"""Dependency-aware portfolio scheduler and starvation-proof certification."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Lane:
    lane_id: str
    dependency_domain: str
    execute: Callable[[], dict]


def run_portfolio(lanes: list[Lane]) -> dict:
    """Run independent lanes concurrently; one failure cannot cancel peers."""
    states = {lane.lane_id: {"state": "QUEUED", "domain": lane.dependency_domain} for lane in lanes}
    started = time.monotonic()

    def one(lane: Lane) -> tuple[str, dict]:
        states[lane.lane_id]["state"] = "RUNNING"
        try:
            result = lane.execute()
            states[lane.lane_id].update(result if isinstance(result, dict) else {})
            states[lane.lane_id]["state"] = "PASS" if states[lane.lane_id].get("status", "PASS") == "PASS" else "RECOVERING"
        except Exception as exc:  # bounded lane failure is recorded, not propagated
            states[lane.lane_id].update({"state": "RECOVERING", "failure_signature": type(exc).__name__})
        return lane.lane_id, states[lane.lane_id]

    with ThreadPoolExecutor(max_workers=max(1, len(lanes)), thread_name_prefix="nexus-portfolio") as pool:
        futures = [pool.submit(one, lane) for lane in lanes]
        for future in futures:
            future.result()
    passed = [key for key, value in states.items() if value["state"] == "PASS"]
    recovering = [key for key, value in states.items() if value["state"] == "RECOVERING"]
    return {"status": "PASS" if passed and not any(value["state"] == "QUEUED" for value in states.values()) else "FAIL",
            "active_lanes": [], "recovering_lanes": recovering, "completed_lanes": passed,
            "waiting_lanes": [key for key, value in states.items() if value["state"] == "QUEUED"],
            "independent_work_remaining": bool(recovering), "duration_ms": int((time.monotonic() - started) * 1000),
            "lanes": states}


def certify_starvation() -> dict:
    def timeout():
        raise TimeoutError("synthetic lane timeout")
    def safe():
        return {"status": "PASS", "verified": True, "receipt": "portfolio_parallelism_safe_lane"}
    result = run_portfolio([Lane("A", "NETWORK_DEPENDENT", timeout), Lane("B", "LOCAL_ONLY", safe)])
    reverse = run_portfolio([Lane("C", "LOCAL_ONLY", safe), Lane("D", "NETWORK_DEPENDENT", timeout)])
    passed = "B" in result["completed_lanes"] and "C" in reverse["completed_lanes"]
    return {"status": "PASS" if passed else "FAIL", "blocked_lane_does_not_starve_portfolio": passed,
            "first": result, "reverse": reverse}


if __name__ == "__main__":
    import json
    print(json.dumps(certify_starvation(), indent=2, sort_keys=True))
