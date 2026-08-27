"""Bounded allowlist executor for after-action improvement proposals."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_PREFIXES = (ROOT / "scripts/nexus_agent_platform", ROOT / "scripts/trading", ROOT / "configs")
FORBIDDEN = {"secret", "credential", "billing", "live_trading", "oauth", "deploy", "external_message"}

@dataclass
class ImprovementDecision:
    status: str
    reason: str
    files: list[str]

def evaluate(proposal: dict[str, Any], files: list[str]) -> ImprovementDecision:
    text = str(proposal).lower().replace(" ", "_")
    paths = [Path(x).resolve() for x in files]
    if any(any(word in text for word in FORBIDDEN) for _ in [0]):
        return ImprovementDecision("IMPROVEMENT_REJECTED_BY_POLICY", "proposal touches a prohibited authority", files)
    if not files or len(files) > 3 or any(not any(p == root or root in p.parents for root in ALLOWED_PREFIXES) for p in paths):
        return ImprovementDecision("IMPROVEMENT_REJECTED_BY_POLICY", "target is outside bounded allowlist", files)
    return ImprovementDecision("IMPROVEMENT_PROPOSED", "eligible only for explicit safe transaction", files)

def apply_safe(proposal: dict[str, Any], *, target: str, old_text: str, new_text: str, test_command: list[str]) -> dict[str, Any]:
    """Apply one exact, reversible replacement and reject failing postconditions."""
    decision = evaluate(proposal, [target]); path = Path(target).resolve()
    if decision.status != "IMPROVEMENT_PROPOSED": return {"status": decision.status, "reason": decision.reason, "applied": False}
    if path not in [p.resolve() for root in ALLOWED_PREFIXES for p in [path] if root == p or root in p.parents]:
        return {"status":"IMPROVEMENT_REJECTED_BY_POLICY","reason":"target outside allowlist","applied":False}
    before = path.read_text(encoding="utf-8")
    if old_text not in before or before.count(old_text) != 1:
        return {"status":"IMPROVEMENT_REJECTED_BY_POLICY","reason":"exact precondition not met","applied":False}
    path.write_text(before.replace(old_text, new_text, 1), encoding="utf-8")
    test = subprocess.run(test_command, cwd=ROOT, capture_output=True, text=True, timeout=120, check=False)
    if test.returncode != 0:
        path.write_text(before, encoding="utf-8")
        return {"status":"IMPROVEMENT_REJECTED_BY_TESTS","applied":False,"rollback":"exact original restored","test_returncode":test.returncode}
    return {"status":"IMPROVEMENT_APPLIED","applied":True,"files_modified":[str(path)],"test_returncode":0,"postcondition":new_text in path.read_text(encoding="utf-8"),"rollback":"restore recorded original text"}
