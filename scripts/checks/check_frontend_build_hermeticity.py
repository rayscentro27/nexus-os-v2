#!/usr/bin/env python3
"""Reject frontend imports that depend on mutable or private local state."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = (
    "data/runtime/",
    "data/private/",
    "data/governed/",
    "reports/runtime/",
    "receipts/",
    "secrets/",
    "tools/voice/runtime/",
    "tools/voice/audio/",
)
IMPORT_RE = re.compile(r"(?:from|import\s*\(|require\s*\()[\s]*['\"]([^'\"]+)['\"]")


def source_files(root: Path) -> list[Path]:
    files = [*root.joinpath("src").rglob("*")]
    files.extend(root.glob("index.html"))
    files.extend(root.glob("vite.config.*"))
    text_suffixes = {".css", ".html", ".js", ".jsx", ".ts", ".tsx", ".json", ".mjs", ".cjs"}
    return sorted(path for path in files if path.is_file() and path.suffix in text_suffixes)


def scan(root: Path = ROOT) -> dict[str, object]:
    findings: list[dict[str, str]] = []
    imports = 0
    for path in source_files(root):
        text = path.read_text(encoding="utf-8")
        for match in IMPORT_RE.finditer(text):
            imports += 1
            specifier = match.group(1)
            matched = next((prefix for prefix in FORBIDDEN if prefix in specifier), None)
            if matched:
                findings.append({"file": str(path.relative_to(root)), "specifier": specifier, "rule": matched})
    return {"status": "PASS" if not findings else "FAIL", "imports_scanned": imports, "forbidden": findings}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    result = scan()
    if args.as_json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"frontend_build_hermeticity={result['status']}")
        for finding in result["forbidden"]:
            print(f"FORBIDDEN_IMPORT {finding['file']} -> {finding['specifier']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
