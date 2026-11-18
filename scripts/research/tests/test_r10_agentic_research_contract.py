from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path


R10 = Path.home() / ".nexus/releases/nexus-research-runtime-r10-codex-native-search-20261104-r14"
sys.path.insert(0, str(R10))
from nexus_research_r10 import batchc, codex_adapter as adapter_module  # noqa: E402


def test_business_research_prompt_requires_full_contract_and_active_follow_through():
    contract = batchc.business_research_deliverables()
    prompt = batchc.build_research_prompt(
        "RESEARCH_INVESTIGATOR", "Full DNA business case research", [], contract,
        existing_findings={"MARKET_DEMAND": {"status": "MISSING", "summary": "No current data"}},
    )
    assert len(contract) == 25
    assert "THE_ORIGINAL_SOURCE_IS_THE_STARTING_POINT_NOT_THE_RESEARCH_UNIVERSE" in prompt
    assert "CONTINUATION_REQUIRED=IN_SESSION_EXECUTION_REQUIRED" in prompt
    assert "Do not return after the first synthesis" in prompt
    assert "MARKET_DEMAND" in prompt
    assert "new source classes" in prompt


def test_business_contract_schema_requires_answer_evidence_and_unknowns_for_each_deliverable():
    schema = batchc.role_json_schema("RESEARCH_INVESTIGATOR", business_contract=True)
    fields = schema["properties"]["business_deliverables"]["properties"]
    assert len(fields) == 25
    for item in fields.values():
        assert set(item["required"]) == {"status", "answer", "evidence", "confidence", "source_quality", "unresolved_points"}
        assert item["properties"]["answer"]["minLength"] == 1


def test_codex_read_tool_allowlist_excludes_mutation_and_keeps_web_search():
    tools = adapter_module.approved_research_tools()
    assert "web_search" in tools
    assert "mcp__research_r5__research_health" in tools and "mcp__research_r5__research_library_search" in tools
    assert "mcp__nexus__github_remote_read_readme" in tools and "mcp__nexus__github_remote_read_file" in tools
    assert not any(name.endswith(("research_start", "research_continue", "research_cancel")) for name in tools)
    assert not any(name.endswith(("opportunities_submit", "systems_job_create")) for name in tools)


def test_codex_resume_keeps_release_directory_trust_bypass():
    command = adapter_module._resume_command("/usr/local/bin/codex", "thread-test")
    assert command == ["/usr/local/bin/codex", "exec", "resume", "--json", "--ignore-user-config",
                       "--skip-git-repo-check", "thread-test", "-"]


def test_continuation_is_in_session_and_same_source_only_retry_is_disallowed():
    policy = batchc.research_continuation_policy()
    assert policy["continuation_required"] == "IN_SESSION_EXECUTION_REQUIRED"
    assert policy["requeue_for_missing_public_information"] is False
    assert policy["same_source_only_retry"] is False
    assert policy["max_runtime_seconds"] <= 600
