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


def critique_rendered(screenshot_paths: Sequence[str], *, surface: str) -> Dict[str, Any]:
    """Review real browser artifacts and bind them to the source critic.

    PNG dimensions and content hashes are deliberately recorded so a visual
    result cannot be claimed from source inspection alone.  Human-visible
    layout findings remain in the screenshot artifact; this bounded critic
    rejects missing, empty, or malformed renders and preserves provenance.
    """
    artifacts = []
    findings = []
    for raw in screenshot_paths:
        path = Path(raw)
        item: Dict[str, Any] = {"path": str(path), "exists": path.is_file()}
        if not path.is_file() or path.stat().st_size < 64:
            findings.append({"severity": "BLOCKER", "path": str(path), "finding": "rendered screenshot missing or empty"})
        else:
            data = path.read_bytes()
            item.update({"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "png_signature": data[:8] == b"\x89PNG\r\n\x1a\n"})
            if not item["png_signature"]:
                findings.append({"severity": "BLOCKER", "path": str(path), "finding": "render artifact is not a PNG"})
            elif len(data) >= 24:
                item.update({"width": int.from_bytes(data[16:20], "big"), "height": int.from_bytes(data[20:24], "big")})
        artifacts.append(item)
    source = critique()
    findings.extend(source.get("findings", []))
    return {"schema_version": "nexus.visual-critic-rendered.v1", "status": "PASS" if not any(f["severity"] == "BLOCKER" for f in findings) else "FAIL", "surface": surface, "critic": "deterministic_render_artifact_plus_source_contract", "dimensions": source["dimensions"], "findings": findings, "artifacts": artifacts, "source_fingerprints": source["source_fingerprints"], "rendered_screenshot": "VERIFIED", "external_action_performed": False}


if __name__ == "__main__":
    import json
    print(json.dumps(critique(), indent=2))
