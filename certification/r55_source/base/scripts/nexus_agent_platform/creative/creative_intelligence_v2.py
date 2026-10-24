"""Nexus-owned Creative Intelligence V2.

This module borrows only the mechanisms proven by the ideate-core canary:
independent stance generation, a bounded shared-pool build-on round, explicit
diversity/history gates, and targeted regeneration. It deliberately does not
depend on ideate-core or create a new Creative authority boundary.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
import hashlib
import json
from typing import Any, Callable, Dict, Iterable, List, Sequence

from .intelligence import DIMENSIONS, creative_signature, similarity, similarity_class

CREATIVE_TENSION_SCHEMA = "nexus.creative-tension.v1"
IDEATION_STANCE_SCHEMA = "nexus.creative-ideation-stance.v1"
CREATIVE_CONCEPT_POOL_SCHEMA = "nexus.creative-concept-pool.v2"

CONCEPT_FIELDS = (
    "human_insight", "audience_tension", "strategic_angle", "central_idea",
    "visual_metaphor", "narrative_structure", "emotional_direction",
    "hook_family", "visual_family", "layout_family", "cta_pattern",
    "channel_fit", "proof_boundary",
)


@dataclass(frozen=True)
class CreativeIdeationBudget:
    max_stances: int = 5
    max_initial_calls: int = 5
    max_build_on_calls: int = 1
    max_regen_calls: int = 2
    max_total_calls: int = 15

    def as_dict(self) -> Dict[str, int]:
        return asdict(self)


DEFAULT_STANCES = (
    {"id": "emotional", "label": "EMOTIONAL", "directive": "Find the felt tension and the emotional shift; avoid generic inspiration."},
    {"id": "proof_driven", "label": "PROOF_DRIVEN", "directive": "Build from what can be verified; make uncertainty and evidence useful without inventing proof."},
    {"id": "visual_metaphor", "label": "VISUAL_METAPHOR", "directive": "Find an ownable visual world or physical metaphor that changes how the audience sees the problem."},
    {"id": "story_first", "label": "STORY_FIRST", "directive": "Create a human narrative with a clear before, tension, turn, and next action."},
    {"id": "contrarian", "label": "CONTRARIAN", "directive": "Reject the obvious category promise and find a credible inversion or overlooked truth."},
    {"id": "utility", "label": "UTILITY", "directive": "Turn the tension into a practical decision aid or useful behavior, not a feature list."},
)


def extract_creative_tension(brief: Dict[str, Any]) -> Dict[str, Any]:
    """Project only facts present in the brief into a bounded tension model."""
    audience = brief.get("audience") or brief.get("customer_segment") or brief.get("opportunity", {}).get("target_customer")
    current = brief.get("current_reality") or brief.get("customer_tension") or brief.get("customer_problem") or brief.get("opportunity", {}).get("problem")
    desired = brief.get("desired_outcome") or brief.get("desired_change") or brief.get("goal") or brief.get("opportunity", {}).get("recommended_next_action")
    proof = brief.get("proof_boundary") or brief.get("evidence_constraints") or brief.get("compliance_context") or ["use only supplied evidence", "do not invent outcomes"]
    return {
        "schema_version": CREATIVE_TENSION_SCHEMA,
        "audience": audience or "UNKNOWN_FROM_BRIEF",
        "current_reality": current or "UNKNOWN_FROM_BRIEF",
        "frustration": current or "UNKNOWN_FROM_BRIEF",
        "desired_change": desired or "UNKNOWN_FROM_BRIEF",
        "emotional_tension": brief.get("emotional_tension") or "UNKNOWN_FROM_BRIEF",
        "functional_tension": brief.get("functional_tension") or current or "UNKNOWN_FROM_BRIEF",
        "identity_tension": brief.get("identity_tension") or "UNKNOWN_FROM_BRIEF",
        "fear": brief.get("fear") or "UNKNOWN_FROM_BRIEF",
        "aspiration": brief.get("aspiration") or desired or "UNKNOWN_FROM_BRIEF",
        "proof_boundary": proof,
        "source_fields": sorted(k for k in ("audience", "customer_segment", "customer_tension", "customer_problem", "desired_outcome", "desired_change", "goal", "evidence_constraints", "compliance_context") if k in brief),
    }


def select_ideation_stances(brief: Dict[str, Any], *, max_stances: int = 5) -> List[Dict[str, Any]]:
    """Choose a bounded diverse panel; no stance sees the panel's output."""
    max_stances = max(4, min(7, max_stances))
    chosen = list(DEFAULT_STANCES[:max_stances])
    if max_stances < 5:
        chosen = [DEFAULT_STANCES[0], DEFAULT_STANCES[1], DEFAULT_STANCES[2], DEFAULT_STANCES[4]][:max_stances]
    return [{"schema_version": IDEATION_STANCE_SCHEMA, "stance_id": s["id"], "label": s["label"], "directive": s["directive"], "selection_reason": "bounded diversity panel"} for s in chosen]


