import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from nexus_agent_platform.creative.creative_visual_discovery import (  # noqa: E402
    build_cross_pollination,
    decomposition_contract,
    discovery_worker_status,
    public_reference_catalog,
    select_cross_industry_references,
    visual_vocabulary,
)


def brief():
    return {"creative_brief_id": "visual-brief", "audience": "operators", "customer_tension": "too much status noise", "desired_outcome": "see the next safe action"}


def test_reference_records_are_principles_not_templates():
    refs = public_reference_catalog()
    assert refs
    assert all(r["copy_prohibited"] and r["reference_only"] for r in refs)
    assert all("source_url" in r and r["interesting_principle"] for r in refs)
    assert visual_vocabulary(refs)["templates_created"] == 0


def test_cross_pollination_selects_unrelated_domains():
    selected = select_cross_industry_references(brief(), public_reference_catalog(), count=4)
    assert 2 <= len(selected) <= 4
    assert len({r["industry"] for r in selected}) == len(selected)
    packet = build_cross_pollination(brief(), public_reference_catalog())
    assert len(packet["reference_ids"]) >= 2
    assert "copy no source language" in packet["synthesis_instruction"]


def test_decomposition_contract_and_worker_status_are_bounded():
    contract = decomposition_contract()
    assert "interesting_principle" in contract["required"]
    assert "copy exact layout" in contract["prohibited"]
    status = discovery_worker_status()
    assert status["status"] == "PASS_REAL_BOUNDED"
    assert status["provider_bypass_count"] == 0
