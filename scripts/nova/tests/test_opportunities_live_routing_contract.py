"""Contract tests for Nova's reachable pre-Hermes Opportunities read route."""
from __future__ import annotations

import ast
import os
import re
from pathlib import Path


ROUTE_FUNCTIONS = {
    "_resolve_opportunities_read_request",
    "_render_opportunities_read_result",
    "_handle_opportunities_primary_read",
}
AVAILABLE_TOOLS = [
    "opportunities_get", "opportunities_list", "opportunities_latest",
    "opportunities_needs_research", "opportunities_search", "opportunities_top",
]


def _load_routes(result=None, tools=None):
    source_path = os.environ.get("NOVA_WORKER_PATH")
    if not source_path:
        raise AssertionError("NOVA_WORKER_PATH must point to the active Nova worker source")
    tree = ast.parse(Path(source_path).read_text(encoding="utf-8"))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name in ROUTE_FUNCTIONS]
    assert {node.name for node in nodes} == ROUTE_FUNCTIONS
    calls = []
    response = result or {"status": "OK", "items": []}
    catalog = [{"name": name} for name in (tools if tools is not None else AVAILABLE_TOOLS)]

    def call(name, arguments):
        calls.append((name, arguments))
        return response, 97

    namespace = {
        "re": re,
        "_current_mcp_tool_catalog": lambda **kwargs: catalog,
        "_call_registered_mcp_tool": call,
        "_deliver_response": lambda update_id, chat_id, text: {"state": "DELIVERED", "response": text},
        "_log_error": lambda *_args: None,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), source_path, "exec"), namespace)
    namespace["calls"] = calls
    return namespace


def test_top_and_90_day_queries_use_live_ranked_engine():
    routes = _load_routes({"status": "OK", "items": [{
        "title": "Mobile DNA testing business", "status": "RESEARCH_PENDING",
        "overall_score": 31.0, "recommendation": "RESEARCH_MORE", "confidence": "LOW",
        "time_to_first_revenue_days": None,
    }]})
    for update_id, question in enumerate((
        "What are our current top business opportunities?",
        "What opportunity should Nexus focus on first if the goal is revenue within 90 days?",
    ), 1):
        assert routes["_handle_opportunities_primary_read"](question, 1, update_id)
    assert [name for name, _ in routes["calls"]] == ["opportunities_top", "opportunities_top"]
    assert "authoritative Business Opportunities register" in routes["_render_opportunities_read_result"](
        {"items": [{"title": "Example", "overall_score": 3}]})
    response = routes["_render_opportunities_read_result"](
        {"items": [{"title": "Example", "overall_score": 3}]}, "revenue within 90 days")
    assert "not a verified revenue forecast" in response


def test_dna_query_reads_existing_record_and_research_handoff():
    routes = _load_routes({"status": "OK", "opportunity": {
        "title": "Mobile DNA testing business", "status": "RESEARCH_PENDING",
        "overall_score": 31.0, "recommendation": "RESEARCH_MORE", "confidence": "LOW",
        "assessment": {"missing_evidence": ["LOCAL_DEMAND", "STARTUP_COST"]},
        "history": [{"event_type": "RESEARCH_REQUESTED", "metadata": {"research_source_id": "hidden"}}],
    }})
    question = "Evaluate the mobile DNA testing opportunity and tell me what Research still needs to answer."
    assert routes["_handle_opportunities_primary_read"](question, 1, 9)
    assert routes["calls"] == [("opportunities_get", {"title": "Mobile DNA testing business"})]
    rendered = routes["_render_opportunities_read_result"](routes["calls"] and {
        "status": "OK", "opportunity": {
            "title": "Mobile DNA testing business", "status": "RESEARCH_PENDING",
            "overall_score": 31.0, "recommendation": "RESEARCH_MORE", "confidence": "LOW",
            "assessment": {"missing_evidence": ["LOCAL_DEMAND", "STARTUP_COST"]},
            "history": [{"event_type": "RESEARCH_REQUESTED", "metadata": {"research_source_id": "hidden"}}],
        }
    })
    assert "RESEARCH_PENDING" in rendered and "31.0/100" in rendered
    assert "LOCAL_DEMAND, STARTUP_COST" in rendered
    assert "Existing Research handoff: submitted; no new request was created." in rendered
    assert "hidden" not in rendered


def test_missing_research_query_uses_opportunities_register():
    routes = _load_routes({"status": "OK", "items": [{"title": "A", "status": "RESEARCH_PENDING"}]})
    assert routes["_handle_opportunities_primary_read"]("What opportunities need Research?", 1, 10)
    assert routes["calls"][0][0] == "opportunities_needs_research"


def test_missing_tool_or_matching_record_allows_accurate_fallback():
    no_tools = _load_routes({"status": "OK", "items": []}, tools=[])
    assert not no_tools["_handle_opportunities_primary_read"]("What are our current top business opportunities?", 1, 11)
    no_record = _load_routes({"status": "NOT_FOUND"})
    assert not no_record["_handle_opportunities_primary_read"]("Evaluate mobile DNA testing opportunity", 1, 12)


def test_opportunity_creation_and_activation_are_not_intercepted_as_reads():
    routes = _load_routes()
    for text in (
        "Create a business opportunity record",
        "Join this affiliate opportunity",
        "Run fresh independent Research on the mobile DNA testing opportunity",
    ):
        assert routes["_resolve_opportunities_read_request"](text, AVAILABLE_TOOLS) is None