def _candidate_from_response(response: Dict[str, Any], stance: Dict[str, Any], brief: Dict[str, Any], generation_round: int) -> Dict[str, Any] | None:
    values: Any = response.get("concepts") or response.get("territories") or response.get("candidates") or response.get("concept") or response.get("candidate") or response
    if isinstance(values, dict): values = [values]
    if not isinstance(values, list) or not values or not isinstance(values[0], dict): return None
    raw = values[0]
    central = raw.get("central_idea") or raw.get("idea") or raw.get("text")
    if not central: return None
    stable_id = hashlib.sha256(f"{brief.get('brief_id') or brief.get('creative_brief_id')}|{stance['stance_id']}|{generation_round}|{central}".encode("utf-8")).hexdigest()[:16]
    candidate = {"schema_version": CREATIVE_CONCEPT_POOL_SCHEMA, "concept_id": f"v2_{stance['stance_id']}_{generation_round}_{stable_id}", "brief_id": brief.get("brief_id") or brief.get("creative_brief_id"), "stance": stance["stance_id"], "generation_round": generation_round, "status": "CANDIDATE"}
    for field in CONCEPT_FIELDS:
        candidate[field] = raw.get(field) or raw.get("visual_world" if field == "visual_family" else "cta_approach" if field == "cta_pattern" else field) or ""
    candidate["hook_pattern"] = candidate["hook_family"]
    candidate["format"] = raw.get("format") or raw.get("channel") or ""
    candidate["evidence_refs"] = brief.get("evidence_refs") or brief.get("customer_language_refs") or []
    candidate["creative_signature"] = creative_signature(candidate)
    candidate["signature_fingerprint"] = "|".join(f"{k}:{v}" for k, v in candidate["creative_signature"].items())
    candidate["central_idea"] = str(central)
    return candidate


def diversity_gate(concepts: Sequence[Dict[str, Any]], history: Sequence[Dict[str, Any]] = (), *, near_threshold: float = .85, high_threshold: float = .65) -> Dict[str, Any]:
    """Keep the first candidate in a collision and mark later candidates for regeneration."""
    kept: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    pairs: List[float] = []
    historical: List[Dict[str, Any]] = []
    for concept in concepts:
        historical.append({**concept, "historical_similarity_score": max((similarity(concept, old) for old in history), default=0.0)})
    for concept in historical:
        values = [similarity(concept, prior) for prior in kept]
        max_current = max(values, default=0.0)
        pairs.extend(values)
        if max_current >= high_threshold:
            rejected.append({**concept, "diversity_gate": "NEAR_DUPLICATE" if max_current >= near_threshold else "HIGH_SIMILARITY", "similarity_to_kept": round(max_current, 3)})
        else:
            kept.append({**concept, "diversity_gate": "PASS", "historical_similarity": similarity_class(concept["historical_similarity_score"])})
    return {"status": "PASS" if not rejected else "REGENERATE_REQUIRED", "kept": kept, "rejected": rejected, "pairwise_max_similarity": round(max(pairs, default=0.0), 3), "pairwise_mean_similarity": round(sum(pairs) / len(pairs), 3) if pairs else 0.0, "near_duplicate_count": sum(1 for x in pairs if x >= near_threshold), "high_similarity_count": sum(1 for x in pairs if x >= high_threshold)}


