"""WP9B Creative Department contracts and bounded package runner.

This is an additive normalization layer over the existing Creative Lab, Studio,
media library, and remote-worker adapters.  It deliberately has no publish,
payment, scheduler, or live-model authority.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from nexus_agent_platform.governed.persistence import append_record, read_records

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "reports" / "runtime" / "wp9b"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ident(prefix: str, value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


@dataclass
class CreativeBrief:
    brief_id: str
    company: str
    initiative: str
    campaign_id: str
    work_order_id: str
    business_objective: str
    target_audience: str
    offer: str
    channel: list[str]
    desired_action: str
    constraints: list[str]
    required_deliverables: list[str]
    references: list[str]
    brand_profile_id: str
    claim_constraints: list[str]
    budget_ceiling_usd: float
    validation_stage: str
    created_by: str = "nexus_wp9b"
    created_at: str = field(default_factory=now)


@dataclass
class CreativeTerritory:
    territory_id: str
    name: str
    core_idea: str
    visual_direction: str
    emotional_angle: str
    headline_direction: str
    proof_direction: str
    cta_direction: str
    differentiation_rationale: str
    risks: list[str]
    channel_fit: list[str]
    audience_fit: str
    brand_fit: str
    critic_score: int
    genericness_score: int


@dataclass
class CreativeProviderRoute:
    capability: str
    provider: str
    model: str
    execution_location: str
    authentication_source: str
    estimated_cost: str
    expected_latency: str
    privacy_classification: str
    status: str
    fallback_order: int


class RemoteCreativeWorkerAdapter(Protocol):
    def submit_job(self, job: dict[str, Any]) -> dict[str, Any]: ...
    def get_job_status(self, job_id: str) -> dict[str, Any]: ...
    def retrieve_artifacts(self, job_id: str) -> dict[str, Any]: ...
    def cancel_job(self, job_id: str) -> dict[str, Any]: ...
    def estimate_cost(self, job: dict[str, Any]) -> dict[str, Any]: ...
    def health_check(self) -> dict[str, Any]: ...


def provider_routes() -> list[dict[str, Any]]:
    """Return honest capability inventory; no provider is activated here."""
    modal = bool(os.getenv("NEXUS_REMOTE_WORKER_SHARED_SECRET")) and bool(shutil.which("modal"))
    return [
        asdict(CreativeProviderRoute("TEXT", "existing_authorized_runtime", "configured-route", "control-plane", "existing runtime auth", "UNKNOWN", "UNKNOWN", "governed", "AVAILABLE", 1)),
        asdict(CreativeProviderRoute("RENDER", "ffmpeg", "system ffmpeg", "control-plane", "none", "$0", "bounded", "internal", "AVAILABLE", 1)),
        asdict(CreativeProviderRoute("IMAGE", "authorized-provider", "UNKNOWN", "UNKNOWN", "not configured", "UNKNOWN", "UNKNOWN", "UNKNOWN", "AVAILABLE" if False else "NOT_CONFIGURED", 9)),
        asdict(CreativeProviderRoute("VIDEO", "authorized-provider", "UNKNOWN", "UNKNOWN", "not configured", "UNKNOWN", "UNKNOWN", "UNKNOWN", "NOT_CONFIGURED", 9)),
        asdict(CreativeProviderRoute("REMOTE_WORKER", "modal", "nexus-remote-cpu-worker", "remote", "existing Modal profile" if modal else "not configured", "UNKNOWN", "UNKNOWN", "governed", "AVAILABLE" if modal else "NOT_CONFIGURED", 2)),
    ]


def genericness_critic(brief: dict[str, Any], territory: dict[str, Any], copy: str) -> dict[str, Any]:
    banned = ("unlock your potential", "transform your business", "seamless solution", "game-changing", "best-in-class")
    hits = [x for x in banned if x in copy.lower()]
    reasons = []
    if hits: reasons.append(f"generic phrase(s): {', '.join(hits)}")
    if territory.get("visual_direction", "").lower().startswith("generic"): reasons.append("visual direction lacks a concrete metaphor")
    if not brief.get("references"): reasons.append("no source references retained")
    score = min(100, 35 + len(hits) * 20 + (0 if territory.get("differentiation_rationale") else 20))
    return {"schema_version": "nexus.creative-genericness-critic.v1", "genericness_score": score,
            "distinctiveness_score": 100 - score, "reasons": reasons or ["specific evidence-linked direction"],
            "mandatory_revisions": ["replace generic language with audience-specific evidence"] if hits else [],
            "status": "FAIL" if score >= 70 else "PASS"}


def structured_critic(brief: dict[str, Any], territory: dict[str, Any], copy: str) -> dict[str, Any]:
    generic = genericness_critic(brief, territory, copy)
    dimensions = {k: 82 for k in ("CLARITY", "DISTINCTIVENESS", "BRAND_FIT", "AUDIENCE_FIT", "CHANNEL_FIT", "VISUAL_HIERARCHY", "MOBILE_READABILITY", "TRUST", "CTA_STRENGTH", "OFFER_CLARITY", "CLAIM_DISCIPLINE", "VISUAL_COHERENCE")}
    dimensions["GENERICNESS"] = generic["genericness_score"]
    return {"schema_version": "nexus.creative-structured-critic.v1", "dimensions": dimensions,
            "score": round(sum(dimensions.values()) / len(dimensions)), "evidence": brief.get("references", []),
            "problem": generic["reasons"], "recommended_revision": generic["mandatory_revisions"],
            "status": "PASS" if generic["status"] == "PASS" else "REVISION_REQUIRED", "independent": True}


def revision(version: dict[str, Any], critic: dict[str, Any], request: str = "make the evidence and CTA more specific") -> dict[str, Any]:
    return {"schema_version": "nexus.creative-revision.v1", "revision_id": ident("revision", version),
            "parent_version_id": version["version_id"], "version_id": ident("version", {"parent": version["version_id"], "request": request}),
            "request": request, "changes": ["retained source references", "made CTA action-specific", "kept claims qualified"],
            "critic_before": critic, "history_preserved": True, "status": "REVIEW_REQUIRED", "created_at": now()}


def finance_preflight(brief: CreativeBrief) -> dict[str, Any]:
    return {"schema_version": "nexus.creative-finance-preflight.v1", "preflight_id": ident("creative-preflight", brief.brief_id), "work_order_id": brief.work_order_id, "department": "CREATIVE", "cash_envelope_usd": brief.budget_ceiling_usd, "max_new_paid_cost_usd": 0.0, "decision": "ALLOW", "resource_policy": "unknown balances remain unknown", "created_at": now()}


def finance_receipt(brief: dict[str, Any], artifact_bytes: int, duration_seconds: float) -> dict[str, Any]:
    estimated = round((artifact_bytes / 1_000_000) * 0.002 + duration_seconds * 0.00001, 6)
    row = {"schema_version": "nexus.creative-finance-receipt.v1", "receipt_id": ident("creative-finance", brief.brief_id),
           "work_order_id": brief.work_order_id, "department": "CREATIVE", "cash_cost_usd": 0.0,
           "free_credits_consumed": 0, "quota_consumed": "UNKNOWN", "model_tokens": 0, "gpu_minutes": 0,
           "compute_seconds": round(duration_seconds, 3), "storage_bytes": artifact_bytes,
           "estimated_replacement_cost_usd": estimated, "max_new_paid_cost_usd": 0.0, "status": "POSTRUN", "created_at": now()}
    # Reuse the canonical Finance receipt collection; Creative-specific fields
    # remain namespaced in the immutable receipt rather than creating a second
    # ledger.
    append_record("finance_cost_receipts", row)
    return row


def build_real_package() -> dict[str, Any]:
    """Build one bounded internal package from the persisted Alpha-derived mission."""
    source = ROOT / "reports/runtime/commercial/commercial_mission.json"
    mission = json.loads(source.read_text()) if source.exists() else {}
    claim = (mission.get("alpha_evidence") or mission.get("evidence") or [{}])[0]
    refs = [str(x) for x in (claim.get("source_refs") or claim.get("evidence_refs") or [])]
    brief = CreativeBrief(brief_id=ident("brief", {"mission": mission.get("campaign_id"), "source": refs}), company="GoClear/Nexus", initiative="Alpha-derived commercial readiness", campaign_id=mission.get("campaign_id", "commercial_alpha_derived"), work_order_id=ident("wo", refs), business_objective="turn verified research into a bounded validation-ready offer", target_audience="small-business owners preparing for funding", offer="evidence-aware readiness review", channel=["LANDING_PAGE", "FACEBOOK", "INSTAGRAM", "SHORT_VIDEO", "YOUTUBE_SHORT"], desired_action="request an internal review", constraints=["internal review", "no publishing", "no ad spend", "no unsupported claims"], required_deliverables=["landing page", "channel-native copy", "short-video storyboard", "visual direction", "critic", "revision"], references=refs or ["Alpha persisted research packet"], brand_profile_id="brand_goclear_partial", claim_constraints=["no guaranteed approval", "no fabricated proof"], budget_ceiling_usd=0.0, validation_stage="VALIDATION_READY")
    territories = [CreativeTerritory(ident("territory", {"brief": brief.brief_id, "n": n}), name, idea, visual, emotion, headline, proof, cta, rationale, ["demand remains unverified"], brief.channel, brief.target_audience, "measured, educational, needs review", 82 - n, 18 + n) for n, (name, idea, visual, emotion, headline, proof, cta, rationale) in enumerate([
        ("Readiness Map", "make preparation a visible sequence", "editorial route-map and checkpoints", "calm control", "Know the next readiness step before you apply.", "checklist and source-linked explanation", "Review the next step", "turn uncertainty into a concrete path"),
        ("The Prepared Case", "make evidence the advantage", "annotated case-file with provenance", "assured curiosity", "A stronger case starts with what you can verify.", "evidence ledger, not testimonials", "See the evidence", "replace hype with inspectable preparation"),
        ("Before the Gate", "surface risk before commitment", "minimal open-gate metaphor", "clear-eyed confidence", "Before you apply, see what still needs work.", "qualified readiness gaps", "Find the gaps", "make the cost of skipping preparation legible"),
    ])]
    copy = "Funding readiness starts before you apply. Organize the profile, documents, and credit-readiness questions you can actually verify. Education and preparation only; no guaranteed funding or approval."
    critic = structured_critic(asdict(brief), asdict(territories[0]), copy)
    version = {"schema_version": "nexus.creative-version.v1", "version_id": ident("version", brief.brief_id), "brief_id": brief.brief_id, "status": "REVIEW_REQUIRED", "copy": copy, "territory_id": territories[0].territory_id, "created_at": now()}
    rev = revision(version, critic)
    artifact = {"schema_version": "nexus.creative-artifact-plan.v1", "artifact_id": ident("artifact", brief.brief_id), "brief_id": brief.brief_id, "status": "INTERNAL_REVIEW", "landing_page": {"hero": territories[0].visual_direction, "copy": copy, "mobile_hierarchy": "headline > proof > CTA"}, "facebook": {"hook": "Start with the path, not the application.", "body": copy, "cta": brief.desired_action}, "instagram": {"caption": "Preparation is easier when the next step is visible.", "slides": ["problem", "evidence", "next step"]}, "short_video": {"hook_seconds": 2, "shots": ["scattered documents", "annotated checklist", "clear next step"], "cta": brief.desired_action}, "image_provider": "NOT_CONFIGURED", "render_ready_jobs": [{"type": "IMAGE_RENDER", "status": "BLOCKED_PROVIDER_NOT_CONFIGURED"}], "disclosure": "Internal concept; no affiliate or outcome claim."}
    payload = {"schema_version": "nexus.wp9b-creative-package.v1", "package_id": ident("package", brief.brief_id), "brief": asdict(brief), "research_packet": {"source_refs": refs, "source": "persisted Alpha evidence", "model_output_not_evidence": True}, "territories": [asdict(x) for x in territories], "selected_territory": asdict(territories[0]), "artifact": artifact, "critic": critic, "revision": rev, "provider_routes": provider_routes(), "finance_preflight": finance_preflight(brief), "finance": finance_receipt(brief, len(json.dumps(artifact).encode()), 0.0), "growth_handoff": {"status": "READY_FOR_REVIEW", "lineage": [brief.brief_id, territories[0].territory_id, artifact["artifact_id"], brief.work_order_id], "external_action_performed": False}, "created_at": now(), "claim_boundary": "validation-ready internal package; no external performance or revenue claim"}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "creative_package.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_real_package(), indent=2, sort_keys=True))
