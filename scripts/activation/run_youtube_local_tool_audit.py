#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from youtube_local_tool import audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = audit()
    print(json.dumps(report, indent=2) if args.json else report["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
