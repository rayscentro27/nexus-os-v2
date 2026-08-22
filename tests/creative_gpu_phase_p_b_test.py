import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from nexus_agent_platform.creative.gpu import build_image_job, validate_image_job


def _job():
    return build_image_job(
        brief_id="brief-test",
        growth_id="growth-test",
        opportunity_id="opp-test",
        evidence_refs=["ev-test"],
        prompt="A safe business readiness illustration.",
        negative_prompt="text, logo, watermark",
        seed=7,
    )


def test_allowlisted_gpu_job_is_bounded_and_provenanced():
    job = _job()
    assert validate_image_job(job) == (True, "ok")
    assert job["capability"] == "creative.image_generate"
    assert job["limits"] == {"timeout_seconds": 180, "width": 1024, "height": 1024, "steps": 20, "images": 1, "output_format": "png"}
    assert job["policy"]["custom_nodes"] == "NONE"
    assert job["source"]["evidence_refs"] == ["ev-test"]


def test_unknown_workflow_model_and_dimensions_fail_closed():
    job = _job()
    job["correlation"]["workflow_id"] = "not-allowlisted"
    assert validate_image_job(job)[0] is False
    job = _job()
    job["correlation"]["model_id"] = "not-allowlisted"
    assert validate_image_job(job)[0] is False
    job = _job()
    job["limits"]["width"] = 2048
    assert validate_image_job(job)[0] is False


def test_material_change_changes_request_identity_inputs():
    first = _job()
    second = _job()
    second["correlation"]["seed"] += 1
    assert first["correlation"] != second["correlation"]


def test_public_actions_are_not_part_of_worker_job_policy():
    job = _job()
    assert job["policy"]["public_ui"] is False
    assert job["policy"]["no_external_processing"] is True
