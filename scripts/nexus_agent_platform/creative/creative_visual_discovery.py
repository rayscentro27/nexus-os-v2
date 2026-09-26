"""Creative visual/reference intelligence without a template library.

References are decomposed into attributed principles. The module never stores
external artwork as a reusable page, copies source copy, or emits production
templates.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Sequence

from nexus_agent_platform.governed.persistence import append_record, read_records

REFERENCE_SCHEMA = "nexus.creative-reference.v1"
CROSS_POLLINATION_SCHEMA = "nexus.creative-cross-pollination.v1"
TERRITORY_SCHEMA = "nexus.creative-visual-territory.v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:16]


@dataclass(frozen=True)
class CreativeReference:
    reference_id: str
    source_url: str
    source_name: str
    source_type: str
    medium: str
    industry: str
    subculture_or_context: str
    composition: str
    hierarchy: str
    typography_behavior: str
    image_treatment: str
    visual_metaphor: str
    spatial_behavior: str
    color_behavior: str
    texture: str
    motion_behavior: str
    interaction_pattern: str
    narrative_structure: str
    information_density: str
    emotional_effect: str
    interesting_principle: str
    why_it_works: str
    customer_tension_it_could_express: str
    possible_cross_industry_use: str
    copy_prohibited: bool = True
    reference_only: bool = True
    similarity_to_existing_nexus_work: str = "NOT_YET_COMPARED"
    historical_usage: str = "NOT_USED"
    last_used_at: str | None = None
    created_at: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def reference_schema() -> Dict[str, Any]:
    return {"schema_version": REFERENCE_SCHEMA, "fields": list(CreativeReference.__dataclass_fields__.keys()), "copy_prohibited": True, "reference_only": True}


def public_reference_catalog() -> List[Dict[str, Any]]:
    """Lawful public source metadata; no external artwork or source copy is stored."""
    rows = [
        {"source_url": "https://ntrs.nasa.gov/citations/20220005510", "source_name": "NASA Introduction to Data Visualization", "source_type": "PUBLIC_TECHNICAL_TUTORIAL", "medium": "data visualization", "industry": "aerospace/science", "context": "public technical communication", "principle": "content-first comparison and accessibility turn complex evidence into navigable visual decisions", "why": "The visual system serves the audience's understanding rather than spectacle.", "effect": "trustworthy, lucid", "use": "express uncertainty without making a customer feel lost"},
        {"source_url": "https://svs.gsfc.nasa.gov/metaviz", "source_name": "NASA Scientific Visualization Studio", "source_type": "PUBLIC_VISUAL_ARCHIVE", "medium": "scientific visualization", "industry": "aerospace/science", "context": "public education", "principle": "layered scale, motion, and annotation let a viewer move from overview to meaningful detail", "why": "A complex system becomes legible without flattening its depth.", "effect": "wonder with authority", "use": "express a customer's transition from noise to a next safe action"},
        {"source_url": "https://www.pentagram.com/work/london-college-of-communication", "source_name": "Pentagram London College of Communication wayfinding", "source_type": "PUBLIC_IDENTITY_CASE_STUDY", "medium": "wayfinding/environmental graphics", "industry": "education/architecture", "context": "multi-building navigation", "principle": "a consistent background plate and adaptable information layers make changing locations understandable", "why": "The system separates stable orientation from changing content.", "effect": "calm, navigable", "use": "express ownership and responsibility without a dashboard template"},
        {"source_url": "https://www.awwwards.com/editorial-new-variable-typeface-by-locomotive-wins-site-of-the-month-october.html", "source_name": "Locomotive Editorial New", "source_type": "PUBLIC_WEB_DESIGN_CASE_STUDY", "medium": "interactive typography", "industry": "type/design culture", "context": "editorial advertising", "principle": "variable typography can become the motion system, with hierarchy changing through weight, scale, and spacing", "why": "The medium's behavior carries the narrative instead of decorative motion.", "effect": "editorial, playful, unexpected", "use": "express a tension that changes as evidence becomes clearer"},
        {"source_url": "https://www.itsnicethat.com/articles/studio-fnt-highlights-graphic-design-050917", "source_name": "Studio Fnt exhibition identity", "source_type": "PUBLIC_GRAPHIC_DESIGN_CASE_STUDY", "medium": "exhibition identity/print", "industry": "arts/culture", "context": "diverse exhibition program", "principle": "bold typography and selective fluorescent color can identify a broad program without overloading it with images", "why": "A strong typographic signal creates unity while leaving content room to breathe.", "effect": "energetic, human, memorable", "use": "express a complex offer without adding more feature noise"},
        {"source_url": "https://www.nas.nasa.gov/assets/nas/pdf/techreports/1994/nas-94-002.pdf", "source_name": "NASA Principles of Information Display", "source_type": "PUBLIC_TECHNICAL_GUIDANCE", "medium": "information display", "industry": "aerospace/science", "context": "technical decision support", "principle": "show content clearly, support comparison, preserve integrity, and reveal detail at multiple levels", "why": "Visual richness is valuable only when it increases truthful understanding.", "effect": "precise, credible", "use": "express evidence boundaries and safe next steps"},
        {"source_url": "https://mynasadata.larc.nasa.gov/basic-page/gestalt-principles-and-data-visualizations", "source_name": "My NASA Data Gestalt principles", "source_type": "PUBLIC_EDUCATIONAL_RESOURCE", "medium": "data visualization/education", "industry": "science education", "context": "teaching perception", "principle": "grouping, proximity, and figure-ground can make a complex relationship immediately graspable", "why": "Perceptual structure reduces cognitive load before any copy is read.", "effect": "clear, approachable", "use": "express a customer's need to see what belongs together"},
        {"source_url": "https://www.pentagram.com/work/london-college-of-communication", "source_name": "Pentagram adaptable wayfinding system", "source_type": "PUBLIC_ARCHITECTURE_REFERENCE", "medium": "signage/system design", "industry": "architecture", "context": "changing physical environment", "principle": "stable visual anchors can hold a system together while local information changes", "why": "It balances consistency with real-world variation.", "effect": "reliable, human-scaled", "use": "express a changing workflow without pretending it is static"},
    ]
    return [{"reference_id": f"ref_{_id(row)}", "schema_version": REFERENCE_SCHEMA, "source_url": row["source_url"], "source_name": row["source_name"], "source_type": row["source_type"], "medium": row["medium"], "industry": row["industry"], "subculture_or_context": row["context"], "composition": row["principle"], "hierarchy": row["principle"], "typography_behavior": row["principle"], "image_treatment": "principle-level only; no asset retained", "visual_metaphor": row["principle"], "spatial_behavior": row["principle"], "color_behavior": row["principle"], "texture": "not retained", "motion_behavior": row["principle"], "interaction_pattern": row["principle"], "narrative_structure": row["principle"], "information_density": row["principle"], "emotional_effect": row["effect"], "interesting_principle": row["principle"], "why_it_works": row["why"], "customer_tension_it_could_express": "bounded customer tension supplied by the brief", "possible_cross_industry_use": row["use"], "copy_prohibited": True, "reference_only": True, "similarity_to_existing_nexus_work": "NOT_YET_COMPARED", "historical_usage": "NOT_USED", "last_used_at": None, "created_at": _now()} for row in rows]


def select_cross_industry_references(brief: Dict[str, Any], references: Sequence[Dict[str, Any]], count: int = 4) -> List[Dict[str, Any]]:
    """Select unrelated domains deterministically; never select by client industry alone."""
    count = max(2, min(4, count))
    audience = str(brief.get("audience") or brief.get("customer_segment") or brief.get("brief_id") or "brief")
    ranked = sorted(references, key=lambda r: _id((audience, r.get("industry"), r.get("reference_id"))))
    selected: List[Dict[str, Any]] = []
    domains: set[str] = set()
    for row in ranked:
        if row.get("industry") in domains: continue
        selected.append(row); domains.add(str(row.get("industry")))
        if len(selected) >= count: break
    return selected


def build_cross_pollination(brief: Dict[str, Any], references: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    selected = select_cross_industry_references(brief, references)
    return {"schema_version": CROSS_POLLINATION_SCHEMA, "brief_id": brief.get("brief_id") or brief.get("creative_brief_id"), "reference_ids": [r["reference_id"] for r in selected], "source_domains": [r["industry"] for r in selected], "principles": [r["interesting_principle"] for r in selected], "synthesis_instruction": "translate each principle into a new visual territory for the supplied customer tension; copy no source language or layout", "created_at": _now()}


def decomposition_contract() -> Dict[str, Any]:
    return {"instruction": "Decompose a public reference into observed design principles, not a reusable template.", "required": ["composition", "hierarchy", "typography_behavior", "image_treatment", "visual_metaphor", "spatial_behavior", "color_behavior", "texture", "motion_behavior", "interaction_pattern", "narrative_structure", "information_density", "emotional_effect", "interesting_principle", "why_it_works", "what_was_not_copied"], "prohibited": ["copy source text", "copy exact layout", "store external artwork", "name it as a Nexus template"]}


def visual_vocabulary(references: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    principles = {r.get("interesting_principle") for r in references if r.get("interesting_principle")}
    domains = {r.get("industry") for r in references if r.get("industry")}
    return {"reference_count": len(references), "unique_visual_principles": len(principles), "unique_source_domains": len(domains), "unrelated_industry_count": len(domains), "principles_only": True, "templates_created": 0}


def persist_reference_principles(references: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Persist only attributed, non-redundant principles; never external artwork."""
    existing = read_records("creative_references")
    existing_ids = {row.get("reference_id") for row in existing}
    seen_principles = {row.get("interesting_principle") for row in existing}
    created = 0
    for reference in references:
        if not reference.get("reference_only") or not reference.get("copy_prohibited"): continue
        if reference.get("reference_id") in existing_ids or reference.get("interesting_principle") in seen_principles: continue
        append_record("creative_references", {**reference, "persistence": "PRINCIPLE_ONLY", "external_asset_stored": False})
        existing_ids.add(reference.get("reference_id")); seen_principles.add(reference.get("interesting_principle")); created += 1
    return {"status": "PASS_REAL_BOUNDED", "created": created, "total": len(existing_ids), "collection": "creative_references", "external_assets_stored": False}


