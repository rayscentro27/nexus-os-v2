from scripts.creative.design_engine import (
    classify_surface, create_design_project, implementation_contract, transition,
)


def test_surface_router_uses_specialist_workers():
    assert classify_surface("Nexus Admin Executive Command Center")["recommended_worker"] == "penpot"
    assert classify_surface("affiliate campaign landing page")["recommended_worker"] == "openpage"
    assert classify_surface("existing React visual refinement", explicit="EXISTING_REACT_VISUAL_EDIT")["recommended_worker"] == "onlook"


def test_project_cannot_reach_codex_before_ray_approval_and_freeze():
    project = create_design_project("Admin", "operator clarity", "Admin dashboard", surface_type="ADMIN_DASHBOARD")
    assert project["state"] == "REQUESTED"
    assert project["design_frozen"] is False
    try:
        implementation_contract(project)
    except ValueError as exc:
        assert str(exc) == "implementation_requires_frozen_approved_design"
    else:
        raise AssertionError("unapproved design reached Codex")


def test_state_machine_requires_approval_then_freeze():
    project = create_design_project("Admin", "operator clarity", "Admin dashboard", surface_type="ADMIN_DASHBOARD")
    for state in ("BRIEF_CREATED", "WORKER_SELECTED", "DESIGNING", "DESIGN_READY", "READY_FOR_RAY", "APPROVED", "FROZEN"):
        project = transition(project, state)
    assert project["design_frozen"] is True
    assert implementation_contract(project)["instruction"] == "IMPLEMENT THIS DESIGN."
