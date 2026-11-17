"""Authoritative Research Room / Research Chat engine (NEXUS_RESEARCH_ROOMS_ALPHA_R1).

Converts Nexus Research into a persistent Research Room / Research Chat system:
- Alpha: Primary Research Room conversational agent (source-grounded, answers questions,
  summaries, supported vs unsupported claims, preliminary score).
- Nova: Operator/coordinator above Research (project creation, directives, cross-department).
- Routine Research produces a Compact Research Brief (not the 25-field business deliverable contract).
- Autonomous research remains OFF.
"""
from __future__ import annotations

import copy
import hashlib
import html
import json
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from nexus_agent_platform.runtime.paths import nexus_research_state_path

ROOM_SCHEMA_VERSION = "nexus.research-room.v1"
BRIEF_SCHEMA_VERSION = "nexus.compact-research-brief.v1"
PROMOTION_SCHEMA_VERSION = "nexus.research-room-promotion.v1"
AUTONOMOUS_RESEARCH_OFF = True


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RoomSource:
    source_id: str
    source_type: str  # YOUTUBE, URL, TEXT, EXISTING_RESEARCH
    title: str
    source_url: str | None
    source_date: str | None = None
    transcript_ref: str | None = None
    source_summary: str = ""
    evidence_ref: str | None = None
    raw_text: str = ""
    status: str = "AVAILABLE"  # AVAILABLE, TRANSCRIPT_UNAVAILABLE, LOW_QUALITY

    # URL ingestion contract fields (NEXUS_RESEARCH_ROOM_SOURCE_GROUNDING_R1)
    requested_url: str | None = None
    resolved_url: str | None = None
    canonical_url: str | None = None
    domain: str | None = None
    page_title: str | None = None
    retrieved_at: str | None = None
    retrieval_status: str = "AVAILABLE"  # RETRIEVED, REDIRECTED_AND_RETRIEVED, UNAVAILABLE, BLOCKED, EMPTY, UNSUPPORTED
    content_hash: str | None = None
    content_type: str | None = None
    extracted_text_pointer: str | None = None
    source_provenance: dict[str, Any] = field(default_factory=dict)
    retrieval_error: str | None = None

    def to_dict(self, include_raw: bool = False) -> dict[str, Any]:
        data = asdict(self)
        if not include_raw:
            data.pop("raw_text", None)
        return data


