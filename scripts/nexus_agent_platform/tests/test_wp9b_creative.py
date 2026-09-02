import json

from nexus_agent_platform.creative.wp9b import (
    CreativeBrief, build_real_package, genericness_critic, provider_routes,
    revision, structured_critic,
)


def brief():
    return CreativeBrief("b", "GoClear/Nexus", "initiative", "c", "w", "objective", "audience", "offer", ["LANDING_PAGE"], "review", ["no claims"], ["landing"], ["alpha"], "brand", ["no guarantee"], 0, "VALIDATION_READY")


def test_wp9b_package_is_alpha_linked_and_validation_ready():
    package = build_real_package()
    assert len(package["territories"]) == 3
    assert package["research_packet"]["model_output_not_evidence"] is True
    assert package["growth_handoff"]["status"] == "READY_FOR_REVIEW"
    assert package["finance"]["cash_cost_usd"] == 0.0


def test_critic_and_revision_preserve_lineage():
    b = brief()
    t = {"territory_id": "t", "visual_direction": "editorial route map", "differentiation_rationale": "specific"}
    c = structured_critic(b.__dict__, t, "A specific readiness path.")
    v = {"version_id": "v1", "copy": "A specific readiness path."}
    r = revision(v, c)
    assert c["independent"] is True
    assert r["parent_version_id"] == "v1"
    assert r["version_id"] != "v1"


def test_provider_inventory_is_honest_without_activation():
    rows = {r["capability"]: r for r in provider_routes()}
    assert rows["RENDER"]["status"] == "AVAILABLE"
    assert rows["IMAGE"]["status"] == "NOT_CONFIGURED"
    assert rows["VIDEO"]["status"] == "NOT_CONFIGURED"
