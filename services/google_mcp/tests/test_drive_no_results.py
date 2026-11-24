import os
from pathlib import Path

os.environ["GOOGLE_MCP_RECEIPT_DIR"] = "/private/tmp/google-drive-no-results-20261031/test-receipts"

from services.google_mcp import server


def test_empty_drive_search_is_explicit_successful_no_match():
    result = server._result("drive_search", query={"query": "Nexus"}, items=[],
                            source="drive.files.list")
    assert result["status"] == "ok"
    assert result["item_count"] == 0
    assert result["no_results"] is True
    assert "drive.file authorization" in result["result_note"]
    assert "do not repeat" in result["result_note"]


def test_drive_search_with_matches_keeps_existing_result_contract():
    result = server._result("drive_search", query={}, items=[{"id": "test"}],
                            source="drive.files.list")
    assert result["status"] == "ok"
    assert result["item_count"] == 1
    assert "no_results" not in result


def test_other_google_tools_keep_existing_empty_result_contract():
    result = server._result("gmail_search", query={}, items=[], source="gmail.messages.list")
    assert result["status"] == "ok"
    assert result["item_count"] == 0
    assert "no_results" not in result


def test_drive_tool_description_explains_scope_and_terminal_empty_result():
    source = Path(server.__file__).read_text()
    assert "app-created or user-selected files" in source
    assert "final no-match" in source
