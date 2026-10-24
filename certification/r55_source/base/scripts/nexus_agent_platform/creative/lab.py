"""Deterministic-first Nexus Creative Lab.

The Creative Lab turns a canonical opportunity and bounded evidence into three
meaningfully distinct creative territories plus a build-spec skeleton. It does
not publish, deploy, or spend money.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from nexus_agent_platform.opportunities.engine import build_opportunity_business_case, canonicalize_opportunity_record

ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = ROOT / "reports" / "hermes_modernization"
OPEN_SOURCE_AUDIT_PATH = REPORT_DIR / "open_source_capability_audit.json"
SKILL_PATH = ROOT / "plugins" / "nexus-hermes-plugin" / "skills" / "nexus-creative-director" / "SKILL.md"


class CreativeLabError(ValueError):
    pass


@dataclass(frozen=True)
class CreativeBudget:
    max_ai_calls: int = 1
    max_input_tokens: int = 1_500
    max_output_tokens: int = 700
    cost_ceiling_usd: float = 0.5
    model_tier: str = "T2_STANDARD_AI"
    explicit_premium_escalation: bool = False


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(text: Any) -> str:
    return hashlib.sha256(json.dumps(text, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _approx_tokens(text: str) -> int:
    return max(0, len(text) // 4)


def _load_open_source_audit() -> Dict[str, Any]:
    return json.loads(OPEN_SOURCE_AUDIT_PATH.read_text(encoding="utf-8"))


def build_creative_audit() -> List[Dict[str, Any]]:
    return [
        {
            "component": "plugins/nexus-hermes-plugin/skills/nexus-creative-director/SKILL.md",
            "classification": "KEEP",
            "reason": "Creative direction is already a skill with research-first rules, not a persistent agent.",
        },
        {
            "component": "src/hermes/alpha/marketingAssetStudio.ts",
            "classification": "WRAP",
            "reason": "Provides bounded draft generation for marketing assets without autonomous publishing.",
        },
        {
            "component": "src/hermes/alpha/alphaBrain.ts",
            "classification": "EXTEND",
            "reason": "Already routes marketing_asset requests through Alpha with deterministic safety controls.",
        },
        {
            "component": "src/hermes/alpha/alphaEvaluationHarness.ts",
            "classification": "MERGE",
            "reason": "Existing fixture harness can host creative territory regression checks.",
        },
        {
            "component": "src/lib/hermesCapabilityRegistry.ts",
            "classification": "EXTEND",
            "reason": "Creative Studio capability is already inventoried as partial and needs a read-only inventory adapter.",
        },
        {
            "component": "src/data/marketingDraftsData.js",
            "classification": "MERGE",
            "reason": "Contains bounded marketing examples, hooks, and CTA patterns that can be reused as reference material.",
        },
        {
            "component": "src/lib/hermesIntent.ts",
            "classification": "WRAP",
            "reason": "Intent routing already recognizes landing-page and campaign surfaces that the Creative Lab should reuse.",
        },
        {
            "component": "src/lib/hermesWorkRouter.ts",
            "classification": "WRAP",
            "reason": "Work routing already maps marketing and creative_studio work to bounded processes.",
        },
        {
            "component": "src/lib/approvalReview.ts",
            "classification": "EXTEND",
            "reason": "Approval review already governs creative readiness and should remain the approval boundary.",
        },
        {
            "component": "src/lib/nexusProjects.ts",
            "classification": "EXTEND",
            "reason": "Creative project inventory already surfaces the creative tab and project metadata.",
        },
        {
            "component": "scripts/creative/create_design_brief.py",
            "classification": "WRAP",
            "reason": "Already assembles design briefs that should feed the Creative Director instead of being duplicated.",
        },
        {
            "component": "scripts/creative/generate_design_variants.py",
            "classification": "MERGE",
            "reason": "Existing design variant generation can be reused as a regression surface for territory comparison.",
        },
        {
            "component": "scripts/creative/score_design_variants.py",
            "classification": "MERGE",
            "reason": "Existing scoring logic should be wrapped into Creative Lab verification rather than duplicated.",
        },
        {
            "component": "scripts/creative/compare_design_variants.py",
            "classification": "MERGE",
            "reason": "Already compares candidate directions and can host territory distinctiveness checks.",
        },
        {
            "component": "scripts/creative/create_creative_approvals.py",
            "classification": "WRAP",
            "reason": "Approval gating already exists and should remain the authority for publish-ready creative decisions.",
        },
        {
            "component": "scripts/creative/generate_campaign_assets.py",
            "classification": "WRAP",
            "reason": "Campaign asset generation is already present as draft-only output and can be governed by the lab.",
        },
        {
            "component": "scripts/creative/generate_overnight_creative_asset_queue.py",
            "classification": "WRAP",
            "reason": "The overnight queue is an existing bounded creative runner, not a new identity.",
        },
        {
            "component": "scripts/creative/generate_best_money_opportunity_creative_package.py",
            "classification": "WRAP",
            "reason": "Opportunity-specific creative packaging should be wrapped by the Creative Director, not reimplemented.",
        },
        {
            "component": "scripts/creative/create_social_post_drafts.py",
            "classification": "WRAP",
            "reason": "Social draft generation already exists and must remain draft-only and approval-gated.",
        },
        {
            "component": "scripts/creative/create_publish_readiness_package.py",
            "classification": "EXTEND",
            "reason": "Publish-readiness packaging is already aligned with approval workflows and can absorb Creative Lab output.",
        },
        {
            "component": "scripts/creative/review_publish_package.py",
            "classification": "EXTEND",
            "reason": "Publish review is the correct place to verify creative output before any release action.",
        },
        {
            "component": "scripts/creative/_design.py",
            "classification": "MERGE",
            "reason": "Low-level design helpers should remain the deterministic implementation surface.",
        },
        {
            "component": "scripts/creative/_publish.py",
            "classification": "WRAP",
            "reason": "Publishing stays outside the lab; existing publish helpers are only a governed wrapper target.",
        },
        {
            "component": "scripts/marketing/build_landing_page_experiments.py",
            "classification": "WRAP",
            "reason": "Landing-page experiment generation already exists and should be routed through evidence-first creative direction.",
        },
        {
            "component": "scripts/marketing/build_content_calendar.py",
            "classification": "WRAP",
            "reason": "Content calendar generation is a bounded marketing planning surface already in place.",
        },
        {
            "component": "scripts/marketing/build_newsletter_draft.py",
            "classification": "WRAP",
            "reason": "Newsletter drafting is already a bounded marketing artifact and should not fork into another system.",
        },
        {
            "component": "scripts/marketing/build_social_draft_queue.py",
            "classification": "WRAP",
            "reason": "Social draft queue is existing bounded creative infrastructure.",
        },
        {
            "component": "scripts/marketing/build_short_video_script_queue.py",
            "classification": "WRAP",
            "reason": "Video script queue already exists and should be controlled as a creative artifact source.",
        },
        {
            "component": "scripts/design/create_feature_design_packet.py",
            "classification": "WRAP",
            "reason": "Feature design packets are existing design artifacts that the lab can reference instead of duplicate.",
        },
        {
            "component": "scripts/design/extract_design_patterns.py",
            "classification": "WRAP",
            "reason": "Pattern extraction already provides a reusable, deterministic design signal source.",
        },
        {
            "component": "scripts/design/register_design_inspiration.py",
            "classification": "WRAP",
            "reason": "Design inspiration registry is already the right place for reference collection.",
        },
        {
            "component": "scripts/design/review_ui_quality.py",
            "classification": "MERGE",
            "reason": "UI quality review can feed territory verification and distinctiveness checks.",
        },
        {
            "component": "scripts/seed_day9_creative_design_department.py",
            "classification": "MERGE",
            "reason": "The seeded creative design department is already a deterministic workflow and should be reused.",
        },
        {
            "component": "reports/hermes_modernization/open_source_capability_audit.json",
            "classification": "WRAP",
            "reason": "Provides the public-evidence reference set for the safe pilot.",
        },
        {
            "component": "reports/marketing_assets/*",
            "classification": "MERGE",
            "reason": "Existing draft assets are reference material, not a replacement for the creative lab.",
        },
        {
            "component": "frontend design tool installs",
            "classification": "DEFER",
            "reason": "Penpot, Excalidraw, and similar tools are future research only for this phase.",
        },
        {
            "component": "brand-guideline generation pipeline",
            "classification": "WRAP",
            "reason": "Brand guidance already exists implicitly in current marketing artifacts and should be referenced, not recreated.",
        },
        {
            "component": "new persistent creative agent",
            "classification": "CREATE_NEW",
            "reason": "Not allowed; creative direction remains a skill used by Hermes orchestration.",
        },
    ]


def build_creative_brief(opportunity: Dict[str, Any], evidence_refs: Sequence[Dict[str, Any]], market_refs: Sequence[Dict[str, Any]], previous_state: Dict[str, Any] | None = None) -> Dict[str, Any]:
    previous_state = previous_state or {}
    evidence_refs = list(evidence_refs)[:6]
    market_refs = list(market_refs)[:4]
    return {
        "opportunity": {
            "id": opportunity.get("id"),
            "title": opportunity.get("title"),
            "category": opportunity.get("category"),
            "problem": opportunity.get("problem"),
            "target_customer": opportunity.get("target_customer"),
            "recommended_next_action": opportunity.get("recommended_next_action"),
            "source_type": opportunity.get("source_type"),
            "source_commit": opportunity.get("source_commit"),
        },
        "evidence_refs": evidence_refs,
        "market_refs": market_refs,
        "whitespace": [
            "evidence-first positioning",
            "no public publishing promises",
            "compact operator-facing layouts",
        ],
        "overused_patterns": [
            "hero-first marketing fluff",
            "stock-photo trust theater",
            "unsupported performance claims",
        ],
        "previous_state": {
            "last_territory_hash": previous_state.get("last_territory_hash"),
            "last_recommendation": previous_state.get("last_recommendation"),
        },
        "history": None,
        "full_history": None,
        "generated_at": utc_now(),
        "source_commit": opportunity.get("source_commit"),
    }


def _territory_templates() -> List[Dict[str, Any]]:
    return [
        {
            "concept_name": "Evidence Ledger",
            "positioning": "Proof-first internal workspace that reads like a ledger of verified facts.",
            "target_audience": "Hermes and Alpha operators who need traceable evidence.",
            "primary_pain_desire": "They need confidence without ambiguity.",
            "emotional_direction": "calm, exact, trustworthy",
            "brand_voice": "measured, terse, governed",
            "visual_direction": "ledger cards, thin rules, restrained accent color",
            "layout_direction": "dense single-column with a strong evidence panel",
            "typography_direction": "small headlines, strong numerals, compact labels",
            "imagery_direction": "no hero imagery; evidence tiles and source chips only",
            "content_style": "fact blocks, provenance callouts, short conclusions",
            "primary_hook": "Verified evidence before interpretation.",
            "cta": "Open Evidence Trail",
            "differentiator": "Provenance is visible on every block.",
            "credibility_mechanism": "source hashes, timestamps, and bounded citations",
            "conversion_hypothesis": "Operators trust and reuse the workspace faster when proof is visible first.",
            "execution_complexity": "medium",
            "base_score": 0,
            "creative_score": 0,
            "rationale": "",
            "evidence_refs": [],
        },
        {
            "concept_name": "Scout Brief",
            "positioning": "Editorial intelligence brief that summarizes what was found and why it matters.",
            "target_audience": "operators who want a quick read before diving into details.",
            "primary_pain_desire": "They need a short, credible read with one obvious next step.",
            "emotional_direction": "curious, focused, informed",
            "brand_voice": "editorial, concise, clear",
            "visual_direction": "newsroom layout, boxed summary, clear hierarchy",
            "layout_direction": "hero summary plus a narrow evidence rail",
            "typography_direction": "medium headlines, readable body, tight line length",
            "imagery_direction": "small reference thumbnails and source icons only",
            "content_style": "brief paragraphs, bullets, callout summaries",
            "primary_hook": "What we found, what it means, what to do next.",
            "cta": "Read the Scout Brief",
            "differentiator": "Best for fast review without losing provenance.",
            "credibility_mechanism": "compact evidence summary and a one-step action path",
            "conversion_hypothesis": "A short editorial format reduces friction for first-time review.",
            "execution_complexity": "low",
            "base_score": 0,
            "creative_score": 0,
            "rationale": "",
            "evidence_refs": [],
        },
        {
            "concept_name": "Control Tower",
            "positioning": "Operator console that turns creative evidence into decision-ready modules.",
            "target_audience": "power users who manage multiple bounded workflows.",
            "primary_pain_desire": "They need a fast scan of what changed and what is ready.",
            "emotional_direction": "confident, operational, alert",
            "brand_voice": "directive, precise, utility-first",
            "visual_direction": "dashboard panes, cards, status chips, strong contrast",
            "layout_direction": "two-pane grid with a dominant readiness module",
            "typography_direction": "bold numerals, compact uppercase labels, minimal ornament",
            "imagery_direction": "status tiles and workflow icons rather than illustration",
            "content_style": "module cards, state summaries, action rows",
            "primary_hook": "Turn evidence into the next decision.",
            "cta": "Open Control Tower",
            "differentiator": "Designed for repeat use, not one-time consumption.",
            "credibility_mechanism": "status indicators, live evidence counters, and bounded next actions",
            "conversion_hypothesis": "A decision-first console reduces the time from review to action.",
            "execution_complexity": "medium",
            "base_score": 0,
            "creative_score": 0,
            "rationale": "",
            "evidence_refs": [],
        },
    ]


def build_creative_territories(brief: Dict[str, Any]) -> List[Dict[str, Any]]:
    evidence_refs = brief["evidence_refs"]
    market_refs = brief["market_refs"]
    combined = evidence_refs + market_refs
    territories = _territory_templates()
    for index, territory in enumerate(territories):
        territory["evidence_refs"] = combined[: max(1, min(len(combined), 3))]
        territory["rationale"] = (
            f"{territory['concept_name']} is tuned for {brief['opportunity']['title']} "
            f"with {len(territory['evidence_refs'])} evidence refs."
        )
        territory["base_score"], territory["creative_score"] = _score_territory(territory)
    return territories


def _score_territory(territory: Dict[str, Any]) -> Tuple[int, int]:
    originality = {"Evidence Ledger": 18, "Scout Brief": 16, "Control Tower": 15}.get(territory["concept_name"], 10)
    credibility = 18 if territory["credibility_mechanism"] else 0
    conversion = {"Evidence Ledger": 14, "Scout Brief": 15, "Control Tower": 16}.get(territory["concept_name"], 10)
    audience_fit = {"Evidence Ledger": 17, "Scout Brief": 15, "Control Tower": 16}.get(territory["concept_name"], 10)
    clarity = {"Evidence Ledger": 16, "Scout Brief": 17, "Control Tower": 15}.get(territory["concept_name"], 10)
    differentiation = {"Evidence Ledger": 18, "Scout Brief": 15, "Control Tower": 16}.get(territory["concept_name"], 10)
    execution_cost = {"Evidence Ledger": 12, "Scout Brief": 16, "Control Tower": 13}.get(territory["concept_name"], 10)
    time_to_test = {"Evidence Ledger": 12, "Scout Brief": 16, "Control Tower": 13}.get(territory["concept_name"], 10)
    score = originality + credibility + conversion + audience_fit + clarity + differentiation + execution_cost + time_to_test
    return score, score


def score_creative_territory(territory: Dict[str, Any]) -> Dict[str, Any]:
    base_score, creative_score = _score_territory(territory)
    return {
        **json.loads(json.dumps(territory, sort_keys=True, default=str)),
        "base_score": base_score,
        "creative_score": creative_score,
        "score_source": "deterministic_python",
        "score_components": {
            "originality": {"Evidence Ledger": 18, "Scout Brief": 16, "Control Tower": 15}.get(territory["concept_name"], 10),
            "credibility": 18 if territory.get("credibility_mechanism") else 0,
            "conversion_potential": {"Evidence Ledger": 14, "Scout Brief": 15, "Control Tower": 16}.get(territory["concept_name"], 10),
            "audience_fit": {"Evidence Ledger": 17, "Scout Brief": 15, "Control Tower": 16}.get(territory["concept_name"], 10),
            "clarity": {"Evidence Ledger": 16, "Scout Brief": 17, "Control Tower": 15}.get(territory["concept_name"], 10),
            "differentiation": {"Evidence Ledger": 18, "Scout Brief": 15, "Control Tower": 16}.get(territory["concept_name"], 10),
            "execution_cost": {"Evidence Ledger": 12, "Scout Brief": 16, "Control Tower": 13}.get(territory["concept_name"], 10),
            "time_to_test": {"Evidence Ledger": 12, "Scout Brief": 16, "Control Tower": 13}.get(territory["concept_name"], 10),
        },
    }


def validate_creative_claims(territory: Dict[str, Any]) -> List[str]:
    text = json.dumps(territory, sort_keys=True, default=str).lower()
    issues = []
    if any(term in text for term in ("guarantee", "guaranteed", "promise", "certified results", "double conversion", "risk free")):
        issues.append("unsupported_market_claim")
    if not territory.get("evidence_refs"):
        issues.append("evidence_refs_required")
    if not territory.get("target_audience"):
        issues.append("target_audience_required")
    if not territory.get("primary_hook"):
        issues.append("primary_hook_required")
    if not territory.get("differentiator"):
        issues.append("differentiator_required")
    return issues


def _territory_signature(territory: Dict[str, Any]) -> Tuple[str, ...]:
    return (
        territory.get("positioning", "").strip().lower(),
        territory.get("target_audience", "").strip().lower(),
        territory.get("emotional_direction", "").strip().lower(),
        territory.get("brand_voice", "").strip().lower(),
        territory.get("visual_direction", "").strip().lower(),
        territory.get("layout_direction", "").strip().lower(),
        territory.get("primary_hook", "").strip().lower(),
        territory.get("cta", "").strip().lower(),
    )


def evaluate_creative_set(territories: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    territories = [dict(t) for t in territories]
    if len(territories) < 3:
        raise CreativeLabError("fewer than 3 territories")
    signatures = [_territory_signature(territory) for territory in territories]
    if len(set(signatures)) < len(territories):
        raise CreativeLabError("cosmetic_only_variants")
    issues = []
    for territory in territories:
        issues.extend(validate_creative_claims(territory))
    if issues:
        raise CreativeLabError(",".join(sorted(set(issues))))
    return {
        "status": "passed",
        "territory_count": len(territories),
        "distinct_signatures": len(set(signatures)),
        "issues": [],
    }


def recommended_creative_tier(base_score: int, *, explicit_premium_escalation: bool = False) -> str:
    if base_score >= 85:
        return "T3_PREMIUM_AI" if explicit_premium_escalation else "T2_STANDARD_AI"
    if base_score >= 55:
        return "T2_STANDARD_AI"
    if base_score >= 35:
        return "T1_CHEAP_AI"
    return "T0_DETERMINISTIC"


def merge_ai_creative_rationale(territory: Dict[str, Any], ai_result: Dict[str, Any]) -> Dict[str, Any]:
    merged = json.loads(json.dumps(territory, sort_keys=True, default=str))
    merged["ai_rationale"] = ai_result.get("rationale", ai_result.get("ai_rationale", ""))
    merged["ai_summary"] = ai_result.get("summary", "")
    if "creative_score" in ai_result:
        merged["ai_proposed_creative_score"] = ai_result["creative_score"]
    if "base_score" in ai_result:
        merged["ai_proposed_base_score"] = ai_result["base_score"]
    return merged


def build_build_spec(territory: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "concept_name": territory["concept_name"],
        "objective": territory["positioning"],
        "target_audience": territory["target_audience"],
        "layout_direction": territory["layout_direction"],
        "content_blocks": [
            "evidence summary",
            "provenance rail",
            "next-action module",
            "approval boundary",
        ],
        "modules": {
            "primary_module": territory["concept_name"],
            "supporting_modules": ["evidence rail", "status strip", "action row"],
        },
        "build_constraints": [
            "no public publish",
            "no paid spend",
            "no client PII",
            "read-only evidence only",
        ],
        "verification": {
            "must_retain_evidence_refs": True,
            "must_retain_target_audience": True,
            "must_retain_differentiator": True,
        },
    }


def _compact_market_refs() -> List[Dict[str, Any]]:
    return [
        {
            "title": "Hermes capability registry",
            "source": "src/lib/hermesCapabilityRegistry.ts",
            "reference": "Creative Studio capability is already partial and read-only.",
        },
        {
            "title": "Alpha marketing asset studio",
            "source": "src/hermes/alpha/marketingAssetStudio.ts",
            "reference": "Draft-only marketing assets already exist.",
        },
        {
            "title": "Open-source scout proof",
            "source": "reports/hermes_modernization/open_source_capability_audit.json",
            "reference": "Public evidence path already proved Nexus-first audit and canonical handoff.",
        },
    ]


def _build_opportunity_input() -> Dict[str, Any]:
    audit = _load_open_source_audit()
    selected = audit["selected_candidate"]
    evidence = {
        "source_id": selected["candidate_id"],
        "source_type": "public_repo_intelligence",
        "classification": "KNOWN",
        "summary": f"{selected['project']} {selected['recommendation']}",
        "retrieved_at": audit["generated_at"],
        "provenance": {
            "source_urls": selected["source_urls"],
            "nexus_audit": audit["nexus_audit"],
        },
    }
    raw = {
        "id": selected["candidate_id"],
        "title": selected["project"],
        "category": "open_source",
        "problem": selected["purpose"],
        "target_customer": "Hermes / Alpha operators",
        "evidence": [evidence],
        "search_demand": selected["search_demand"],
        "social_signal": selected["social_signal"],
        "competitive_signal": selected["competitive_signal"],
        "commercial_intent": selected["commercial_intent"],
        "revenue_model": selected["revenue_model"],
        "startup_cost": selected["startup_cost"],
        "ongoing_cost": selected["ongoing_cost"],
        "difficulty": selected["difficulty"],
        "time_to_test": selected["time_to_test"],
        "risk": selected["risk"],
        "confidence": selected["confidence"],
        "status": "DISCOVERED",
        "recommended_next_action": selected["recommendation_rationale"],
        "source": selected["repository"],
        "source_type": "public_repo_intelligence",
        "retrieved_at": audit["generated_at"],
        "provenance": {
            "source_urls": selected["source_urls"],
            "nexus_state": selected["nexus_state"],
            "existing_owner": selected["existing_owner"],
        },
        "tags": [selected["category"], selected["license"]],
        "source_commit": selected["provenance"]["source_commit"],
        "generated_at": utc_now(),
        "ai_rationale": "",
    }
    canonical = canonicalize_opportunity_record(
        raw,
        source="nexus_creative_lab",
        source_type="public_repo_intelligence",
        retrieved_at=raw["retrieved_at"],
        provenance=raw["provenance"],
    )
    canonical["business_case"] = build_opportunity_business_case(canonical)
    return canonical


def build_creative_pilot(previous_state: Dict[str, Any] | None = None) -> Dict[str, Any]:
    budget = CreativeBudget()
    opportunity = _build_opportunity_input()
    brief = build_creative_brief(opportunity, opportunity["evidence"], _compact_market_refs(), previous_state=previous_state)
    territories = build_creative_territories(brief)
    verification = evaluate_creative_set(territories)
    recommended = max(territories, key=lambda territory: territory["creative_score"])
    build_spec = build_build_spec(recommended)
    ai_calls = 0
    input_text = json.dumps(brief, sort_keys=True, default=str)
    output_text = json.dumps(territories, sort_keys=True, default=str)
    return {
        "ok": True,
        "generated_at": utc_now(),
        "opportunity": opportunity,
        "brief": brief,
        "market_reference_summary": _compact_market_refs(),
        "territories": territories,
        "territory_count": len(territories),
        "recommended_territory": recommended,
        "verification": verification,
        "build_spec": build_spec,
        "ai_calls": ai_calls,
        "zero_token_execution": ai_calls == 0,
        "input_tokens": 0 if ai_calls == 0 else _approx_tokens(input_text),
        "output_tokens": 0 if ai_calls == 0 else _approx_tokens(output_text),
        "estimated_cost_usd": 0.0,
        "estimated_cost_status": "ZERO_TOKEN",
        "budget": {
            "max_ai_calls": budget.max_ai_calls,
            "max_input_tokens": budget.max_input_tokens,
            "max_output_tokens": budget.max_output_tokens,
            "cost_ceiling_usd": budget.cost_ceiling_usd,
            "model_tier": budget.model_tier,
            "explicit_premium_escalation": budget.explicit_premium_escalation,
        },
        "source_commit": opportunity.get("source_commit"),
        "provenance": {
            "opportunity_source": opportunity.get("source"),
            "evidence_count": len(opportunity.get("evidence", [])),
            "source_refs": [ref["source"] for ref in _compact_market_refs()],
        },
        "previous_state": {
            "last_territory_hash": previous_state.get("last_territory_hash") if previous_state else None,
            "last_recommendation": previous_state.get("last_recommendation") if previous_state else None,
        },
        "territory_hash": _hash([territory["concept_name"] for territory in territories]),
    }


def build_creative_lab_report(previous_state: Dict[str, Any] | None = None) -> Dict[str, Any]:
    audit = build_creative_audit()
    pilot = build_creative_pilot(previous_state=previous_state)
    return {
        "generated_at": pilot["generated_at"],
        "skill_only": True,
        "persistent_agents": ["nexus_hermes", "hermes_nova", "alpha"],
        "creative_audit": audit,
        "opportunity": pilot["opportunity"],
        "brief": pilot["brief"],
        "market_reference_summary": pilot["market_reference_summary"],
        "territories": pilot["territories"],
        "territory_count": pilot["territory_count"],
        "recommended_territory": pilot["recommended_territory"],
        "verification": pilot["verification"],
        "build_spec": pilot["build_spec"],
        "ai_calls": pilot["ai_calls"],
        "zero_token_execution": pilot["zero_token_execution"],
        "input_tokens": pilot["input_tokens"],
        "output_tokens": pilot["output_tokens"],
        "estimated_cost_usd": pilot["estimated_cost_usd"],
        "estimated_cost_status": pilot["estimated_cost_status"],
        "source_commit": pilot["source_commit"],
        "provenance": pilot["provenance"],
        "previous_state": pilot["previous_state"],
    }


def write_creative_lab_reports(previous_state: Dict[str, Any] | None = None) -> Dict[str, Any]:
    report = build_creative_lab_report(previous_state=previous_state)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "creative_lab_audit.md").write_text(_render_audit(report["creative_audit"]), encoding="utf-8")
    (REPORT_DIR / "creative_lab.md").write_text(_render_lab(report), encoding="utf-8")
    (REPORT_DIR / "creative_pilot.md").write_text(_render_pilot(report), encoding="utf-8")
    (REPORT_DIR / "creative_benchmark.md").write_text(_render_benchmark(report), encoding="utf-8")
    return report


def run_creative_lab(previous_state: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return write_creative_lab_reports(previous_state=previous_state)


def _render_audit(audit: Sequence[Dict[str, Any]]) -> str:
    lines = [
        "# Creative Lab Audit",
        "",
        "## Existing surfaces",
        "",
        "| Component | Classification | Reason |",
        "|---|---|---|",
    ]
    for row in audit:
        lines.append(f"| {row['component']} | {row['classification']} | {row['reason']} |")
    return "\n".join(lines) + "\n"


def _render_lab(report: Dict[str, Any]) -> str:
    lines = [
        "# Nexus Creative Lab",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Audit outcome",
        "",
        f"- existing reused: {sum(1 for row in report['creative_audit'] if row['classification'] in {'KEEP', 'WRAP', 'MERGE', 'EXTEND'})}",
        f"- extended: {sum(1 for row in report['creative_audit'] if row['classification'] == 'EXTEND')}",
        f"- new: {sum(1 for row in report['creative_audit'] if row['classification'] == 'CREATE_NEW')}",
        "",
        "## Creative Director",
        "",
        f"- skill only: {'PASS' if report['skill_only'] else 'FAIL'}",
        "",
        "## Territories",
        "",
        f"- count: {report['territory_count']}",
        "",
        "| Concept | Score | Hook | CTA | Evidence refs |",
        "|---|---|---|---|---|",
    ]
    for territory in report["territories"]:
        lines.append(
            f"| {territory['concept_name']} | {territory['creative_score']} | {territory['primary_hook']} | {territory['cta']} | {len(territory['evidence_refs'])} |"
        )
    lines.extend(
        [
            "",
            "## Build spec",
            "",
            f"- created: {'yes' if report['build_spec'] else 'no'}",
            f"- recommended territory: {report['recommended_territory']['concept_name']}",
            f"- zero token execution: {'yes' if report['zero_token_execution'] else 'no'}",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_pilot(report: Dict[str, Any]) -> str:
    t = report["recommended_territory"]
    lines = [
        "# Creative Pilot",
        "",
        "## Safe pilot scope",
        "",
        "The pilot used public or governed internal evidence only.",
        "",
        "It did not:",
        "",
        "- build the site",
        "- generate production assets",
        "- publish",
        "- deploy",
        "- spend money",
        "",
        "## Opportunity",
        "",
        f"- id: {report['opportunity']['id']}",
        f"- title: {report['opportunity']['title']}",
        f"- target: {report['opportunity']['target_customer']}",
        "",
        "## Recommended territory",
        "",
        f"- concept: {t['concept_name']}",
        f"- positioning: {t['positioning']}",
        f"- audience: {t['target_audience']}",
        f"- hook: {t['primary_hook']}",
        f"- CTA: {t['cta']}",
        "",
        "## Build spec skeleton",
        "",
        "```json",
        json.dumps(report["build_spec"], indent=2, sort_keys=True),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _render_benchmark(report: Dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Creative Benchmark",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| territories | {report['territory_count']} |",
            f"| ai_calls | {report['ai_calls']} |",
            f"| input_tokens | {report['input_tokens']} |",
            f"| output_tokens | {report['output_tokens']} |",
            f"| estimated_cost_usd | {report['estimated_cost_usd']} |",
            f"| verification | {report['verification']['status']} |",
            f"| build_spec | {'created' if report['build_spec'] else 'missing'} |",
            f"| recommended_territory | {report['recommended_territory']['concept_name']} |",
            "",
            f"Skill file: {SKILL_PATH.relative_to(ROOT)}",
        ]
    ) + "\n"
