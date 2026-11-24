"""Regression contract for the currently active R10 structured-output schemas."""
from pathlib import Path
import sys

ACTIVE_R10 = Path.home() / ".nexus/releases/nexus-research-runtime-r10-codex-native-search-20261104-r14"
sys.path.insert(0, str(ACTIVE_R10))

from nexus_research_r10.batchc import ROLE_POLICY, role_json_schema  # noqa: E402


def test_all_codex_structured_output_properties_are_required():
    for role in ROLE_POLICY:
        schema = role_json_schema(role)
        assert set(schema["required"]) == set(schema["properties"]), role


def test_investigator_always_emits_evidence_limitations_field():
    schema = role_json_schema("RESEARCH_INVESTIGATOR")
    assert "evidence_limitations" in schema["properties"]
    assert "evidence_limitations" in schema["required"]
