"""Read-only existing-knowledge reconciliation adapter."""
from __future__ import annotations

from typing import Any


class KnowledgeAdapter:
    def __init__(self, lookup: Any = None):
        self.lookup = lookup

    def reconcile(self, subject: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        if self.lookup is None:
            return {"relationship": "NEW", "prior_knowledge": [], "material_changes": [],
                    "lookup_status": "UNAVAILABLE"}
        try:
            prior = self.lookup(subject) or []
            relationship = "RELATED" if prior else "NEW"
            comparison = {}
            if prior:
                try:
                    from research.research_v2 import compare_knowledge
                    comparison = compare_knowledge(new_item={"title": subject,
                        "evidence": evidence}, prior_items=prior)
                    relationship = str(comparison.get("relationship") or relationship).upper()
                except Exception:
                    # A compatibility adapter can return prior context even if
                    # the optional legacy comparator is unavailable.
                    comparison = {}
            return {"relationship": relationship, "prior_knowledge": prior,
                    "material_changes": comparison.get("material_changes") or
                        (["Current evidence compared with prior knowledge."] if prior else []),
                    "comparison": comparison, "lookup_status": "AVAILABLE"}
        except Exception as exc:
            return {"relationship": "NEW", "prior_knowledge": [], "material_changes": [],
                    "lookup_status": "UNAVAILABLE", "error": f"{type(exc).__name__}: {exc}"}
