"""Reusable Prompt Architect contracts and bounded instruction construction."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

GENERATOR_PROFILES = {
    "IMAGE_GENERATOR": "scene, subject, composition, hierarchy, camera, light, materials, color, typography limits, aspect ratio, negative constraints",
    "VIDEO_GENERATOR": "shot progression, timing, continuity, camera movement, transitions, typography limits, audio and format boundaries",
    "WEB_DESIGN_EXECUTOR": "page story, hero and section hierarchy, visual rhythm, asset placement, responsive intent, interaction intent",
    "COPY_GENERATOR": "hook, message hierarchy, tone, persuasion role, CTA role, proof boundary, prohibited claims, channel length",
}

PROMPT_FIELDS = (
    "prompt_architect_version", "source_creative_direction_id", "source_creative_direction_sha256",
    "target_generator_type", "creative_intent", "human_insight", "subject", "scene",
    "composition", "visual_hierarchy", "camera_direction", "lighting", "materials_texture",
    "color_relationship", "typography_treatment", "emotional_tone", "visual_metaphor",
    "brand_relationship", "conversion_role", "negative_constraints", "channel_requirements",
    "aspect_ratio", "continuity_requirements", "final_execution_prompt",
)
RESPONSE_PROMPT_FIELDS = (
    "target_emotion", "target_thought", "desired_action", "hook",
    "first_1_second_event", "first_3_second_event", "story_arc",
    "core_tension", "curiosity_gap", "payoff", "cta_trigger",
)

META_MINIMUM_CONTRACT_FIELDS = (
    "brand", "audience", "offer", "customer_problem_or_desire",
    "campaign_objective", "source_material", "verified_facts",
    "prohibited_or_unverified_claims", "requested_deliverables",
    "tool_and_budget_boundaries",
)

OPEN_IDEATION_MODE = "OPEN_IDEATION_MODE"
DIRECTED_PRODUCTION_MODE = "DIRECTED_PRODUCTION_MODE"

# These keys represent solutions, not business/source truth. They are rejected
# from the open contract so a prior campaign cannot leak through a generic
# source_material dictionary.
PRIOR_CREATIVE_SOLUTION_KEYS = frozenset({
    "creative_direction", "creative_handoff", "selected_concept", "prior_concept",
    "prior_campaign", "response_strategy", "art_direction", "prompt_architect",
    "creative_territories", "hook", "visual_metaphor", "emotional_arc",
    "shot_sequence", "funnel_structure", "cta_strategy", "campaign_world",
})


def sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def source_direction_id(direction: Mapping[str, Any]) -> str:
    return str(direction.get("territory_id") or direction.get("concept_id") or direction.get("territory_name") or "UNKNOWN_SOURCE_DIRECTION")


def build_instruction(direction: Mapping[str, Any], brand: Mapping[str, Any], channel: Mapping[str, Any], generator_type: str) -> str:
    if generator_type not in GENERATOR_PROFILES:
        raise ValueError(f"unsupported_generator_type:{generator_type}")
    response = direction.get("response_strategy")
    requested_fields = PROMPT_FIELDS + (RESPONSE_PROMPT_FIELDS if isinstance(response, Mapping) else ())
    response_clause = ""
    if isinstance(response, Mapping):
        response_clause = " For this response-driven handoff, include these additional top-level fields in the returned JSON and preserve them exactly in meaning: " + ", ".join(RESPONSE_PROMPT_FIELDS) + ". Do not omit them. RESPONSE_STRATEGY=" + json.dumps(response, ensure_ascii=False)
    return (
        "Translate the approved Creative Direction into one structured Prompt Architect artifact. "
        "Preserve its meaning; do not invent a concept, section, copy, palette, typography, CTA, or visual metaphor. "
        "Use UNKNOWN_FROM_APPROVED_DIRECTION where the source is silent. Return JSON only with fields: "
        + ", ".join(requested_fields) + ". "
        + f"Target generator profile: {generator_type}. Profile requirements: {GENERATOR_PROFILES[generator_type]}. "
        + "Include explicit anti-generic and compliance-safe negative constraints. " + response_clause + " "
        + f"APPROVED_CREATIVE_DIRECTION={json.dumps(direction, ensure_ascii=False)} "
        + f"BRAND_CONSTRAINTS={json.dumps(brand, ensure_ascii=False)} "
        + f"CHANNEL_REQUIREMENTS={json.dumps(channel, ensure_ascii=False)}"
    )


def build_open_meta_prompt(
    *,
    brand: Mapping[str, Any],
    audience: str,
    offer: str,
    customer_problem_or_desire: str,
    campaign_objective: str,
    source_material: Mapping[str, Any],
    verified_facts: list[str],
    prohibited_or_unverified_claims: list[str],
    requested_deliverables: list[str],
    tool_and_budget_boundaries: list[str],
    optional_creative_guidance: Mapping[str, Any] | None = None,
    mode: str = OPEN_IDEATION_MODE,
) -> str:
    """Build a mode-explicit Meta contract without silently supplying creative solutions."""
    if mode not in {OPEN_IDEATION_MODE, DIRECTED_PRODUCTION_MODE}:
        raise ValueError(f"unsupported_meta_creative_mode:{mode}")
    if mode == OPEN_IDEATION_MODE:
        leaked = sorted(set(source_material).intersection(PRIOR_CREATIVE_SOLUTION_KEYS))
        if leaked:
            raise ValueError("open_ideation_prior_creative_solution_leak:" + ",".join(leaked))
        if optional_creative_guidance:
            raise ValueError("open_ideation_optional_guidance_requires_explicit_directed_mode")
    payload = {
        "BRAND": brand,
        "AUDIENCE": audience,
        "OFFER": offer,
        "CUSTOMER_PROBLEM_OR_DESIRE": customer_problem_or_desire,
        "CAMPAIGN_OBJECTIVE": campaign_objective,
        "SOURCE_MATERIAL": source_material,
        "VERIFIED_FACTS": verified_facts,
        "PROHIBITED_OR_UNVERIFIED_CLAIMS": prohibited_or_unverified_claims,
        "REQUESTED_DELIVERABLES": requested_deliverables,
        "TOOL_AND_BUDGET_BOUNDARIES": tool_and_budget_boundaries,
    }
    if mode == OPEN_IDEATION_MODE:
        instruction = (
            "You are the primary creative studio for this campaign. Create the strongest "
            "original campaign concepts you can from the supplied business context and "
            "accessible source material. You are free to determine the concept, story, "
            "emotion, visual language, headline, composition, pacing, sound, funnel "
            "structure, copy approach, and creative treatment. Do not inherit or preserve "
            "any previous campaign concept, hook, metaphor, emotional arc, scene sequence, "
            "funnel structure, or CTA treatment. Do not merely describe how assets could be "
            "made. For this bounded ideation step, originate three materially different "
            "concepts for review; do not create final media before a concept is selected. "
            "Remain truthful to verified facts and do not invent restricted claims. This is "
            "internal review only: do not publish, spend, or submit an approval decision."
        )
    else:
        instruction = (
            "You are the primary creative studio for this directed campaign. Execute the "
            "explicitly selected creative direction supplied in the contract using your "
            "available creative capabilities. Preserve the selected direction while making "
            "the requested assets coherent. Remain truthful to verified facts and do not "
            "invent restricted claims. This is internal review only: do not publish, spend, "
            "or submit an approval decision."
        )
    prompt = (
        f"MODE={mode}\n"
        + instruction
        + "\n\n"
        "MINIMUM_CAMPAIGN_CONTRACT=\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )
    if optional_creative_guidance and mode == DIRECTED_PRODUCTION_MODE:
        prompt += (
            "\n\nOPTIONAL_CREATIVE_GUIDANCE (suggestions only; do not treat as "
            "requirements and feel free to reject them):\n"
            + json.dumps(optional_creative_guidance, ensure_ascii=False, indent=2)
        )
    return prompt


def valid_artifact(value: Any) -> bool:
    return isinstance(value, dict) and all(field in value for field in PROMPT_FIELDS)
