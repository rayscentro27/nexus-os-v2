from nova import live_capability_registry
from nova.live_capability_registry import _capability_inventory, summarize_capability_registry


def test_inventory_separates_active_inactive_auth_and_unavailable():
    hermes = {
        "native_tools_enabled": ["web", "browser", "file", "terminal", "code_execution", "image_gen", "skills", "cronjob"],
        "native_tools_disabled": ["video_gen"],
        "browser_enabled": True,
        "mcp_servers": {"nexus_mcp_remote": True, "you-com": True, "metricool_goclear": True},
        "you_com_handshake": "PASS",
        "metricool": {"handshake": "PASS", "tool_count": 9},
        "runtime": {
            "terminal_backend": "local", "command_allowlist_configured": False,
            "safe_write_roots": ["/opt/data"], "code_execution_mode": "project",
            "single_query_approval_mode": "deny", "image_provider_available": False,
            "video_provider_available": False, "voice_enabled": False,
            "routines_enabled": False,
        },
    }
    mcp = {"handshake": "PASS", "tools": ["nexus_assign_research"]}
    google = {"tools": ["gmail_search", "calendar_search_events", "drive_search"], "authentication": "AUTH_REQUIRED"}
    rows = {r["capability"]: r for r in _capability_inventory(hermes, ["nexus_mcp_remote", "you-com", "web"], mcp, google)}
    assert rows["web_search"]["status"] == "ACTIVE"
    assert rows["browser_automation"]["status"] == "KNOWN_BUT_INACTIVE"
    assert rows["file_document_pdf"]["status"] == "KNOWN_BUT_INACTIVE"
    assert rows["terminal"]["safe_for_nova"] is False
    assert rows["code_execution"]["safe_for_nova"] is False
    assert rows["image_generation"]["status"] == "UNAVAILABLE"
    assert rows["video_generation"]["status"] == "UNAVAILABLE"
    assert rows["google_workspace"]["status"] == "AUTH_REQUIRED"
    assert rows["nexus_mcp"]["status"] == "ACTIVE"
    assert rows["metricool_mcp"]["status"] == "KNOWN_BUT_INACTIVE"


def test_capability_answer_uses_current_executor_boundaries():
    registry = {
        "nexus_mcp": {"handshake": "PASS", "tool_count": 25, "tools": ["gmail_search", "calendar_search_events", "drive_search"]},
        "google": {"authentication": "AUTH_REQUIRED", "read_tests": {"GMAIL": "AUTH_REQUIRED", "CALENDAR": "AUTH_REQUIRED", "DRIVE": "AUTH_REQUIRED"}},
        "hermes": {"toolset": ["nexus_mcp_remote", "you-com", "web"], "you_com_handshake": "PASS", "you_com_tool_count": 2},
        "capabilities": [
            {"capability": "browser_automation", "status": "KNOWN_BUT_INACTIVE", "current_blocker": "No approved browser route"},
            {"capability": "web_search", "status": "ACTIVE"},
            {"capability": "file_document_pdf", "status": "KNOWN_BUT_INACTIVE", "current_blocker": "Unscoped reads"},
            {"capability": "terminal", "status": "KNOWN_BUT_INACTIVE", "current_blocker": "Credential mount reachable"},
            {"capability": "code_execution", "status": "KNOWN_BUT_INACTIVE", "current_blocker": "Single-query policy denies arbitrary code"},
            {"capability": "google_workspace", "status": "AUTH_REQUIRED", "current_blocker": "OAuth refresh invalid_grant"},
        ],
    }
    browser_answer = summarize_capability_registry(registry, "Can you look at a website?")
    assert "Interactive browser automation is installed but inactive" in browser_answer
    assert "I can search the web" in browser_answer
    file_answer = summarize_capability_registry(registry, "Can you work with files?")
    assert "Hermes file tool is inactive" in file_answer
    code_answer = summarize_capability_registry(registry, "Can you run code for a diagnostic?")
    assert "route work to the governed Systems department" in code_answer
    assert "Direct Hermes terminal and code execution are inactive" in code_answer
    google_answer = summarize_capability_registry(registry, "What's my next appointment?")
    assert "shared Google authorization needs renewal" in google_answer


def test_capability_answer_uses_successful_live_google_reads():
    registry = {
        "nexus_mcp": {"handshake": "PASS", "tool_count": 25, "tools": ["gmail_search", "calendar_search_events", "drive_search"]},
        "google": {"authentication": "PASS", "read_tests": {"GMAIL": "READ_TEST_PASS", "CALENDAR": "READ_TEST_PASS", "DRIVE": "READ_TEST_PASS"}},
        "capabilities": [{"capability": "web_search", "status": "ACTIVE"}],
    }
    inventory = summarize_capability_registry(registry, "What tools do you actually have available right now?")
    appointment = summarize_capability_registry(registry, "What's my next appointment?")
    files = summarize_capability_registry(registry, "Can you work with files?")
    assert "Gmail, Calendar, and Drive read access is verified" in inventory
    assert "read-only access is currently verified" in appointment
    assert "authorization is currently verified" in files


def test_executor_question_includes_live_registry_context(monkeypatch):
    monkeypatch.setattr(live_capability_registry, "build_live_registry", lambda **_: {"nexus_mcp": {"handshake": "PASS"}, "capabilities": []})
    context = live_capability_registry.capability_context_for_request("Can you run code if Nexus needs a diagnostic?")
    assert "LIVE CAPABILITY REGISTRY" in context


def test_nexus_mcp_tool_count_query_does_not_probe_google(monkeypatch):
    calls = []
    monkeypatch.setattr(live_capability_registry, "build_live_registry", lambda **kwargs: (
        calls.append(kwargs) or {
            "nexus_mcp": {"handshake": "PASS", "tool_count": 26, "tools": []},
            "google": {"authentication": "NOT_TESTED", "read_tests": {}},
            "capabilities": [],
        }
    ))
    answer = live_capability_registry.render_capability_answer(
        "Use Nexus MCP only and tell me how many tools are currently available."
    )
    assert "26 tools" in answer
    assert calls == [{"probe_google": False, "force": True}]
