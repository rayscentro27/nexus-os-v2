#!/usr/bin/env python3
"""Deterministic research scoring helpers for CLI use."""
from __future__ import annotations

import argparse
import json

from common import score_research_text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default="")
    parser.add_argument("--topic", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    print(json.dumps({"ok": True, "scores": score_research_text(args.text, args.topic)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
