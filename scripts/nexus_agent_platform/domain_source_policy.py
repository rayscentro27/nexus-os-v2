"""Domain-aware source selection for Nova.

Classification is advisory metadata. It never grants a capability; the shared
capability layer and TruthKernel still enforce reads, writes, and authority.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


DOMAIN_SOURCE_POLICY: Dict[str, Dict[str, Any]] = {
    "NEXUS_OPERATIONS": {"primary": ["TruthKernel", "runtime", "heartbeat", "receipts"], "secondary": ["current reports"], "invalid_default": ["public web"]},
    "CLIENT_DATA": {"primary": ["authoritative Supabase business records"], "secondary": ["current client artifacts"], "invalid_default": ["process registry"]},
    "INTERNAL_RESEARCH_ALPHA": {"primary": ["Alpha artifacts", "research ledger", "completed reports"], "secondary": ["research heartbeat"], "invalid_default": ["generic Nexus health"]},
    "PUBLIC_BUSINESS_RESEARCH": {"primary": ["public web", "primary sources", "independent evidence"], "secondary": ["Alpha"], "invalid_default": ["Nexus runtime"]},
    "PUBLIC_COMPANY_RESEARCH": {"primary": ["company materials", "independent public reporting"], "secondary": ["Alpha"], "invalid_default": ["Nexus runtime"]},
    "WEBSITE_ANALYSIS": {"primary": ["provided website", "independent public sources"], "secondary": ["Alpha"], "invalid_default": ["Nexus runtime"]},
    "GENERAL_KNOWLEDGE": {"primary": ["Nova model knowledge"], "secondary": ["current public sources when needed"], "invalid_default": ["Nexus runtime"]},
    "GENERAL_BUSINESS": {"primary": ["Nova reasoning", "public business sources when current"], "secondary": ["Alpha"], "invalid_default": ["Nexus runtime"]},
    "FINANCIAL_ECONOMICS": {"primary": ["current market/public evidence", "explicit assumptions"], "secondary": ["Alpha"], "invalid_default": ["unverified company counters"]},
    "INTERNAL_COMPANY_BUSINESS": {"primary": ["Supabase/company records", "current reports"], "secondary": ["public research", "Alpha"], "invalid_default": ["stale daily brief alone"]},
    "DELEGATION_REQUEST": {"primary": ["Nexus or Alpha governed intake"], "secondary": [], "invalid_default": ["direct execution by Nova"]},
    "OPERATIONAL_ACTION": {"primary": ["Nexus authority path"], "secondary": ["TruthKernel approval ledger"], "invalid_default": ["Nova direct mutation"]},
}


def classify_domain(text: str) -> List[str]:
    """Return ordered domains using meaning cues, allowing multi-domain work."""
    lower = re.sub(r"\s+", " ", (text or "").lower()).strip()
    domains: List[str] = []
    def add(domain: str) -> None:
        if domain not in domains:
            domains.append(domain)
    if any(x in lower for x in ("send", "submit", "delegate", "have nexus", "pass that")):
        add("DELEGATION_REQUEST")
    if any(x in lower for x in ("approve", "execute", "restart", "change", "run this")):
        add("OPERATIONAL_ACTION")
    if any(x in lower for x in ("active operator", "nexus", "truthkernel", "system health", "runtime", "service")):
        add("NEXUS_OPERATIONS")
    if any(x in lower for x in ("client", "onboarding", "customer", "supabase")):
        add("CLIENT_DATA")
    if any(x in lower for x in ("research found", "research find", "what did research", "alpha", "research artifact", "research report")):
        add("INTERNAL_RESEARCH_ALPHA")
    if any(x in lower for x in ("focus on today", "what should we focus", "company priorities", "what matters today")):
        add("INTERNAL_COMPANY_BUSINESS")
    if any(x in lower for x in ("website", "site", "company online", "what this company does")):
        add("WEBSITE_ANALYSIS")
    if any(x in lower for x in ("youtube", "affiliate", "make $", "make money", "market", "competitor", "agency")):
        add("PUBLIC_BUSINESS_RESEARCH")
    if any(x in lower for x in ("tesla", "company strategy", "stock", "industry")):
        add("PUBLIC_COMPANY_RESEARCH")
    if any(x in lower for x in ("profit", "revenue", "cost", "economics", "$")):
        add("FINANCIAL_ECONOMICS")
    if any(x in lower for x in ("llc", "what is", "how do", "benefits of")):
        add("GENERAL_KNOWLEDGE")
    if not domains:
        add("GENERAL_KNOWLEDGE")
    return domains


def source_plan(text: str) -> Dict[str, Any]:
    domains = classify_domain(text)
    return {"domains": domains, "sources": [DOMAIN_SOURCE_POLICY[d] for d in domains], "nexus_relevant": "NEXUS_OPERATIONS" in domains or "CLIENT_DATA" in domains or "INTERNAL_COMPANY_BUSINESS" in domains}
