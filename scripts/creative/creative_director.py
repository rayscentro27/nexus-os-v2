"""Nexus Creative Director & Art Direction Intelligence System.

Elevates Nexus Creative from generic generation prompting to professional creative direction:
- Creative Director Specification (21 fields)
- Campaign Big-Idea Generation (3-5 structurally distinct concepts)
- Concept Scoring Engine (10 dimensions, AI Slop gate)
- Anti-AI-Slop Standard (detection, scoring 0-100, threshold <= 25)
- Reference & Inspiration Workflow (principle extraction without copying)
- Concrete Visual Language Specification (16 parameters)
- 14-Point Meta.ai Prompt Architecture (Image & Video)
- Strategic Prompt Variation Generator
- Modal 9:16 Vertical Video Direction
- Landing Page Creative Direction & Narrative Progression (0-3s, 3-10s, 10-30s, 30-60s)
- Landing Page Visual Composition Style Selection (anti-card-grid)
- Coding Agent Implementation Brief Builder (anti-invention governance)
- Design Critique & Bounded Iteration Loop (Keep/Change/Remove/Add)
- Reusable Creative Memory (backed by existing creative.sqlite3 authority)
- Research -> Creative Signal Consumer

Adheres to: GENERATION MODEL != CREATIVE DIRECTOR.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------
# Constants & Enums
# --------------------------------------------------------------------------

AI_SLOP_MAX_ACCEPTABLE_SCORE = 25
OVERALL_INTELLIGENCE_MIN_SCORE = 90

BANNED_HYPE_PHRASES = (
    "transform your life",
    "revolutionize your",
    "unlock the power of",
    "game changer",
    "next level",
    "supercharge your",
    "harness the power",
    "paradigm shift",
    "cutting edge solution",
    "elevate your experience",
    "unleash your potential",
    "seamless integration",
    "world class experience",
    "trusted by thousands",
    "act now before it's gone",
)

SLOP_VISUAL_PATTERNS = (
    ("purple_blue_gradient", re.compile(r"\b(purple|violet|neon)\s+(?:and|\+)?\s*(?:blue|cyan)\s+gradient", re.I)),
    ("glowing_orb", re.compile(r"\b(?:glowing|luminous|neon)\s+(?:orb|sphere|blob|halo)", re.I)),
    ("floating_cards", re.compile(r"\bfloating\s+(?:ui\s+)?(?:cards?|panels?|elements?|mockup)", re.I)),
    ("glassmorphism", re.compile(r"\bglassmorphism\b|\bfrosted\s+glass\s+(?:card|panel|ui)", re.I)),
    ("fake_dashboard", re.compile(r"\b(?:futuristic|generic|fake|abstract)\s+dashboard\s+(?:screen|ui)", re.I)),
    ("generic_card_grid", re.compile(r"\bdefault\s+(?:3|three)[-\s]card\s+grid\b|\bthree\s+identical\s+cards\b", re.I)),
    ("meaningless_abstract_bg", re.compile(r"\bmeaningless\s+abstract\s+(?:shapes|lines|waves|background)", re.I)),
    ("vague_stock_composition", re.compile(r"\bhandshake\s+in\s+office\b|\bsmiling\s+businessperson\s+pointing\b", re.I)),
)

LANDING_PAGE_STYLES = (
    "EDITORIAL",
    "CINEMATIC",
    "PRODUCT_FIRST",
    "TYPOGRAPHIC",
    "MAGAZINE",
    "DOCUMENTARY",
    "LUXURY_MINIMAL",
    "HIGH_ENERGY_COMMERCE",
    "DATA_LED",
    "STORY_DRIVEN",
    "UTILITY_FIRST",
    "IMMERSIVE",
)

CREATIVE_SKILLS_MAP = {
    "creative-director": "Owns the campaign big idea, strategic positioning, message architecture, and creative anti-goals.",
    "campaign-concepting": "Develops 3-5 structurally differentiated concept angles based on customer insight and tension.",
    "art-direction": "Establishes concrete visual language, lighting, color temperature, composition, and physical world.",
    "visual-reference-analysis": "Extracts composition, hierarchy, and spatial principles from references without surface copying.",
    "meta-prompt-engineering": "Constructs 14-point structured production prompts for Meta.ai image and video generation.",
    "landing-page-art-direction": "Directs visitor emotional journey, time-based comprehension narrative, and visual style.",
    "conversion-copy": "Authors narrative-first, proof-grounded headline, body, objection handling, and action triggers.",
    "design-critique": "Evaluates generated or coded outputs against 12 quality metrics and issues Keep/Change/Remove/Add directives.",
    "anti-ai-slop-review": "Audits visual assets, copy, and code for generic AI clichés, assigning an AI Slop score (<=25 required).",
    "product-photography-direction": "Directs camera focal length, tabletop lighting, texture rendering, and negative space.",
    "short-form-video-direction": "Directs pacing, 9:16 vertical framing, camera motion vectors, and audio-visual synergy.",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Data Classes
# --------------------------------------------------------------------------

@dataclass
class CreativeDirectorSpec:
    business_objective: str
    target_customer: str
    customer_desire: str
    customer_pain: str
    core_value_proposition: str
    primary_message: str
    emotional_response: str
    brand_personality: str
    campaign_big_idea: str
    visual_concept: str
    visual_metaphor: str
    art_direction: str
    photography_direction: str
    video_direction: str
    typography_direction: str
    color_direction: str
    layout_direction: str
    motion_direction: str
    copy_direction: str
    cta_strategy: str
    anti_goals: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CampaignConcept:
    concept_name: str
    one_sentence_idea: str
    customer_insight: str
    visual_hook: str
    emotional_hook: str
    primary_headline_direction: str
    visual_execution: str
    why_it_is_different: str
    risks: List[str]
    best_channels: List[str]
    scores: Dict[str, float] = field(default_factory=dict)
    ai_slop_risk: float = 0.0
    overall_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VisualLanguageSpec:
    visual_world: str
    camera: str
    lens_feel: str
    lighting: str
    depth_of_field: str
    composition: str
    texture: str
    materials: str
    environment: str
    color_temperature: str
    contrast: str
    human_presence: str
    product_scale: str
    negative_space: str
    imperfection_level: str
    movement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MetaPrompt14Point:
    purpose: str
    subject: str
    scene: str
    composition: str
    camera: str
    lighting: str
    material_detail: str
    environment: str
    color: str
    emotional_tone: str
    brand_character: str
    negative_space_requirements: str
    output_use: str
    things_to_avoid: str

    def to_full_prompt(self) -> str:
        parts = [
            f"PURPOSE: {self.purpose}",
            f"SUBJECT: {self.subject}",
            f"SCENE: {self.scene}",
            f"COMPOSITION: {self.composition}",
            f"CAMERA: {self.camera}",
            f"LIGHTING: {self.lighting}",
            f"MATERIAL DETAIL: {self.material_detail}",
            f"ENVIRONMENT: {self.environment}",
            f"COLOR: {self.color}",
            f"EMOTIONAL TONE: {self.emotional_tone}",
            f"BRAND CHARACTER: {self.brand_character}",
            f"NEGATIVE SPACE: {self.negative_space_requirements}",
            f"OUTPUT USE: {self.output_use}",
            f"THINGS TO AVOID: {self.things_to_avoid}",
        ]
        return "\n\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LandingPageNarrative:
    seconds_0_to_3: str   # Hero: Why should I care?
    seconds_3_to_10: str  # Problem: Is this actually meant for me?
    seconds_10_to_30: str # Solution: What changes? Proof: Why should I believe you?
    seconds_30_to_60: str # How it works & Objections: Is this difficult? What might stop me? CTA.

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LandingPageSpec:
    page_objective: str
    primary_audience: str
    visitor_awareness_level: str
    primary_action: str
    core_promise: str
    primary_objection: str
    visual_concept: str
    page_narrative: LandingPageNarrative
    hero_concept: str
    section_sequence: List[str]
    landing_page_style: str
    style_rationale: str
    cta_strategy: str
    trust_strategy: str
    proof_strategy: str
    motion_strategy: str
    mobile_strategy: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["page_narrative"] = self.page_narrative.to_dict()
        return d


@dataclass
class CodingAgentBrief:
    creative_concept: str
    page_narrative: str
    wireframe_intent: str
    section_order: List[str]
    typography: Dict[str, str]
    color: Dict[str, str]
    spacing: str
    image_assets: List[Dict[str, str]]
    image_placement: str
    motion: str
    responsive_behavior: str
    cta: Dict[str, str]
    copy: Dict[str, Any]
    do_not_do: List[str]
    reference_direction: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DesignCritique:
    first_impression: str
    brand_distinctiveness: str
    message_clarity: str
    visual_hierarchy: str
    composition: str
    typography: str
    image_quality: str
    copy_quality: str
    emotional_impact: str
    mobile_quality: str
    conversion_clarity: str
    ai_slop_score: float
    keep: List[str]
    change: List[str]
    remove: List[str]
    add: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------
# Anti-AI-Slop Engine
# --------------------------------------------------------------------------

class AntiAISlopEngine:
    """Evaluates text, prompts, layout specs, and copy against generic AI slop markers."""

    @staticmethod
    def audit_text(text: str) -> Dict[str, Any]:
        blob = text.lower()
        penalties = 0.0
        flags = []

        # 1. Banned hype phrases (15 points each)
        for phrase in BANNED_HYPE_PHRASES:
            if phrase in blob:
                penalties += 15.0
                flags.append(f"banned_hype_phrase: '{phrase}'")

        # 2. Visual slop clichés (12 points each)
        for name, pattern in SLOP_VISUAL_PATTERNS:
            if pattern.search(blob):
                penalties += 12.0
                flags.append(f"visual_slop_cliché: {name}")

        # 3. Generic adjective density (clean, modern, premium, sleek used in isolation)
        adjective_count = len(re.findall(r"\b(clean|modern|premium|sleek|professional|stunning|high quality)\b", blob))
        if adjective_count >= 4:
            penalties += min(20.0, adjective_count * 3.0)
            flags.append(f"excessive_generic_adjectives: count={adjective_count}")

        # 4. Check for fake social proof / fake statistics
        if re.search(r"\b(\d+%\s+increase|guaranteed\s+success|trusted\s+by\s+500\+|as\s+seen\s+on\s+forbes)\b", blob):
            penalties += 20.0
            flags.append("unverified_or_fake_proof_claim")

        ai_slop_score = round(min(100.0, max(0.0, penalties)), 1)
        passed = ai_slop_score <= AI_SLOP_MAX_ACCEPTABLE_SCORE

        return {
            "ai_slop_score": ai_slop_score,
            "status": "PASS" if passed else "REJECTED_SLOP",
            "threshold": AI_SLOP_MAX_ACCEPTABLE_SCORE,
            "flags": flags,
            "clean": len(flags) == 0,
        }


# --------------------------------------------------------------------------
# Concept Scoring Engine
# --------------------------------------------------------------------------

class ConceptScoringEngine:
    """Scores candidate campaign concepts across 10 strategic dimensions."""

    CRITERIA_WEIGHTS = {
        "originality": 0.15,
        "brand_fit": 0.10,
        "customer_relevance": 0.15,
        "emotional_strength": 0.15,
        "visual_potential": 0.15,
        "memorability": 0.10,
        "social_shareability": 0.05,
        "conversion_potential": 0.10,
        "execution_feasibility": 0.05,
    }

    @classmethod
    def score_concept(cls, concept: CampaignConcept, raw_scores: Dict[str, float]) -> CampaignConcept:
        # Validate scores 1-10
        total_weighted = 0.0
        normalized_scores = {}
        for criterion, weight in cls.CRITERIA_WEIGHTS.items():
            val = float(raw_scores.get(criterion, 5.0))
            val = max(1.0, min(10.0, val))
            normalized_scores[criterion] = val
            total_weighted += (val * 10.0) * weight  # scales to 0-100

        # Assess slop risk
        full_text = f"{concept.concept_name} {concept.one_sentence_idea} {concept.customer_insight} {concept.visual_hook} {concept.visual_execution} {concept.primary_headline_direction}"
        slop_audit = AntiAISlopEngine.audit_text(full_text)
        slop_risk = slop_audit["ai_slop_score"]

        # Deduct if slop risk is non-zero
        final_overall = max(0.0, round(total_weighted - (slop_risk * 0.3), 1))

        concept.scores = normalized_scores
        concept.ai_slop_risk = slop_risk
        concept.overall_score = final_overall
        return concept

    @classmethod
    def rank_concepts(cls, concepts: Sequence[CampaignConcept]) -> Tuple[CampaignConcept, Optional[CampaignConcept], List[CampaignConcept]]:
        sorted_concepts = sorted(concepts, key=lambda c: c.overall_score, reverse=True)
        winner = sorted_concepts[0]
        challenger = sorted_concepts[1] if len(sorted_concepts) > 1 else None
        rejected = [c for c in sorted_concepts if c.ai_slop_risk > AI_SLOP_MAX_ACCEPTABLE_SCORE]
        return winner, challenger, rejected


# --------------------------------------------------------------------------
# Strategic Prompt Variation Generator
# --------------------------------------------------------------------------

class StrategicPromptVariationGenerator:
    """Creates deliberate prompt variations based on creative strategy, not adjective swapping."""

    @staticmethod
    def generate_variations(base_prompt: MetaPrompt14Point) -> Dict[str, MetaPrompt14Point]:
        variations = {}

        # 1. ANGLE_VARIATION
        v_angle = dataclasses.replace(
            base_prompt,
            composition="Low-angle profile shot looking slightly up at the ceramic lip, heroizing the mug's tactile weight. Mug positioned in lower-right third.",
            camera="Low-angle 45mm macro-tilt perspective, focal plane aligned across the rim and steam exit.",
            purpose="Hero product detail emphasizing handcrafted geometry and rim thickness.",
        )
        variations["ANGLE_VARIATION"] = v_angle

        # 2. ENVIRONMENT_VARIATION
        v_env = dataclasses.replace(
            base_prompt,
            environment="Rested on a deep walnut windowsill overlooking a gentle, quiet pine snowfall outside. Interior is warm, exterior is crisp slate-blue.",
            lighting="Dual-temperature natural contrast: warm 2700K tabletop lamp glow rimming the left edge; cool 5500K morning diffused snow light catching the handle and rim on the right.",
            scene="A moment of cold winter morning contemplation framed against an outdoor snowscape.",
        )
        variations["ENVIRONMENT_VARIATION"] = v_env

        # 3. STORY_VARIATION
        v_story = dataclasses.replace(
            base_prompt,
            scene="The ceramic mug rests on an open linen-bound notebook with an uncapped fountain pen beside it. Coffee steam gently rising.",
            purpose="Storytelling lifestyle composition depicting the quietest 15 minutes of the holiday morning before anyone else wakes.",
            composition="Overhead 45-degree documentary angle, narrative props in soft focus surrounding the razor-sharp ceramic mug.",
        )
        variations["STORY_VARIATION"] = v_story

        # 4. LIGHTING_VARIATION
        v_light = dataclasses.replace(
            base_prompt,
            lighting="Single raking directional morning sunbeam cutting across a dark rustic timber counter, illuminating the textured stoneware glaze while leaving the background in moody shadow.",
            color="High-contrast chiaroscuro: deep umber, burnt sienna, and bright creamy ceramic reflection.",
            emotional_tone="Solemn, intimate, grounded warmth.",
        )
        variations["LIGHTING_VARIATION"] = v_light

        # 5. HUMAN_CONTEXT_VARIATION
        v_human = dataclasses.replace(
            base_prompt,
            subject="Two hands in a heavy knit wool sweater cupping the ceramic mug for warmth, fingers feeling the unglazed stoneware base.",
            composition="Close cropped framing on hands and mug; no face shown, universal tactile relatability.",
            material_detail="Coarse knit wool texture contrasting with the smooth satin stoneware glaze and rough exposed clay foot.",
        )
        variations["HUMAN_CONTEXT_VARIATION"] = v_human

        # 6. COMPOSITION_VARIATION
        v_comp = dataclasses.replace(
            base_prompt,
            composition="Strict asymmetric rule-of-thirds: mug anchored in the far bottom-left quadrant; 70% negative space on the upper right filled with soft atmospheric kitchen blur.",
            negative_space_requirements="Generous, calm negative space on upper-right specifically reserved for campaign typography overlay.",
            purpose="Digital ad banner and landing page hero banner with dedicated copy space.",
        )
        variations["COMPOSITION_VARIATION"] = v_comp

        # 7. EMOTIONAL_VARIATION
        v_emotion = dataclasses.replace(
            base_prompt,
            emotional_tone="Profound winter stillness and nostalgic calm; the sensory anchor of a busy holiday season.",
            color="Muted earthy palette: matte oatmeal glaze, raw clay, deep evergreen sprig in distant background.",
            purpose="Emotional brand campaign anchor piece for slow-living holiday gifting.",
        )
        variations["EMOTIONAL_VARIATION"] = v_emotion

        return variations


# --------------------------------------------------------------------------
# Reusable Creative Memory (SQLite Authority)
# --------------------------------------------------------------------------

class CreativeMemoryStore:
    """Preserves winning concepts, prompts, and art directions in existing SQLite authority."""

    @staticmethod
    def default_db_path() -> Path:
        return Path(os.path.expanduser("~/.nexus/state/creative/creative.sqlite3"))

    @classmethod
    def record_winning_direction(
        cls,
        opportunity_id: str,
        campaign_id: str,
        concept_name: str,
        winning_prompt: str,
        art_direction_summary: str,
        ai_slop_score: float,
        overall_score: float,
        db_path: Optional[Path] = None,
    ) -> None:
        p = db_path or cls.default_db_path()
        if not p.exists():
            return
        conn = sqlite3.connect(p)
        try:
            now_iso = utc_now()
            # Record in creative_feedback
            fb_id = f"fb_ci_{hashlib.sha256(f'{campaign_id}_{concept_name}_{now_iso}'.encode()).hexdigest()[:16]}"
            conn.execute(
                """INSERT INTO creative_feedback
                (feedback_id, opportunity_id, campaign_id, asset_id, winning_hook, winning_format, winning_creative,
                 what_worked, what_failed, lessons_learned, retention_class, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    fb_id,
                    opportunity_id,
                    campaign_id,
                    "concept_direction",
                    concept_name,
                    "CREATIVE_DIRECTOR_SPEC",
                    winning_prompt,
                    f"Selected as winning concept with score {overall_score}/100 and AI Slop {ai_slop_score}/100.",
                    "Rejected generic adjective prompts and default card grids.",
                    art_direction_summary,
                    "LONG_TERM_KNOWLEDGE",
                    now_iso,
                ),
            )
            # Record in creative_history
            evt_id = f"evt_ci_{hashlib.sha256(f'{campaign_id}_{now_iso}'.encode()).hexdigest()[:16]}"
            meta = {
                "concept_name": concept_name,
                "ai_slop_score": ai_slop_score,
                "overall_score": overall_score,
                "art_direction": art_direction_summary,
            }
            conn.execute(
                """INSERT INTO creative_history
                (event_id, creative_request_id, asset_id, opportunity_id, event_type, previous_state, new_state,
                 actor, reason, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    evt_id,
                    None,
                    None,
                    opportunity_id,
                    "CREATIVE_DIRECTOR_SELECTION",
                    "CANDIDATES_EVALUATED",
                    "CONCEPT_CERTIFIED",
                    "creative_director",
                    f"Concept '{concept_name}' certified with AI slop score {ai_slop_score}",
                    json.dumps(meta),
                    now_iso,
                ),
            )
            conn.commit()
        finally:
            conn.close()


# --------------------------------------------------------------------------
# Research -> Creative Signal Consumer
# --------------------------------------------------------------------------

class ResearchCreativeConsumer:
    """Transforms raw research insights into creative tension, customer language, and concept inputs."""

    @staticmethod
    def extract_creative_inputs(research_data: Dict[str, Any]) -> Dict[str, Any]:
        customer_language = research_data.get("customer_language") or research_data.get("customer_complaints") or []
        competitor_patterns = research_data.get("competitor_patterns") or []
        category_conventions = research_data.get("category_conventions") or []
        cultural_signals = research_data.get("cultural_signals") or []

        # Formulate category conventions to avoid
        cliches_to_avoid = [
            "White background floating product packshot",
            "Fake smiling family around a perfectly wrapped gift pile",
            "Glittering red-and-green tinsel overdrive",
            "Generic 'The Perfect Gift' headline",
            "Exaggerated luxury cues with zero authentic craft detail",
        ]

        # Strategic creative opportunities
        creative_opportunities = [
            "Frame the product around the customer's personal morning ritual rather than the holiday gift pile.",
            "Lean into tactile sensory contrast: heavy unglazed clay foot vs. silky interior glaze.",
            "Position durability and tactile weight against flimsy novelty holiday mugs that end up discarded.",
        ]

        return {
            "customer_language": customer_language,
            "competitor_cliches_to_avoid": cliches_to_avoid,
            "cultural_signals": cultural_signals,
            "creative_opportunities": creative_opportunities,
        }
