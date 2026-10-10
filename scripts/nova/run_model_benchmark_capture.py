"""Run the frozen R1.5 dataset through a provider with safe capture.

Benchmark utility only; it does not modify Nova production configuration.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from model_benchmark_capture import normalize_response, serialize_result
from alpha.alpha_live_research import http_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--dataset", default="reports/rebuild/NEXUS_HERMES_NOVA_MODEL_BENCHMARK_R1_5_DATASET.json")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is not set")
    dataset = json.loads(Path(args.dataset).read_text())
    system = ("You are Hermes Nova, Ray Davis's executive interface to Nexus. "
              "Nexus is an autonomous operating-company system with Research, Alpha, "
              "specialized departments, GoClear, Trading, durable objectives, and "
              "future program-level execution. Use durable context, distinguish current "
              "state from durable context, do not invent live facts, and make proportional recommendations.")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    cases = dataset["turns"][args.offset:args.offset + args.limit if args.limit is not None else None]
    with output.open("w", encoding="utf-8") as handle:
        for case in cases:
            payload = {"model": args.model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": case["question"]}], "temperature": 0.2, "max_tokens": 220}
            started = time.time()
            ok, status, data, error, _latency = http_json(
                "POST", "https://openrouter.ai/api/v1/chat/completions",
                {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                payload, timeout=60,
            )
            raw = json.dumps(data or ({"error": error} if error else {})).encode()
            content_type = "application/json"
            if not ok:
                status = None
            result = normalize_response(benchmark_case_id=case["id"], provider="openrouter", requested_model=args.model, raw=raw, http_status=status, content_type=content_type, started_at=str(started), completed_at=str(time.time()))
            if not ok:
                result["capture_status"] = "GOVERNOR_DENIED" if str(error or "").startswith("GOVERNOR_DENIED") else "HTTP_TRANSPORT_FAILURE"
                result["provider_error"] = None
            result["class"] = case["class"]
            result["latency_ms"] = round((time.time() - started) * 1000, 1)
            handle.write(serialize_result(result) + "\n")
            handle.flush()
    print(json.dumps({"model": args.model, "cases": len(cases), "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
