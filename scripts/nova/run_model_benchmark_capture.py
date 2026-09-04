"""Run the frozen R1.5 dataset through a provider with safe capture.

Benchmark utility only; it does not modify Nova production configuration.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from model_benchmark_capture import normalize_response, serialize_result


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
            payload = json.dumps({"model": args.model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": case["question"]}], "temperature": 0.2, "max_tokens": 220}).encode()
            started = time.time()
            status = None
            content_type = None
            completed = subprocess.run(
                ["curl", "-sS", "--max-time", "60", "-D", "-", "-H", f"Authorization: Bearer {key}", "-H", "Content-Type: application/json", "-d", payload.decode(), "https://openrouter.ai/api/v1/chat/completions"],
                capture_output=True,
                check=False,
            )
            header_blob, _, raw = completed.stdout.partition(b"\r\n\r\n")
            if not raw:
                header_blob, _, raw = completed.stdout.partition(b"\n\n")
            status_match = __import__("re").search(rb"HTTP/[^ ]+ (\d+)", header_blob)
            status = int(status_match.group(1)) if status_match else None
            content_type_match = __import__("re").search(rb"(?im)^content-type:\s*([^\r\n]+)", header_blob)
            content_type = content_type_match.group(1).decode("ascii", errors="replace") if content_type_match else None
            if completed.returncode != 0:
                raw = json.dumps({"transport_error": True, "curl_exit": completed.returncode}).encode()
                status = None
                content_type = "application/json"
            result = normalize_response(benchmark_case_id=case["id"], provider="openrouter", requested_model=args.model, raw=raw, http_status=status, content_type=content_type, started_at=str(started), completed_at=str(time.time()))
            if completed.returncode != 0:
                result["capture_status"] = "HTTP_TRANSPORT_FAILURE"
                result["provider_error"] = None
            result["class"] = case["class"]
            result["latency_ms"] = round((time.time() - started) * 1000, 1)
            handle.write(serialize_result(result) + "\n")
            handle.flush()
    print(json.dumps({"model": args.model, "cases": len(cases), "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
