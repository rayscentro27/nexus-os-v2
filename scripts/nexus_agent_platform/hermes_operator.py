"""Natural-language Hermes control-plane resolution over canonical evidence."""
from __future__ import annotations

import re
from typing import Any, Dict

from nexus_agent_platform.capability_broker import discover, run_capability
from nexus_agent_platform.process_broker import read_processes

ROUTES = (
    (re.compile(r"\b(system health|health audit|system status)\b", re.I), "system.health"),
    (re.compile(r"\b(proof watchdog|check the proof|proof audit)\b", re.I), "proof.watchdog"),
    (re.compile(r"\b(frontend build|run the build|build the frontend)\b", re.I), "frontend.build"),
    (re.compile(r"\b(run the tests|run tests|test suite)\b", re.I), "tests.run"),
    (re.compile(r"\b(forex research|forex)\b", re.I), "forex.research"),
    (re.compile(r"\b(alpha|research)\b", re.I), "research.alpha"),
    (re.compile(r"\b(creative critic|creative intelligence)\b", re.I), "creative.intelligence"),
    (re.compile(r"\b(visual critic|visual design)\b", re.I), "visual.critic"),
    (re.compile(r"\b(model control|models)\b", re.I), "model.router"),
)


def resolve(text: str) -> str | None:
    for pattern, capability_id in ROUTES:
        if pattern.search(text):
            return capability_id
    return None


def operate(text: str, *, execute: bool = False, args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    lower = text.lower()
    if re.search(r"\b(show|list|what)\b.*\b(tools|capabilities)\b", lower):
        return {"status": "PASS", "intent": "discover", "evidence": discover()}
    if re.search(r"\b(processes|what is running|active jobs)\b", lower):
        return {"status": "PASS", "intent": "process_status", "evidence": read_processes()}
    capability_id = resolve(text)
    if not capability_id:
        return {"status": "UNKNOWN", "intent": "unsupported", "message": "I cannot resolve that to a registered Nexus capability."}
    if not execute:
        return {"status": "REGISTERED", "intent": "resolve", "capability_id": capability_id, "evidence": discover()}
    receipt = run_capability(capability_id, args or {})
    return {"status": receipt["status"], "intent": "execute", "capability_id": capability_id, "receipt": receipt}
