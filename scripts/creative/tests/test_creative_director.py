"""Contract tests for Nexus Creative Director & Art Direction Intelligence System."""
from __future__ import annotations

import sqlite3
from pathlib import Path
import pytest

from scripts.creative.creative_director import (
    AI_SLOP_MAX_ACCEPTABLE_SCORE,
    AntiAISlopEngine,
    CampaignConcept,
    CodingAgentBrief,
    ConceptScoringEngine,
    CreativeDirectorSpec,
    CreativeMemoryStore,
    DesignCritique,
    LandingPageNarrative,
    LandingPageSpec,
    MetaPrompt14Point,
    ResearchCreativeConsumer,
    StrategicPromptVariationGenerator,
    VisualLanguageSpec,
)


def test_anti_ai_slop_engine_detects_slop():
    slop_text = (
        "Revolutionize your morning with this game changer! "
        "Modern clean sleek premium floating ui cards with a purple blue gradient "
        "and glowing orbs on frosted glass glassmorphism. "
        "Guaranteed success with 500% increase in happiness!"
    )
    audit = AntiAISlopEngine.audit_text(slop_text)
    assert audit["status"] == "REJECTED_SLOP"
    assert audit["ai_slop_score"] > AI_SLOP_MAX_ACCEPTABLE_SCORE
    assert any("banned_hype_phrase" in f for f in audit["flags"])
    assert any("visual_slop_cliché" in f for f in audit["flags"])
    assert any("unverified_or_fake_proof_claim" in f for f in audit["flags"])


def test_anti_ai_slop_engine_passes_clean_art_direction():
    clean_direction = (
        "Tactile stoneware ceramic mug resting on dark walnut kitchen counter. "
        "Natural morning window lighting at 3200K, raking across the exposed coarse clay foot. "
        "Mug anchored in lower-left third with quiet negative space on upper right. "
        "Subtle steam rising in soft morning stillness."
    )
    audit = AntiAISlopEngine.audit_text(clean_direction)
    assert audit["status"] == "PASS"
    assert audit["ai_slop_score"] <= AI_SLOP_MAX_ACCEPTABLE_SCORE
    assert audit["clean"] is True
    assert len(audit["flags"]) == 0


