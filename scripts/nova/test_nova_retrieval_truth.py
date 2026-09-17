from nexus_agent_platform.nova_capability_truth import build_admin_runtime_capability_truth
from nexus_agent_platform.nova_knowledge_retrieval import classify_question_layers, format_knowledge_for_prompt, retrieve_knowledge


def test_department_retrieval_uses_canonical_registry():
    query = "What departments does Nexus currently have and what is each responsible for?"
    result = retrieve_knowledge(query, classify_question_layers(query))
    rows = (result.get("governed") or {}).get("candidates", [])
    assert len(rows) == 12 and rows[0]["source_type"] == "DEPARTMENT_CANONICAL_PROJECTION"
    assert "responsibility" in format_knowledge_for_prompt(result)


def test_architecture_retrieval_prioritizes_runtime_trace():
    query = "What happened to Hermes and why is Admin Nova not using it?"
    result = retrieve_knowledge(query, classify_question_layers(query))
    rows = (result.get("repository") or {}).get("candidates", [])
    assert rows and rows[0]["path"] == "RUNTIME_ARCHITECTURE_TRACE"
    assert "get_nova_graph" in format_knowledge_for_prompt(result)


def test_direct_admin_capability_truth_does_not_infer_mcp_access():
    truth = build_admin_runtime_capability_truth()
    assert truth["nexus_mcp"]["active_connected"] is False
    assert truth["nexus_mcp"]["available_to_admin_nova"] is False
    assert truth["google_mcp"]["available_to_admin_nova"] is False
    assert truth["gmail_read"]["available_to_admin_nova"] is False