def _prompt_for_stance(brief: Dict[str, Any], tension: Dict[str, Any], stance: Dict[str, Any], history: Sequence[Dict[str, Any]]) -> str:
    exclusions = [{k: old.get(k) for k in ("strategic_angle", "visual_metaphor", "hook_pattern", "central_idea")} for old in list(history)[:20]]
    return (f"Generate exactly one Creative territory as JSON under concepts[]. You are the independent {stance['label']} stance. "
            f"{stance['directive']} Do not see or reference other current-round concepts. Brief={brief}. TENSION={tension}. "
            f"Historical exclusion hints only={exclusions}. Return fields={list(CONCEPT_FIELDS)}. Evidence-bounded, draft-only, no invented proof.")


def _call(model: Any, purpose: str, instruction: str, context: Dict[str, Any]) -> Dict[str, Any]:
    # BoundedCreativeModel compacts its context for ordinary Creative calls.
    # Review stages must see the complete bounded pool, so deliver the exact
    # pool in the instruction envelope and keep the auxiliary context small.
    full_context = json.dumps(context, sort_keys=True, default=str, separators=(",", ":"))
    result = model.call(purpose, f"{instruction}\nFULL_BOUNDED_CONTEXT_JSON={full_context}", {"context_delivery": "full_in_instruction", "brief_id": context.get("brief", {}).get("brief_id") if isinstance(context.get("brief"), dict) else None})
    if result.get("status") != "PASS": raise RuntimeError(f"creative_v2_model_blocked:{purpose}")
    return result


def regenerate_creative_concept(model: Any, brief: Dict[str, Any], rejected: Dict[str, Any], new_stance: Dict[str, Any], *, reason: str) -> Dict[str, Any] | None:
    response = _call(model, "Creative V2 Regeneration", "Replace the rejected territory with one genuinely new strategic territory. Do not rewrite the headline. Use a different stance and different strategic angle, central idea, and visual world. Return exactly one object under concepts[].", {"brief": brief, "rejected": rejected, "new_stance": new_stance, "reason": reason, "required_fields": CONCEPT_FIELDS})
    return _candidate_from_response(response, new_stance, brief, 3)