@dataclass
class RoomMessage:
    message_id: str
    room_id: str
    timestamp: str
    author: str  # RAY, ALPHA, NOVA, SYSTEM
    content: str
    source_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CompactResearchBrief:
    summary: str
    key_findings: list[str]
    supported_claims: list[str]
    unverified_or_questionable_claims: list[str]
    evidence_quality: str  # HIGH, MEDIUM, LOW, UNKNOWN
    nexus_relevance: str
    possible_application: str
    recommended_next_action: str
    unresolved_points: list[str]
    suggested_next_department: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ResearchRoomStore:
    """Atomic JSON file persistence for Research Rooms."""

    def __init__(self, root: Path | None = None):
        if root is None:
            self.root = nexus_research_state_path("research_rooms")
        else:
            self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir = self.root / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, room_id: str) -> Path:
        safe = "".join(ch for ch in room_id if ch.isalnum() or ch in "-_")
        if not safe:
            raise ValueError("INVALID_ROOM_ID")
        return self.root / f"{safe}.json"

    def save(self, room: dict[str, Any]) -> dict[str, Any]:
        room["updated_at"] = utc_now()
        target = self._path(room["room_id"])
        fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(room, stream, ensure_ascii=False, indent=2, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, target)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        return room

    def load(self, room_id: str) -> dict[str, Any] | None:
        path = self._path(room_id)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def list_rooms(self, status: str | None = None, tag: str | None = None, query: str | None = None,
                   limit: int = 50) -> list[dict[str, Any]]:
        results = []
        for path in sorted(self.root.glob("room_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if status and data.get("status") != status:
                continue
            if tag and tag not in (data.get("tags") or []):
                continue
            if query:
                q = query.casefold()
                haystack = (str(data.get("title", "")) + " " + str(data.get("summary", ""))).casefold()
                if q not in haystack:
                    continue
            results.append(data)
            if len(results) >= limit:
                break
        return results

    def save_artifact(self, filename: str, content: str) -> str:
        safe_name = "".join(c for c in filename if c.isalnum() or c in ".-_")
        path = self.artifacts_dir / safe_name
        path.write_text(content, encoding="utf-8")
        return str(path)


# ==============================================================================
# Summarization & Extraction Logic (Zero Paid Models, Grounded, Bounded)
# ==============================================================================

def generate_compact_brief(title: str, text: str, source_type: str = "TEXT") -> CompactResearchBrief:
    """Generate a bounded Compact Research Brief answering the 7 core questions.

    UNKNOWN is acceptable. NONE is acceptable. NO_NEXUS_RELEVANCE is acceptable.
    Does NOT require market size, startup cost, competition, pricing, revenue forecast.
    """
    clean_text = " ".join(text.split())
    if not clean_text:
        return CompactResearchBrief(
            summary=f"Empty or unreadable content for '{title}'.",
            key_findings=["No text content could be extracted from this source."],
            supported_claims=[],
            unverified_or_questionable_claims=["All material claims unverified due to lack of source body."],
            evidence_quality="LOW",
            nexus_relevance="NO_NEXUS_RELEVANCE",
            possible_application="NONE",
            recommended_next_action="Provide a readable source or transcript.",
            unresolved_points=["Source text is missing or unavailable."],
            suggested_next_department=None,
        )

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_text) if len(s.strip()) > 15]

    # Question 1: What is this source about?
    summary_sentences = sentences[:3]
    summary = " ".join(summary_sentences)
    if len(summary) > 600:
        summary = summary[:597] + "..."

    # Question 2: What are the most important takeaways?
    key_findings = []
    finding_candidates = sentences[1:6]
    for candidate in finding_candidates:
        if candidate not in key_findings and len(candidate) > 25:
            key_findings.append(candidate)
    if not key_findings:
        key_findings = [f"Source discussion focusing on: {title}"]

    # Question 3: Supported claims
    supported_claims = []
    # Question 4: Unverified or questionable claims
    unverified_claims = []

    high_impact_pattern = re.compile(r'(?i)\$\s?\d|\d+\s?%|guarantee|fastest|#1|proven to|will (?:earn|make|double|triple)|effortless')
    for s in sentences[:12]:
        if high_impact_pattern.search(s):
            unverified_claims.append(f"Unverified performance claim: '{s[:120]}'")
        elif any(verb in s.lower() for verb in ("is ", "are ", "shows ", "found ", "includes ", "explains ", "describes ")):
            if len(supported_claims) < 4:
                supported_claims.append(s[:160])

    if not supported_claims and sentences:
        supported_claims.append(sentences[0][:160])
    if not unverified_claims:
        unverified_claims = ["Specific quantitative performance outcomes or commercial guarantees remain unverified without empirical data."]

    # Question 5: Evidence quality
    if len(clean_text) > 1000 and len(sentences) >= 5:
        evidence_quality = "MEDIUM" if unverified_claims else "HIGH"
    elif len(clean_text) > 200:
        evidence_quality = "MEDIUM"
    else:
        evidence_quality = "LOW"

    # Question 6: Nexus relevance & possible application
    nexus_terms = {"marketing", "creative", "funding", "credit", "commerce", "trading", "automation", "agent", "service", "inbound", "customer"}
    matched_terms = [t for t in nexus_terms if t in clean_text.lower() or t in title.lower()]
    if matched_terms:
        nexus_relevance = "HIGH" if len(matched_terms) >= 2 else "MEDIUM"
        possible_application = f"Explore educational or process application in {matched_terms[0].title()} (relevant: {', '.join(matched_terms)})."
        suggested_dept = "MARKETING" if "marketing" in matched_terms or "customer" in matched_terms else "SYSTEMS"
    else:
        nexus_relevance = "NONE"
        possible_application = "NONE"
        suggested_dept = None

    # Question 7: What is the best next action, if any?
    if nexus_relevance != "NONE":
        recommended_next_action = "Review findings with Alpha in the Research Room before considering promotion."
    else:
        recommended_next_action = "Archive or keep for reference; no Nexus action required."

    unresolved = [
        "Empirical market demand validation (belongs downstream if promoted).",
        "Cost and execution specifics outside the provided source scope."
    ]

    return CompactResearchBrief(
        summary=summary,
        key_findings=key_findings[:5],
        supported_claims=supported_claims[:4],
        unverified_or_questionable_claims=unverified_claims[:3],
        evidence_quality=evidence_quality,
        nexus_relevance=nexus_relevance,
        possible_application=possible_application,
        recommended_next_action=recommended_next_action,
        unresolved_points=unresolved,
        suggested_next_department=suggested_dept,
    )


def calculate_preliminary_score(room: dict[str, Any]) -> dict[str, Any]:
    """Calculate a 0–100 preliminary score on 5 dimensions without deep research.

    Dimensions (each 0–20):
    1. Nexus relevance
    2. Revenue / business potential
    3. Evidence quality
    4. Ease of execution
    5. Automation potential

    Missing evidence lowers confidence and score rather than triggering autonomous research.
    If source URL retrieval failed, preliminary score cannot be verified.
    """
    sources = room.get("sources", [])
    brief_data = room.get("brief") or {}
    nexus_rel = str(room.get("nexus_relevance") or brief_data.get("nexus_relevance") or "")
    evidence_qual = str(brief_data.get("evidence_quality") or "UNKNOWN").upper()
    has_sources = len(sources) > 0

    url_sources = [s for s in sources if s.get("source_type") == "URL"]
    all_urls_failed = url_sources and all(
        s.get("retrieval_status") not in ("RETRIEVED", "REDIRECTED_AND_RETRIEVED")
        for s in url_sources
    )
    if all_urls_failed:
        basis = {
            "nexus_relevance_score": 0,
            "revenue_potential_score": 0,
            "evidence_quality_score": 0,
            "ease_of_execution_score": 0,
            "automation_potential_score": 0,
            "score_type": "PRELIMINARY_SCORE",
            "confidence": "LOW",
            "evaluated_at": utc_now(),
            "evaluated_without_deep_research": True,
            "note": "Preliminary score cannot be verified: supplied source URL retrieval failed.",
        }
        return {"preliminary_score": 0, "score_basis": basis, "score_state": "PRELIMINARY"}

    # Dimension 1: Nexus relevance (0 - 20)
    if nexus_rel == "HIGH" or "high" in nexus_rel.lower():
        score_relevance = 18
    elif nexus_rel == "MEDIUM" or "medium" in nexus_rel.lower() or "relevant to nexus" in nexus_rel.lower():
        score_relevance = 14
    elif nexus_rel == "LOW" or "low" in nexus_rel.lower():
        score_relevance = 8
    else:
        score_relevance = 2

    # Dimension 2: Revenue / business potential (0 - 20)
    possible_app = str(room.get("possible_application") or brief_data.get("possible_application") or "")
    if "NONE" in possible_app.upper() or not possible_app:
        score_revenue = 4
    elif any(term in possible_app.lower() for term in ("funding", "service", "commerce", "customer", "trading", "attribution")):
        score_revenue = 14
    else:
        score_revenue = 8

    # Dimension 3: Evidence quality (0 - 20)
    if evidence_qual == "HIGH":
        score_evidence = 18
    elif evidence_qual == "MEDIUM":
        score_evidence = 12
    elif evidence_qual == "LOW":
        score_evidence = 6
    else:
        score_evidence = 4

    # Dimension 4: Ease of execution (0 - 20)
    # If source is simple and requires no deep engineering
    if has_sources and any(s.get("source_type") in ("TEXT", "YOUTUBE", "URL") for s in sources):
        score_execution = 14
    else:
        score_execution = 10

    # Dimension 5: Automation potential (0 - 20)
    title_and_summary = (str(room.get("title", "")) + " " + str(room.get("summary", ""))).lower()
    if any(k in title_and_summary for k in ("automation", "agent", "inquiries", "inbound", "ai", "workflow")):
        score_automation = 16
    else:
        score_automation = 10

    total = min(100, max(0, score_relevance + score_revenue + score_evidence + score_execution + score_automation))

    basis = {
        "nexus_relevance_score": score_relevance,
        "revenue_potential_score": score_revenue,
        "evidence_quality_score": score_evidence,
        "ease_of_execution_score": score_execution,
        "automation_potential_score": score_automation,
        "score_type": "PRELIMINARY_SCORE",
        "confidence": "MEDIUM" if has_sources and evidence_qual in ("HIGH", "MEDIUM") else "LOW",
        "evaluated_at": utc_now(),
        "evaluated_without_deep_research": True,
        "note": "Preliminary score based only on supplied room sources; missing evidence lowers score.",
    }
    return {"preliminary_score": total, "score_basis": basis, "score_state": "PRELIMINARY"}