def test_concept_scoring_and_ranking():
    c1 = CampaignConcept(
        concept_name="The 6:12 AM Quiet Ritual",
        one_sentence_idea="The mug for the 15 uninterrupted minutes before the holiday house wakes up.",
        customer_insight="Holiday mornings are chaotic; true luxury is the quiet sensory grounding before the noise begins.",
        visual_hook="Close-up tabletop shot of steam catching raking early morning light on raw ceramic clay.",
        emotional_hook="Solitude, calm presence, and tactile grounding.",
        primary_headline_direction="The only fifteen minutes that belong entirely to you.",
        visual_execution="Dark walnut tabletop, warm 2800K directional light, linen runner, matte oatmeal glaze.",
        why_it_is_different="Refuses cheerful holiday clutter in favor of intimate, peaceful personal sanctuary.",
        risks=["May feel too quiet if contrast is too low."],
        best_channels=["Meta Feed", "Instagram Stories", "Direct Landing Page"],
    )

    c2 = CampaignConcept(
        concept_name="The Mug That Refuses The Cabinet",
        one_sentence_idea="Handcrafted stoneware so heavy and sculptural it earns a permanent place beside the espresso machine.",
        customer_insight="People have 20 mugs in cabinets but reach for the exact same heavy, comforting one every morning.",
        visual_hook="Countertop presence: solitary stoneware mug resting beside polished metal espresso tamper.",
        emotional_hook="Permanent domestic belonging and quiet craft pride.",
        primary_headline_direction="You will never put it back in the cupboard.",
        visual_execution="Butcher block counter, dramatic chiaroscuro side-lighting, tactile stone texture.",
        why_it_is_different="Focuses on countertop permanence and everyday obsession rather than festive novelty.",
        risks=["Must not read as kitchen clutter."],
        best_channels=["Meta Feed", "Pinterest", "Product Landing Page"],
    )

    c3 = CampaignConcept(
        concept_name="Hands Warm First",
        one_sentence_idea="A thick-walled ceramic vessel engineered to hold thermal warmth against cold fingers.",
        customer_insight="In winter, holding a warm cup is a physical source of comfort before taking the first sip.",
        visual_hook="Both hands wrapped completely around the thick unglazed base on a snowy morning.",
        emotional_hook="Deep physical comfort and sensory warmth.",
        primary_headline_direction="Warm your hands before you speak a word.",
        visual_execution="Wool sweater cuffs, windowsill, frosty pine trees blurred outside.",
        why_it_is_different="Positions the ceramic as a thermal tactile instrument rather than a decorative novelty.",
        risks=["Hands might distract from mug silhouette if improperly cropped."],
        best_channels=["Instagram Reels", "Meta Video", "TikTok"],
    )

    scored_c1 = ConceptScoringEngine.score_concept(c1, {
        "originality": 9.5, "brand_fit": 9.2, "customer_relevance": 9.4, "emotional_strength": 9.6,
        "visual_potential": 9.5, "memorability": 9.0, "social_shareability": 8.5,
        "conversion_potential": 9.2, "execution_feasibility": 9.5,
    })
    scored_c2 = ConceptScoringEngine.score_concept(c2, {
        "originality": 8.8, "brand_fit": 8.9, "customer_relevance": 9.0, "emotional_strength": 8.5,
        "visual_potential": 8.8, "memorability": 8.7, "social_shareability": 8.0,
        "conversion_potential": 8.9, "execution_feasibility": 9.0,
    })
    scored_c3 = ConceptScoringEngine.score_concept(c3, {
        "originality": 8.5, "brand_fit": 8.8, "customer_relevance": 8.9, "emotional_strength": 8.8,
        "visual_potential": 8.7, "memorability": 8.2, "social_shareability": 8.3,
        "conversion_potential": 8.6, "execution_feasibility": 9.0,
    })

    winner, challenger, rejected = ConceptScoringEngine.rank_concepts([scored_c1, scored_c2, scored_c3])
    assert winner.concept_name == "The 6:12 AM Quiet Ritual"
    assert challenger.concept_name == "The Mug That Refuses The Cabinet"
    assert len(rejected) == 0
    assert winner.overall_score >= 90.0
    assert winner.ai_slop_risk <= AI_SLOP_MAX_ACCEPTABLE_SCORE


def test_strategic_prompt_variations():
    base = MetaPrompt14Point(
        purpose="Luxury ecommerce hero image for holiday quiet ritual campaign.",
        subject="Single handcrafted stoneware ceramic mug with subtle oatmeal glaze and raw unglazed clay foot.",
        scene="Tabletop morning quiet scene in a serene kitchen before sunrise.",
        composition="Mug anchored in lower-left third; generous negative space on upper-right for typography.",
        camera="Natural 50mm perspective, eye-level with the rim, shallow depth of field (f/2.8).",
        lighting="Soft 2800K directional morning side-light casting gentle elongated shadow to the right.",
        material_detail="Matte eggshell glaze with micro-speckling, smooth satin rim, tactile porous base.",
        environment="Solid dark walnut counter, faint warm kitchen blur in deep background, no holiday clutter.",
        color="Muted earthy palette: charcoal, deep walnut brown, oatmeal cream, warm amber highlights.",
        emotional_tone="Intimate, tranquil, grounded, mindful stillness.",
        brand_character="Quiet luxury, artisanal craft integrity, anti-disposable permanence.",
        negative_space_requirements="Upper-right 40% area clear of high-contrast objects for copy placement.",
        output_use="High-resolution hero campaign banner and Meta ad asset.",
        things_to_avoid="Garish red/green holiday tinsel, cartoon steam, shiny plastic glaze, floating graphics.",
    )

    variations = StrategicPromptVariationGenerator.generate_variations(base)
    assert len(variations) == 7
    expected_keys = {
        "ANGLE_VARIATION", "ENVIRONMENT_VARIATION", "STORY_VARIATION",
        "LIGHTING_VARIATION", "HUMAN_CONTEXT_VARIATION", "COMPOSITION_VARIATION",
        "EMOTIONAL_VARIATION",
    }
    assert set(variations.keys()) == expected_keys

    # Check each variation has deliberate changes
    assert "macro-tilt" in variations["ANGLE_VARIATION"].camera
    assert "windowsill" in variations["ENVIRONMENT_VARIATION"].environment
    assert "notebook" in variations["STORY_VARIATION"].scene
    assert "chiaroscuro" in variations["LIGHTING_VARIATION"].color
    assert "Two hands" in variations["HUMAN_CONTEXT_VARIATION"].subject
    assert "70% negative space" in variations["COMPOSITION_VARIATION"].composition
    assert "Profound winter stillness" in variations["EMOTIONAL_VARIATION"].emotional_tone