def run_creative_intelligence_v2(brief: Dict[str, Any], model: Any, *, history: Sequence[Dict[str, Any]] = (), budget: CreativeIdeationBudget | None = None) -> Dict[str, Any]:
    budget = budget or CreativeIdeationBudget()
    tension = extract_creative_tension(brief)
    stances = select_ideation_stances(brief, max_stances=budget.max_stances)
    calls = 0
    results: List[Dict[str, Any]] = []

    def generate(stance: Dict[str, Any]) -> Dict[str, Any] | None:
        response = _call(model, f"Creative V2 {stance['label']}", _prompt_for_stance(brief, tension, stance, history), {"brief": brief, "tension": tension, "stance": stance, "history_exclusion_hints": [{"central_idea": h.get("central_idea")} for h in list(history)[:20]]})
        return _candidate_from_response(response, stance, brief, 1)

    with ThreadPoolExecutor(max_workers=len(stances)) as pool:
        futures = [pool.submit(generate, stance) for stance in stances[:budget.max_initial_calls]]
        for future in as_completed(futures):
            candidate = future.result()
            calls += 1
            if candidate: results.append(candidate)
    results.sort(key=lambda x: x["concept_id"])
    gate = diversity_gate(results, history)
    kept = list(gate["kept"])

    build_on: List[Dict[str, Any]] = []
    if kept and calls < budget.max_total_calls and budget.max_build_on_calls:
        seed = kept[0]
        build_stance = next((s for s in stances if s["stance_id"] != seed["stance"]), stances[-1])
        response = _call(model, "Creative V2 Build On", "Turn the promising seed into a new strategic territory. Choose EXPAND, COMBINE, REFRAME, FLIP, DEEPEN, VISUALIZE_DIFFERENTLY, or CHANGE_NARRATIVE. Do not rewrite the same headline. Return exactly one object under concepts[].", {"brief": brief, "tension": tension, "seed": seed, "build_on_stance": build_stance, "pool": kept})
        candidate = _candidate_from_response(response, build_stance, brief, 2)
        calls += 1
        if candidate: build_on.append(candidate)
        gate = diversity_gate([*kept, *build_on], history)
        kept = gate["kept"]

    contrarian = advocate = critic = director = None
    if calls + 4 <= budget.max_total_calls:
        pooled = {"brief": brief, "tension": tension, "concepts": kept}
        contrarian = _call(model, "Creative V2 Contrarian", "Inspect the full pool for industry clichés, AI clichés, overused metaphors, predictable hooks, and overlapping concepts. Propose at least one alternative territory if the pool is too safe. Return JSON only.", pooled)
        calls += 1
        advocate = _call(model, "Creative V2 Customer Advocate", "Challenge whether this customer would care, whether the concept is about the customer rather than Nexus, whether the tension is real in the brief, and which assumptions are unsupported. Return JSON only.", pooled)
        calls += 1
        critic = _call(model, "Creative V2 Critic", "Evaluate every pooled concept on originality, brief fit, customer relevance, emotional strength, strategic distinction, visual potential, genericness, brand fit, proof safety, and channel fit. Return verdicts with concept_id and one of ACCEPT, BUILD_ON, REGENERATE, REVISION_MINOR, REVISION_MAJOR, REJECT_DIRECTION. Return JSON only.", {**pooled, "contrarian": contrarian, "customer_advocate": advocate})
        calls += 1
        verdicts = critic.get("verdicts") if isinstance(critic, dict) else []
        if not isinstance(verdicts, list): verdicts = []
        for verdict in verdicts:
            decision = str(verdict.get("decision", "")).upper() if isinstance(verdict, dict) else ""
            target = next((c for c in kept if c.get("concept_id") == verdict.get("concept_id")), None) if isinstance(verdict, dict) else None
            if decision in {"REGENERATE", "REJECT_DIRECTION"} and target and calls < budget.max_total_calls and len([c for c in build_on if c.get("generation_round") == 3]) < budget.max_regen_calls:
                alternate = next((s for s in stances if s["stance_id"] != target.get("stance")), stances[0])
                replacement = regenerate_creative_concept(model, brief, target, alternate, reason=verdict.get("reason", decision))
                calls += 1
                if replacement:
                    kept = [c for c in kept if c.get("concept_id") != target.get("concept_id")] + [replacement]
                    build_on.append(replacement)
        director = _call(model, "Creative V2 Creative Director", "Select PRIMARY, ALTERNATE, and EXPERIMENTAL from the pool. Do not choose only by numeric score. Explain WHY, RISK, CUSTOMER_TENSION, and PRODUCTION_POTENTIAL for each. Return JSON only.", {**pooled, "critic": critic, "contrarian": contrarian, "customer_advocate": advocate})
        calls += 1

    return {"status": "PASS_REAL_BOUNDED", "tension": tension, "stances": stances, "blind_generation": True, "initial_candidates": results, "build_on_candidates": build_on, "concepts": kept, "diversity_gate": gate, "budget": budget.as_dict(), "calls": calls, "contrarian": contrarian, "customer_advocate": advocate, "critic": critic, "director": director}
