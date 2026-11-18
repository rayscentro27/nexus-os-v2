from __future__ import annotations

from services.nexus_mcp import auth
from services.nexus_mcp.github_remote_operator import GITHUB_REMOTE_TOOL_NAMES, register_github_remote_tools


class ToolCollector:
    def __init__(self):
        self.tools = {}
    def tool(self, *, name, description):
        def register(fn):
            self.tools[name] = fn
            return fn
        return register


def test_operator_registers_complete_typed_surface():
    collector = ToolCollector()
    register_github_remote_tools(collector)
    assert set(collector.tools) == set(GITHUB_REMOTE_TOOL_NAMES)
    assert len(collector.tools) == 18


def test_auth_classifies_remote_reads_and_bounded_state_actions():
    reads = {"github_remote_health", "github_remote_status", "github_remote_repo_info", "github_remote_read_readme",
             "github_remote_read_file", "github_remote_list_files", "github_remote_releases",
             "github_remote_current_commit", "github_remote_list_sources", "github_remote_monitor_status",
             "github_remote_get_changes", "github_remote_snapshot_info", "github_remote_classify"}
    writes = {"github_remote_register_source", "github_remote_check_source", "github_remote_fetch_snapshot",
              "github_remote_cleanup_snapshot", "github_remote_route_change"}
    for name in reads:
        auth.authorize_read(name)
    for name in writes:
        auth.authorize_action(name)


def test_arbitrary_tools_remain_denied():
    try:
        auth.authorize_action("github_remote_shell")
    except PermissionError:
        pass
    else:
        raise AssertionError("arbitrary action must remain denied")

