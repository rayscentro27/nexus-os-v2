"""Typed, remote-first GitHub tools for the existing Nexus MCP."""
from __future__ import annotations

from typing import Any

from .auth import authorize_action, authorize_read

GITHUB_REMOTE_TOOL_NAMES = (
    "github_remote_health", "github_remote_status", "github_remote_repo_info", "github_remote_read_readme",
    "github_remote_read_file", "github_remote_list_files", "github_remote_releases", "github_remote_current_commit",
    "github_remote_register_source", "github_remote_list_sources", "github_remote_monitor_status",
    "github_remote_check_source", "github_remote_get_changes", "github_remote_fetch_snapshot",
    "github_remote_snapshot_info", "github_remote_cleanup_snapshot", "github_remote_classify",
    "github_remote_route_change",
)


def _core():
    from scripts.github_remote import github_remote
    return github_remote


def _run(fn, *args, **kwargs) -> dict[str, Any]:
    try:
        return fn(*args, **kwargs)
    except (ValueError, RuntimeError) as exc:
        return {"status": "ERROR", "reason": str(exc)[:300]}


def register_github_remote_tools(mcp: Any) -> None:
    @mcp.tool(name="github_remote_health", description="Read Systems-owned GitHub Remote health, SQLite integrity, source/snapshot counts and safe API status. No credentials are returned.")
    def github_remote_health() -> dict[str, Any]:
        authorize_read("github_remote_health")
        return _run(_core().health)

    @mcp.tool(name="github_remote_status", description="Read remote monitor/source freshness, stale/failed source counts, rate-limit reporting policy and snapshot cleanup status.")
    def github_remote_status() -> dict[str, Any]:
        authorize_read("github_remote_status")
        return _run(_core().monitor_status)

    @mcp.tool(name="github_remote_repo_info", description="Read public or authorized GitHub repository metadata via GitHub REST API; never clones or executes code.")
    def github_remote_repo_info(repository: str) -> dict[str, Any]:
        authorize_read("github_remote_repo_info")
        return _run(_core().repo_info, repository)

    @mcp.tool(name="github_remote_read_readme", description="Read a bounded README remotely via GitHub API; no clone or local repository copy.")
    def github_remote_read_readme(repository: str, ref: str = "") -> dict[str, Any]:
        authorize_read("github_remote_read_readme")
        return _run(_core().read_readme, repository, ref)

    @mcp.tool(name="github_remote_read_file", description="Read one exact bounded repository file from a branch, tag or commit. No arbitrary URL or local write.")
    def github_remote_read_file(repository: str, path: str, ref: str = "") -> dict[str, Any]:
        authorize_read("github_remote_read_file")
        return _run(_core().read_file, repository, path, ref)

    @mcp.tool(name="github_remote_list_files", description="List a bounded repository tree remotely, optionally under one exact directory prefix.")
    def github_remote_list_files(repository: str, path: str = "", ref: str = "") -> dict[str, Any]:
        authorize_read("github_remote_list_files")
        return _run(_core().list_files, repository, path, ref)

    @mcp.tool(name="github_remote_releases", description="Read up to 20 GitHub release/tag records without downloading repository history.")
    def github_remote_releases(repository: str, limit: int = 10) -> dict[str, Any]:
        authorize_read("github_remote_releases")
        return _run(_core().releases, repository, limit)

    @mcp.tool(name="github_remote_current_commit", description="Return the current exact commit SHA for the default branch or a supplied ref.")
    def github_remote_current_commit(repository: str, ref: str = "") -> dict[str, Any]:
        authorize_read("github_remote_current_commit")
        return _run(_core().current_commit, repository, ref)

    @mcp.tool(name="github_remote_register_source", description="Register or update one exact repository for remote monitoring/routing. Local installation is always disabled; bounded to a typed owner and route.")
    def github_remote_register_source(repository: str, owner_engine: str, routing_target: str,
                                      monitor_enabled: bool = False, tracked_paths: list[str] | None = None,
                                      verification_required: bool = True, execution_mode: str = "READ_ONLY") -> dict[str, Any]:
        authorize_action("github_remote_register_source")
        return _run(_core().register_source, repository, owner_engine, routing_target,
                    monitor_enabled=monitor_enabled, tracked_paths=tracked_paths,
                    verification_required=verification_required, execution_mode=execution_mode)

    @mcp.tool(name="github_remote_list_sources", description="List registered GitHub sources with internal registry identifiers suppressed.")
    def github_remote_list_sources(owner_engine: str = "", limit: int = 100) -> dict[str, Any]:
        authorize_read("github_remote_list_sources")
        return _run(_core().list_sources, owner_engine, limit)

    @mcp.tool(name="github_remote_monitor_status", description="Read Systems-owned monitor status and sources requiring check; reports GitHub API limits without exposing credentials.")
    def github_remote_monitor_status() -> dict[str, Any]:
        authorize_read("github_remote_monitor_status")
        return _run(_core().monitor_status)

    @mcp.tool(name="github_remote_check_source", description="Check one registered source's exact current commit and record only compact changed-path metadata; does not copy repo content.")
    def github_remote_check_source(repository: str) -> dict[str, Any]:
        authorize_action("github_remote_check_source")
        return _run(_core().check_source, repository)

    @mcp.tool(name="github_remote_get_changes", description="Read compact commit-change events and routing metadata; no repository contents are copied downstream.")
    def github_remote_get_changes(repository: str = "", limit: int = 50) -> dict[str, Any]:
        authorize_read("github_remote_get_changes")
        return _run(_core().get_changes, repository, limit)

    @mcp.tool(name="github_remote_fetch_snapshot", description="Fetch an exact commit/tag tarball into temporary storage with 24-hour expiry. Does not unpack, execute or install repository code; no Git history.")
    def github_remote_fetch_snapshot(repository: str, exact_ref: str) -> dict[str, Any]:
        authorize_action("github_remote_fetch_snapshot")
        return _run(_core().fetch_snapshot, repository, exact_ref)

    @mcp.tool(name="github_remote_snapshot_info", description="Read provenance, exact commit, hash and expiry for one opaque temporary snapshot reference.")
    def github_remote_snapshot_info(snapshot_reference: str) -> dict[str, Any]:
        authorize_read("github_remote_snapshot_info")
        return _run(_core().snapshot_info, snapshot_reference)

    @mcp.tool(name="github_remote_cleanup_snapshot", description="Remove only expired exact snapshots created under Nexus's bounded GitHub temporary directory.")
    def github_remote_cleanup_snapshot(snapshot_reference: str = "") -> dict[str, Any]:
        authorize_action("github_remote_cleanup_snapshot")
        return _run(_core().cleanup_snapshots, snapshot_reference)

    @mcp.tool(name="github_remote_classify", description="Classify how a GitHub project can be used from remote metadata/README evidence. Never executes repository code or recommends local installation by default.")
    def github_remote_classify(repository: str, owner_engine: str = "SHARED", routing_target: str = "RESEARCH_ONLY") -> dict[str, Any]:
        authorize_read("github_remote_classify")
        return _run(_core().classify, repository, owner_engine, routing_target)

    @mcp.tool(name="github_remote_route_change", description="Prepare the newest compact monitored change for its registered owner; Research verification precedes opportunity/trading/creative routing. Does not bypass existing engine queues.")
    def github_remote_route_change(repository: str) -> dict[str, Any]:
        authorize_action("github_remote_route_change")
        return _run(_core().route_change, repository)