def synthesize_visual_territory(brief: Dict[str, Any], pollination: Dict[str, Any], model: Any, *, index: int = 0) -> Dict[str, Any]:
    """One bounded model call: source principles become a new visual territory."""
    prompt = ("Create one original visual territory as JSON. Use the customer tension and cross-industry principles as inputs, "
              "not templates. Do not copy source wording, layout, assets, or brand identity. Return fields: "
              "customer_tension, strategic_angle, reference_domains, borrowed_principles, central_design_idea, composition, "
              "typography_behavior, image_world, visual_metaphor, motion_or_interaction, narrative_structure, emotional_effect, "
              "what_makes_it_new_for_nexus, proof_boundary, channel_fit, template_likeness. Classify template_likeness as "
              "ORIGINAL_SYNTHESIS, ADAPTED_REFERENCE_PRINCIPLE, TEMPLATE_LIKE, or DERIVATIVE.\n"
              f"BRIEF={json.dumps(brief, default=str)}\nCROSS_POLLINATION={json.dumps(pollination, default=str)}")
    result = model.call("Creative Visual Discovery", prompt, {"brief_id": brief.get("brief_id") or brief.get("creative_brief_id"), "reference_ids": pollination.get("reference_ids", []), "copy_prohibited": True})
    if result.get("status") != "PASS": raise RuntimeError("creative_visual_discovery_model_blocked")
    data = result.get("territory") or result.get("concept") or result
    if isinstance(data, list): data = data[0] if data else {}
    territory = {"schema_version": TERRITORY_SCHEMA, "territory_id": f"visual_territory_{_id((brief, pollination, index))}", "brief_id": brief.get("brief_id") or brief.get("creative_brief_id"), "reference_ids": pollination.get("reference_ids", []), "source_domains": pollination.get("source_domains", []), "generation_source": "creative.visual_discovery", "created_at": _now()}
    for key in ("customer_tension", "strategic_angle", "reference_domains", "borrowed_principles", "central_design_idea", "composition", "typography_behavior", "image_world", "visual_metaphor", "motion_or_interaction", "narrative_structure", "emotional_effect", "what_makes_it_new_for_nexus", "proof_boundary", "channel_fit", "template_likeness"):
        territory[key] = data.get(key, "UNKNOWN_FROM_MODEL")
    territory["copy_prohibited"] = True
    territory["reference_only_inputs"] = True
    return territory


def discovery_worker_status() -> Dict[str, Any]:
    return {"worker": "creative.visual_discovery", "tool_path": "Nexus-owned Python reference/decomposition adapter + existing Hermes model route", "host": "MAC", "capability": "creative.visual_discovery", "status": "PASS_REAL_BOUNDED", "remote_control_plane_required": False, "provider_bypass_count": 0}
