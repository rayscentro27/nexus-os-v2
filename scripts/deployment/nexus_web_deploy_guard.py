#!/usr/bin/env python3
"""Enforce the canonical Git-connected cloud deployment boundary."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def gate_legacy_netlify_cli() -> int:
    override = os.environ.get("NEXUS_ALLOW_LEGACY_NETLIFY_CLI_DEPLOY", "NO").upper()
    reason = os.environ.get("NEXUS_LEGACY_NETLIFY_DEPLOY_REASON", "").strip()
    receipt = os.environ.get("NEXUS_LEGACY_NETLIFY_DEPLOY_RECEIPT", "").strip()
    if override != "YES":
        print("BLOCKED: direct Netlify CLI deployment is disabled; push Git and use the connected cloud build.", file=sys.stderr)
        return 2
    if not reason or not receipt:
        print("BLOCKED: emergency Netlify CLI deployment requires reason and receipt path.", file=sys.stderr)
        return 2
    if not Path(receipt).parent.exists():
        print("BLOCKED: emergency deployment receipt parent does not exist.", file=sys.stderr)
        return 2
    print("ALLOWED: emergency legacy Netlify CLI path explicitly authorized; provider execution remains caller-owned.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("legacy-netlify-cli",))
    args = parser.parse_args()
    if args.command == "legacy-netlify-cli":
        return gate_legacy_netlify_cli()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