def test_creative_memory_store_integration(tmp_path: Path):
    db_file = tmp_path / "test_creative.sqlite3"
    conn = sqlite3.connect(db_file)
    conn.execute("""
        CREATE TABLE creative_feedback (
            feedback_id TEXT PRIMARY KEY, opportunity_id TEXT, campaign_id TEXT, asset_id TEXT,
            winning_hook TEXT, winning_format TEXT, winning_creative TEXT, ctr REAL, conversion_rate REAL,
            revenue_attribution REAL, customer_response TEXT, what_worked TEXT, what_failed TEXT,
            lessons_learned TEXT, retention_class TEXT, retain_until TEXT, created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE creative_history (
            event_id TEXT PRIMARY KEY, creative_request_id TEXT, asset_id TEXT, opportunity_id TEXT,
            event_type TEXT NOT NULL, previous_state TEXT, new_state TEXT, actor TEXT, reason TEXT,
            metadata_json TEXT, created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

    CreativeMemoryStore.record_winning_direction(
        opportunity_id="opp_holiday_mug_001",
        campaign_id="CAMP-HOLIDAY-MUG-2026",
        concept_name="The 6:12 AM Quiet Ritual",
        winning_prompt="PURPOSE: Luxury ecommerce hero image...",
        art_direction_summary="Tactile stoneware, 2800K morning side-light, walnut wood, calm solitude.",
        ai_slop_score=0.0,
        overall_score=93.5,
        db_path=db_file,
    )

    conn = sqlite3.connect(db_file)
    fb_rows = conn.execute("SELECT winning_hook, what_worked, retention_class FROM creative_feedback").fetchall()
    assert len(fb_rows) == 1
    assert fb_rows[0][0] == "The 6:12 AM Quiet Ritual"
    assert fb_rows[0][2] == "LONG_TERM_KNOWLEDGE"

    hist_rows = conn.execute("SELECT event_type, actor, new_state FROM creative_history").fetchall()
    assert len(hist_rows) == 1
    assert hist_rows[0][0] == "CREATIVE_DIRECTOR_SELECTION"
    assert hist_rows[0][1] == "creative_director"
    conn.close()


def test_research_creative_consumer():
    research_signals = {
        "customer_language": [
            "Every mug I own is either cheap or chipping",
            "I hate holiday gift junk that ends up in the thrift store",
            "My 15 minutes before the kids wake up is sacred",
        ],
        "category_conventions": ["Bright red holiday wrapping", "Over-caffeinated cheer"],
    }
    extracted = ResearchCreativeConsumer.extract_creative_inputs(research_signals)
    assert len(extracted["customer_language"]) == 3
    assert len(extracted["competitor_cliches_to_avoid"]) > 0
    assert any("White background floating product packshot" in c for c in extracted["competitor_cliches_to_avoid"])
    assert len(extracted["creative_opportunities"]) > 0