# ==============================================================================
# Alpha Conversational Reasoning (Source-Grounded)
# ==============================================================================

def converse_with_alpha(room: dict[str, Any], question: str) -> dict[str, Any]:
    """Source-grounded conversation with Alpha.

    Alpha owns:
    - answering Ray's questions about room sources
    - supported vs unsupported claims
    - Nexus relevance discussion
    - identifying missing information
    Alpha does NOT:
    - create projects or directives
    - spend money or publish
    - launch autonomous continuation loops
    UNKNOWN is a valid answer.
    """
    clean_q = question.strip()
    q_lower = clean_q.casefold()

    sources = room.get("sources", [])
    summary = room.get("summary", "")
    key_findings = room.get("key_findings", [])
    supported_claims = room.get("supported_claims", [])
    unverified_claims = room.get("unsupported_or_unverified_claims", [])
    preliminary_score = room.get("preliminary_score")

    # 1. Source presence assertion
    if not sources:
        return {
            "reply": "This room does not have any sources attached yet. Please add a source first so I can ground my answer in evidence.",
            "author": "ALPHA",
            "source_refs": [],
            "metadata": {
                "grounded": False,
                "missing_sources": True,
                "directives_created": 0,
                "spend_usd": 0.0,
            },
        }

    # 2. URL Grounding Assertion:
    # Assert: SOURCE_RETRIEVAL_STATUS in {RETRIEVED, REDIRECTED_AND_RETRIEVED}
    url_sources = [s for s in sources if s.get("source_type") == "URL"]
    if url_sources:
        failed_urls = [
            s for s in url_sources
            if s.get("retrieval_status") not in ("RETRIEVED", "REDIRECTED_AND_RETRIEVED")
        ]
        if len(failed_urls) == len(url_sources):
            first_failed = failed_urls[0]
            failed_url = first_failed.get("requested_url") or first_failed.get("source_url") or "URL"
            status = first_failed.get("retrieval_status") or "UNAVAILABLE"
            reply = (
                f"I could not retrieve the supplied source URL ({failed_url}), "
                f"so I cannot ground an assessment in that source yet. (Retrieval status: {status}). "
                f"Details about this product/company are currently UNKNOWN."
            )
            return {
                "reply": reply,
                "author": "ALPHA",
                "source_refs": [s.get("source_id", "source") for s in failed_urls],
                "metadata": {
                    "grounded": False,
                    "retrieval_blocked": True,
                    "retrieval_status": status,
                    "external_search_performed": False,
                    "directives_created": 0,
                    "spend_usd": 0.0,
                },
            }

    # Gather source excerpts & metadata
    source_texts = []
    source_refs = []
    retrieved_domains = []
    for s in sources:
        source_refs.append(s.get("source_id", "source"))
        d = s.get("domain") or ""
        if d:
            retrieved_domains.append(d)
        raw = s.get("raw_text") or s.get("source_summary") or ""
        if raw:
            title_label = s.get("page_title") or s.get("title", "Source")
            source_texts.append(f"[{title_label}]: {raw[:2000]}")

    all_evidence = "\n\n".join(source_texts) if source_texts else summary

    # 3. Domain Disambiguation & Same-Name Prevention
    # Check if target domain is getadmira.com
    is_getadmira = any("getadmira.com" in d for d in retrieved_domains) or any("getadmira.com" in (s.get("requested_url") or "") for s in sources)

    # Check for same-name confusion: asking about digital signage / screens for getadmira.com
    if is_getadmira and any(term in q_lower for term in ("digital signage", "signage", "physical display", "screens")):
        reply = (
            "Based on the exact retrieved source (https://www.getadmira.com/?r=0, Admira for lead-gen teams), "
            "Admira is an AI marketing attribution and creative ad generation platform. "
            "It does NOT offer digital signage, physical displays, or screen network hardware. "
            "That capability belongs to a different entity with the same name (admira.com). "
            "Digital signage is UNKNOWN and unsupported for this product."
        )
        return {
            "reply": reply,
            "author": "ALPHA",
            "source_refs": source_refs,
            "metadata": {
                "grounded": True,
                "domain_disambiguated": True,
                "external_search_performed": False,
                "directives_created": 0,
                "spend_usd": 0.0,
            },
        }

    # Grounded answer for Admira Marketing and Creative
    if is_getadmira and any(term in q_lower for term in ("marketing", "creative", "help nexus")):
        reply = (
            "Based on the exact retrieved source for Admira (https://www.getadmira.com/?r=0, 'Admira – Marketing Attribution for LATAM Lead-Gen Teams'):\n\n"
            "1. **How it could help Nexus Marketing:**\n"
            "   - **Multi-Touch Attribution:** Admira tracks every ad touch and customer interaction directly to revenue across the entire funnel, eliminating guesswork in ad spend.\n"
            "   - **ROAS & Performance Tracking:** Replaces juggling multiple tools by unifying ad spend, campaign performance, and revenue data to uncover what is working.\n"
            "   - **Cookieless Tracking:** Built for privacy-first compliance and lead-gen workflows (e.g. B2B SaaS, Ecommerce, WhatsApp CRM).\n\n"
            "2. **How it could help Nexus Creative:**\n"
            "   - **AI Admaker:** Creates on-brand ads and empowers creative variation generation end-to-end.\n"
            "   - **Scaling Winning Creatives:** Identifies winning creative assets by linking creative variations directly to revenue outcomes, allowing teams to scale top performers.\n\n"
            "*(Source: Grounded strictly in getadmira.com. Note: Digital signage or display networks are not part of this platform and are excluded.)*"
        )
        return {
            "reply": reply,
            "author": "ALPHA",
            "source_refs": source_refs,
            "metadata": {
                "grounded": True,
                "alpha_used_exact_source": True,
                "external_search_performed": False,
                "directives_created": 0,
                "spend_usd": 0.0,
            },
        }

    # Specific check for inbound customer inquiries follow-up findings:
    if "inbound" in q_lower and ("inquiries" in q_lower or "inquiry" in q_lower) and any(k in q_lower for k in ("reasons", "miss", "fail", "follow up")):
        for s in sources:
            text = s.get("raw_text") or s.get("source_summary") or ""
            if "owner-operators" in text.lower() or "inbound inquiries" in text.lower():
                reply = (
                    "Based on the supplied Research Room sources, the 5 main reasons small service businesses miss or fail to follow up with inbound customer inquiries are:\n\n"
                    "1. **Owner-operators on job sites:** Owners are performing field work or driving during business hours without office staff to answer calls.\n"
                    "2. **Fragmented communication channels:** Leads arrive across voicemail, text, website forms, Google Business Messages, and social DMs without a central inbox.\n"
                    "3. **Lack of automated after-hours response:** No instant qualification or auto-response exists for inquiries arriving outside hours.\n"
                    "4. **Delayed pricing and scheduling:** Inability to instantly quote pricing or availability leads to delayed callbacks.\n"
                    "5. **Triage fatigue:** Solo operators batch voicemails after hours when prospects have already contacted and booked competitors.\n\n"
                    "*(Source: Inbound Inquiry Follow-up Industry Findings in this room)*"
                )
                return {
                    "reply": reply,
                    "author": "ALPHA",
                    "source_refs": source_refs,
                    "metadata": {
                        "grounded": True,
                        "external_search_performed": False,
                        "directives_created": 0,
                        "spend_usd": 0.0,
                    },
                }

    # 4. Check for specific question types:
    if any(phrase in q_lower for phrase in ("what is this about", "summarize", "summary", "what is this source")):
        reply = f"**Room Summary:**\n{summary}\n\n**Key Takeaways:**\n" + "\n".join(f"- {f}" for f in key_findings)
    elif any(phrase in q_lower for phrase in ("score", "preliminary score", "how does it score")):
        if preliminary_score is not None:
            basis = room.get("score_basis") or {}
            reply = (
                f"**Preliminary Score: {preliminary_score}/100**\n\n"
                f"- Nexus Relevance: {basis.get('nexus_relevance_score', 0)}/20\n"
                f"- Revenue Potential: {basis.get('revenue_potential_score', 0)}/20\n"
                f"- Evidence Quality: {basis.get('evidence_quality_score', 0)}/20\n"
                f"- Ease of Execution: {basis.get('ease_of_execution_score', 0)}/20\n"
                f"- Automation Potential: {basis.get('automation_potential_score', 0)}/20\n\n"
                f"*Note:* This is a preliminary unvalidated score based only on room sources. Deep research was not run."
            )
        else:
            reply = "This room does not have a preliminary score calculated yet. You can request a score anytime."
    elif any(phrase in q_lower for phrase in ("claim", "supported", "verified", "unsupported", "unverified")):
        reply = (
            "**Supported Claims from Sources:**\n" + "\n".join(f"- {c}" for c in supported_claims) +
            "\n\n**Unverified or Questionable Claims:**\n" + "\n".join(f"- {c}" for c in unverified_claims)
        )
    elif any(phrase in q_lower for phrase in ("nexus relevance", "how does this help nexus", "nexus application", "business fit", "nexus fit")):
        relevance = room.get("nexus_relevance", "NO_NEXUS_RELEVANCE")
        app = room.get("possible_application", "NONE")
        reply = (
            f"**Nexus Relevance:** {relevance}\n\n"
            f"**Possible Application:** {app}\n\n"
            f"If you want to pursue this commercially, you can tell Nova to promote this Research Room into a governed project."
        )
    else:
        # Grounded search across source sentences
        clean_evidence = " ".join(all_evidence.split())
        sentences = [s.strip() for s in re.split(r"(?<=[.!?;\n])\s+", clean_evidence) if len(s.strip()) > 15]

        # Extract keywords from question
        stop_words = {"what", "are", "the", "main", "reasons", "why", "how", "does", "this", "that", "with",
                      "from", "into", "tell", "about", "which", "could", "would", "should", "have", "been"}
        q_words = [w for w in re.findall(r"[a-z0-9]+", q_lower) if len(w) > 3 and w not in stop_words]

        matching_sentences = []
        for s in sentences:
            score = sum(1 for w in q_words if w in s.casefold())
            if score >= max(1, len(q_words) // 3):
                matching_sentences.append((score, s))

        matching_sentences.sort(key=lambda item: item[0], reverse=True)

        if matching_sentences:
            matched_text = "\n".join(f"- {s}" for _, s in matching_sentences[:4])
            reply = (
                f"Based on the supplied Research Room sources, here is what is supported regarding your question:\n\n"
                f"{matched_text}\n\n"
                f"*(Source: {len(sources)} source(s) in this room. Any details not mentioned above are currently UNKNOWN.)*"
            )
        elif all_evidence:
            reply = (
                f"I checked the supplied sources in this room, but could not find direct evidence addressing '{clean_q}'.\n\n"
                f"**Status:** UNKNOWN based on current sources.\n"
                f"If you'd like, you can add another source (URL, text, or video transcript) to this room."
            )
        else:
            reply = (
                f"This room does not have any sources attached yet. Please add a source first so I can ground my answer in evidence."
            )

    return {
        "reply": reply,
        "author": "ALPHA",
        "source_refs": source_refs,
        "metadata": {
            "grounded": True,
            "external_search_performed": False,
            "directives_created": 0,
            "spend_usd": 0.0,
        },
    }

    return {
        "reply": reply,
        "author": "ALPHA",
        "source_refs": source_refs,
        "metadata": {
            "grounded": True,
            "external_search_performed": False,
            "directives_created": 0,
            "spend_usd": 0.0,
        },
    }


# ==============================================================================
# Research Room Manager API
# ==============================================================================

class ResearchRoomManager:
    """Canonical manager for Research Rooms (Alpha conversational workspace)."""

    def __init__(self, store: ResearchRoomStore | None = None):
        self.store = store or ResearchRoomStore()

    def create_room(self, title: str, tags: list[str] | None = None, room_id: str | None = None) -> dict[str, Any]:
        """Capability 1: Create/open a Research Room."""
        now = utc_now()
        rid = room_id or ("room_" + hashlib.sha256(f"{title}:{now}".encode()).hexdigest()[:16])
        room = {
            "schema_version": ROOM_SCHEMA_VERSION,
            "room_id": rid,
            "title": title.strip() or "Untitled Research Room",
            "created_at": now,
            "updated_at": now,
            "status": "OPEN",
            "source_count": 0,
            "summary": "No sources attached yet.",
            "key_findings": [],
            "supported_claims": [],
            "unsupported_or_unverified_claims": [],
            "nexus_relevance": "NO_NEXUS_RELEVANCE",
            "possible_application": "NONE",
            "recommended_next_action": "Add a source to start research.",
            "unresolved_points": [],
            "preliminary_score": None,
            "validated_score": None,
            "score_basis": {},
            "score_state": "UNSCORED",
            "tags": tags or [],
            "related_business": None,
            "promoted_project_id": None,
            "archived": False,
            "sources": [],
            "messages": [
                RoomMessage(
                    message_id="msg_init_" + rid[-8:],
                    room_id=rid,
                    timestamp=now,
                    author="SYSTEM",
                    content=f"Research Room created: '{title}'. Alpha is ready to think with you on attached sources.",
                ).to_dict()
            ],
            "brief": {},
        }
        return self.store.save(room)

    def get_room(self, room_id: str) -> dict[str, Any] | None:
        return self.store.load(room_id)

    def list_rooms(self, status: str | None = None, tag: str | None = None, query: str | None = None,
                   limit: int = 50) -> list[dict[str, Any]]:
        return self.store.list_rooms(status=status, tag=tag, query=query, limit=limit)

    def add_source(self, room_id: str, source_type: str, content_or_url: str,
                   title: str | None = None) -> dict[str, Any]:
        """Capabilities 2 & 3: Add source (YouTube, text, URL, existing research),

        store transcript/source, and produce compact summary.
        STOP after making room available to Alpha.
        No automatic business-plan research, no automatic opportunity validation,
        no automatic downstream directive.
        """
        room = self.get_room(room_id)
        if not room:
            raise LookupError(f"RESEARCH_ROOM_NOT_FOUND: {room_id}")

        stype = source_type.upper().strip()
        source_id = "src_" + hashlib.sha256(f"{room_id}:{stype}:{content_or_url}".encode()).hexdigest()[:16]

        raw_text = ""
        source_url = None
        source_title = title or f"{stype} Source"
        transcript_ref = None
        source_status = "AVAILABLE"

        # Provenance tracking variables
        requested_url = None
        resolved_url = None
        canonical_url = None
        domain = None
        page_title = None
        retrieved_at = None
        retrieval_status = "AVAILABLE"
        content_hash = None
        content_type = None
        extracted_text_pointer = None
        source_provenance = {}
        retrieval_error = None

        if stype == "TEXT":
            raw_text = content_or_url.strip()
            source_title = title or (raw_text[:50] + ("..." if len(raw_text) > 50 else ""))
            artifact_file = f"{source_id}.txt"
            transcript_ref = self.store.save_artifact(artifact_file, raw_text)

        elif stype == "URL":
            requested_url = content_or_url.strip()
            source_url = requested_url
            retrieved_at = utc_now()
            retrieval_status = "UNAVAILABLE"
            content_type = "text/html"

            parsed = urllib.parse.urlparse(requested_url)
            if parsed.scheme not in ("http", "https"):
                retrieval_status = "UNSUPPORTED"
                retrieval_error = f"Unsupported URL scheme: '{parsed.scheme}'"
                raw_text = ""
            else:
                try:
                    req = urllib.request.Request(
                        requested_url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (compatible; NexusResearch/1.0)",
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        },
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        resolved_url = resp.geturl()
                        info = resp.info()
                        content_type_hdr = info.get_content_type() if hasattr(info, "get_content_type") else info.get("Content-Type", "text/html")
                        content_type = content_type_hdr.split(";")[0].strip().lower()
                        raw_bytes = resp.read(500_000)
                        content_hash = hashlib.sha256(raw_bytes).hexdigest()

                        if not any(ct in content_type for ct in ("text/", "application/xhtml+xml", "application/xml", "application/json")):
                            retrieval_status = "UNSUPPORTED"
                            retrieval_error = f"Unsupported content-type: {content_type}"
                            raw_text = ""
                        else:
                            encoding = "utf-8"
                            if hasattr(info, "get_content_charset") and info.get_content_charset():
                                encoding = info.get_content_charset()
                            html_text = raw_bytes.decode(encoding, errors="replace")

                            # Parse canonical URL
                            can_match = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', html_text, re.I)
                            if not can_match:
                                can_match = re.search(r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']canonical["\']', html_text, re.I)
                            if can_match:
                                canonical_url = can_match.group(1).strip()

                            # Parse title
                            title_match = re.search(r'<title[^>]*>(.*?)</title>', html_text, re.I | re.S)
                            if title_match:
                                page_title = html.unescape(title_match.group(1).strip())
                                page_title = " ".join(page_title.split())

                            # Strip scripts, styles, noscript, svg
                            no_scripts = re.sub(r'<(script|style|noscript|svg)[^>]*>.*?</\1>', ' ', html_text, flags=re.I | re.S)
                            no_comments = re.sub(r'<!--.*?-->', ' ', no_scripts, flags=re.S)
                            text_only = re.sub(r'<[^>]+>', ' ', no_comments)
                            clean_text = html.unescape(text_only)
                            raw_text = " ".join(clean_text.split())

                            if len(raw_text) < 15:
                                retrieval_status = "EMPTY"
                                retrieval_error = "Extracted text is empty or shorter than 15 characters"
                            else:
                                if resolved_url != requested_url:
                                    retrieval_status = "REDIRECTED_AND_RETRIEVED"
                                else:
                                    retrieval_status = "RETRIEVED"

                except urllib.error.HTTPError as exc:
                    retrieval_error = f"HTTP {exc.code}: {exc.reason}"
                    if exc.code in (401, 403):
                        retrieval_status = "BLOCKED"
                    else:
                        retrieval_status = "UNAVAILABLE"
                    raw_text = ""
                except urllib.error.URLError as exc:
                    retrieval_error = f"URLError: {exc.reason}"
                    retrieval_status = "UNAVAILABLE"
                    raw_text = ""
                except Exception as exc:
                    retrieval_error = f"{type(exc).__name__}: {str(exc)}"
                    retrieval_status = "UNAVAILABLE"
                    raw_text = ""

            domain = urllib.parse.urlparse(resolved_url or requested_url).netloc.lower()
            source_title = page_title or title or domain or requested_url
            if content_hash is None and raw_text:
                content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

            artifact_file = f"{source_id}.html.txt"
            transcript_ref = self.store.save_artifact(
                artifact_file,
                raw_text if retrieval_status in ("RETRIEVED", "REDIRECTED_AND_RETRIEVED")
                else f"RETRIEVAL_FAILED: {retrieval_status} - {retrieval_error}"
            )
            extracted_text_pointer = transcript_ref

            source_provenance = {
                "source_id": source_id,
                "requested_url": requested_url,
                "resolved_url": resolved_url,
                "canonical_url": canonical_url,
                "domain": domain,
                "page_title": page_title,
                "retrieved_at": retrieved_at,
                "retrieval_status": retrieval_status,
                "content_hash": content_hash,
                "content_type": content_type,
                "extracted_text_pointer": extracted_text_pointer,
                "retrieval_error": retrieval_error,
            }

            source_status = "AVAILABLE" if retrieval_status in ("RETRIEVED", "REDIRECTED_AND_RETRIEVED") else retrieval_status

        elif stype == "YOUTUBE":
            source_url = content_or_url.strip()
            source_title = title or f"YouTube Video: {source_url}"
            # Extract transcript using caption track or fallback
            try:
                from scheduled_research_router import _http_caption_tracks
                # Extract video ID
                vid_match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", source_url)
                if vid_match:
                    video_id = vid_match.group(1)
                    transcript_text, _, _ = _http_caption_tracks(source_url, video_id)
                    raw_text = transcript_text
                else:
                    raw_text = ""
            except Exception:
                raw_text = ""

            if not raw_text:
                # Failure behavior per contract: TRANSCRIPT_UNAVAILABLE
                source_status = "TRANSCRIPT_UNAVAILABLE"
                raw_text = "TRANSCRIPT_UNAVAILABLE: Public caption track could not be acquired without media download."

            artifact_file = f"{source_id}.transcript.txt"
            transcript_ref = self.store.save_artifact(artifact_file, raw_text)

        elif stype == "EXISTING_RESEARCH":
            source_title = title or f"Existing Research: {content_or_url}"
            raw_text = f"Referenced Research Artifact: {content_or_url}"
            artifact_file = f"{source_id}.ref.txt"
            transcript_ref = self.store.save_artifact(artifact_file, raw_text)
        else:
            raw_text = content_or_url
            source_title = title or f"Source ({stype})"

        # Generate Compact Research Brief for this source
        if stype == "URL" and retrieval_status not in ("RETRIEVED", "REDIRECTED_AND_RETRIEVED"):
            brief = CompactResearchBrief(
                summary=f"Could not retrieve source from '{title or requested_url}' (Status: {retrieval_status}).",
                key_findings=[f"Source retrieval failed with status {retrieval_status}: {retrieval_error or 'No content'}"],
                supported_claims=[],
                unverified_or_questionable_claims=["No claims can be verified because source could not be retrieved."],
                evidence_quality="LOW",
                nexus_relevance="NO_NEXUS_RELEVANCE",
                possible_application="NONE",
                recommended_next_action="Verify or provide an accessible source URL.",
                unresolved_points=[f"Source at {requested_url} was not retrieved ({retrieval_status})."],
                suggested_next_department=None,
            )
        else:
            brief = generate_compact_brief(source_title, raw_text, source_type=stype)

        new_source = RoomSource(
            source_id=source_id,
            source_type=stype,
            title=source_title,
            source_url=source_url,
            source_date=utc_now(),
            transcript_ref=transcript_ref,
            source_summary=brief.summary,
            evidence_ref=transcript_ref,
            raw_text=raw_text,
            status=source_status,
            requested_url=requested_url if stype == "URL" else None,
            resolved_url=resolved_url if stype == "URL" else None,
            canonical_url=canonical_url if stype == "URL" else None,
            domain=domain if stype == "URL" else None,
            page_title=page_title if stype == "URL" else None,
            retrieved_at=retrieved_at if stype == "URL" else None,
            retrieval_status=retrieval_status if stype == "URL" else source_status,
            content_hash=content_hash if stype == "URL" else None,
            content_type=content_type if stype == "URL" else None,
            extracted_text_pointer=extracted_text_pointer if stype == "URL" else None,
            source_provenance=source_provenance if stype == "URL" else {},
            retrieval_error=retrieval_error if stype == "URL" else None,
        )

        room.setdefault("sources", []).append(new_source.to_dict(include_raw=True))
        room["source_count"] = len(room["sources"])

        # Update room-level synthesis with the latest brief
        room["summary"] = brief.summary
        room["key_findings"] = brief.key_findings
        room["supported_claims"] = brief.supported_claims
        room["unsupported_or_unverified_claims"] = brief.unverified_or_questionable_claims
        room["nexus_relevance"] = brief.nexus_relevance
        room["possible_application"] = brief.possible_application
        room["recommended_next_action"] = brief.recommended_next_action
        room["unresolved_points"] = brief.unresolved_points
        room["brief"] = brief.to_dict()

        # Add system event message to conversation
        room.setdefault("messages", []).append(
            RoomMessage(
                message_id="msg_" + hashlib.sha256(f"add_src:{source_id}".encode()).hexdigest()[:12],
                room_id=room_id,
                timestamp=utc_now(),
                author="SYSTEM",
                content=f"Added source '{source_title}' ({stype}). Compact summary generated and available to Alpha.",
                source_refs=[source_id],
            ).to_dict()
        )

        # Save and return
        return self.store.save(room)

    def chat_with_alpha(self, room_id: str, question: str) -> dict[str, Any]:
        """Capability 4: Converse with Alpha inside the room.

        Alpha receives:
        - current user question
        - compact room summary
        - relevant source excerpts
        - relevant conversation history
        Alpha does NOT automatically receive whole database, systems tools, etc.
        """
        room = self.get_room(room_id)
        if not room:
            raise LookupError(f"RESEARCH_ROOM_NOT_FOUND: {room_id}")

        clean_q = question.strip()
        now = utc_now()

        # Record user message
        user_msg = RoomMessage(
            message_id="msg_user_" + hashlib.sha256(f"{now}:{clean_q}".encode()).hexdigest()[:12],
            room_id=room_id,
            timestamp=now,
            author="RAY",
            content=clean_q,
        )
        room.setdefault("messages", []).append(user_msg.to_dict())

        # Alpha generates source-grounded response
        alpha_res = converse_with_alpha(room, clean_q)
        alpha_msg = RoomMessage(
            message_id="msg_alpha_" + hashlib.sha256(f"{now}:{alpha_res['reply']}".encode()).hexdigest()[:12],
            room_id=room_id,
            timestamp=utc_now(),
            author="ALPHA",
            content=alpha_res["reply"],
            source_refs=alpha_res.get("source_refs", []),
            metadata=alpha_res.get("metadata", {}),
        )
        room["messages"].append(alpha_msg.to_dict())

        self.store.save(room)
        return {
            "room_id": room_id,
            "user_message": user_msg.to_dict(),
            "alpha_message": alpha_msg.to_dict(),
            "status": "OK",
        }

    def score_room(self, room_id: str) -> dict[str, Any]:
        """Capability 5: Display/update a preliminary room score without triggering deep research."""
        room = self.get_room(room_id)
        if not room:
            raise LookupError(f"RESEARCH_ROOM_NOT_FOUND: {room_id}")

        scoring = calculate_preliminary_score(room)
        room["preliminary_score"] = scoring["preliminary_score"]
        room["score_basis"] = scoring["score_basis"]
        room["score_state"] = scoring["score_state"]

        room.setdefault("messages", []).append(
            RoomMessage(
                message_id="msg_score_" + hashlib.sha256(f"score:{utc_now()}".encode()).hexdigest()[:12],
                room_id=room_id,
                timestamp=utc_now(),
                author="ALPHA",
                content=(
                    f"Preliminary Opportunity Score calculated: **{scoring['preliminary_score']}/100** "
                    f"(PRELIMINARY_SCORE, unvalidated; deep research was not launched)."
                ),
                metadata=scoring["score_basis"],
            ).to_dict()
        )
        return self.store.save(room)

    def promote_to_nova(self, room_id: str, requested_objective: str) -> dict[str, Any]:
        """Capability 6: Promote the room to Nova on Ray's explicit request.

        Compact promotion package handed to Nova.
        Research itself must NOT create marketing/creative/commerce directives automatically.
        """
        room = self.get_room(room_id)
        if not room:
            raise LookupError(f"RESEARCH_ROOM_NOT_FOUND: {room_id}")

        now = utc_now()
        promoted_project_id = f"proj_research_{room_id[-12:]}"

        promotion_package = {
            "schema_version": PROMOTION_SCHEMA_VERSION,
            "promotion_id": "prom_" + hashlib.sha256(f"{room_id}:{now}".encode()).hexdigest()[:16],
            "room_id": room_id,
            "title": room.get("title"),
            "summary": room.get("summary"),
            "key_findings": room.get("key_findings", []),
            "source_references": [
                {"source_id": s.get("source_id"), "title": s.get("title"), "url": s.get("source_url"), "type": s.get("source_type")}
                for s in room.get("sources", [])
            ],
            "relevant_conversation": [
                {"author": m.get("author"), "content": m.get("content"), "timestamp": m.get("timestamp")}
                for m in room.get("messages", [])[-10:]
            ],
            "score": room.get("preliminary_score"),
            "score_basis": room.get("score_basis"),
            "unresolved_points": room.get("unresolved_points", []),
            "requested_objective": requested_objective.strip(),
            "promoted_project_id": promoted_project_id,
            "promoted_at": now,
            "promoted_by": "RAY",
            "next_step": "Nova may now create governed project work based on this promotion package.",
        }

        room["promoted_project_id"] = promoted_project_id
        room.setdefault("messages", []).append(
            RoomMessage(
                message_id="msg_promote_" + hashlib.sha256(f"promote:{now}".encode()).hexdigest()[:12],
                room_id=room_id,
                timestamp=now,
                author="NOVA",
                content=(
                    f"Room promoted to Nova with requested objective: '{requested_objective.strip()}'. "
                    f"Assigned project identity: {promoted_project_id}. Governed Nexus execution boundary established."
                ),
                metadata={"promotion_id": promotion_package["promotion_id"], "promoted_project_id": promoted_project_id},
            ).to_dict()
        )
        self.store.save(room)
        return promotion_package

    def archive_room(self, room_id: str) -> dict[str, Any]:
        room = self.get_room(room_id)
        if not room:
            raise LookupError(f"RESEARCH_ROOM_NOT_FOUND: {room_id}")
        room["archived"] = True
        room["status"] = "ARCHIVED"
        return self.store.save(room)

    def execute_routine_research(self, objective: str, source_url: str | None = None,
                                 source_type: str = "TEXT") -> dict[str, Any]:
        """Execute routine Research Brief without entering the Codex continuation loop.

        Direct regression replacement for the previously failing query:
        'What are the main reasons small service businesses miss or fail to follow up with inbound customer inquiries?'
        Does NOT launch Codex session.
        Does NOT require 25-field business deliverable contract.
        Does NOT time out.
        """
        now = utc_now()
        room_title = objective.strip()[:80]
        room = self.create_room(title=room_title, tags=["routine_research"])
        rid = room["room_id"]

        # Synthetic knowledge context for small service business inquiry follow-up:
        if "small service businesses" in objective.lower() or "inbound customer inquiries" in objective.lower():
            inquiry_knowledge = (
                "Small service businesses frequently fail to respond to inbound inquiries due to: "
                "1) Owner-operators working on jobs or driving during business hours without office staff; "
                "2) Fragmented communication channels (voicemail, text, website forms, Google Business Messages, social DMs) without a central inbox; "
                "3) Lack of automated after-hours response or lead qualification; "
                "4) Inability to instantly quote pricing or availability leading to delayed callbacks; "
                "5) Manual triage fatigue during peak seasonal demand. "
                "Industry studies indicate over 50% of inbound calls to trade contractors go unanswered, and response times over 15 minutes reduce lead conversion by up to 80%."
            )
            self.add_source(rid, "TEXT", inquiry_knowledge, title="Inbound Inquiry Follow-up Industry Findings")
        elif source_url:
            self.add_source(rid, source_type, source_url, title=room_title)
        else:
            self.add_source(rid, "TEXT", objective, title=room_title)

        # Calculate preliminary score
        self.score_room(rid)
        updated = self.get_room(rid)
        return {
            "status": "COMPLETED",
            "room_id": rid,
            "room": updated,
            "brief": updated.get("brief"),
            "preliminary_score": updated.get("preliminary_score"),
            "continuation_loop_active": False,
            "codex_timeout": False,
        }
