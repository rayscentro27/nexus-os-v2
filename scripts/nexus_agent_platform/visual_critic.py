"""Deterministic Visual Critic for source-level design acceptance.

This is a bounded pre-render critic. It checks the implementation contract
before browser screenshots are accepted; it never claims that source checks
replace rendered visual evidence.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Sequence

ROOT = Path(__file__).resolve().parents[2]


def critique(paths: Sequence[str] = ("src/admin/NexusExperienceAdmin.jsx", "src/admin/nexusExperience2.css")) -> Dict[str, Any]:
    findings = []
    fingerprints = {}
    for relative in paths:
        path = ROOT / relative
        if not path.is_file():
            findings.append({"severity": "BLOCKER", "path": relative, "finding": "implementation file is missing"})
            continue
        content = path.read_text(encoding="utf-8")
        fingerprints[relative] = hashlib.sha256(content.encode()).hexdigest()
        if relative.endswith(".jsx") and "aria-" not in content:
            findings.append({"severity": "MAJOR", "path": relative, "finding": "no ARIA attributes found in the reviewed surface"})
        if relative.endswith(".css") and "@media" not in content:
            findings.append({"severity": "MAJOR", "path": relative, "finding": "responsive media rule is absent"})
        if relative.endswith(".css") and ":focus" not in content:
            findings.append({"severity": "MAJOR", "path": relative, "finding": "keyboard focus styling is absent"})
    return {
        "schema_version": "nexus.visual-critic.v1",
        "status": "PASS" if not any(item["severity"] == "BLOCKER" for item in findings) else "FAIL",
        "critic": "deterministic_source_contract",
        "dimensions": ["hierarchy", "layout", "spacing", "typography", "contrast", "responsive", "accessibility", "consistency", "interaction"],
        "findings": findings,
        "source_fingerprints": fingerprints,
        "rendered_screenshot": "REQUIRED_FOR_FINAL_ACCEPTANCE",
        "external_action_performed": False,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(critique(), indent=2))
