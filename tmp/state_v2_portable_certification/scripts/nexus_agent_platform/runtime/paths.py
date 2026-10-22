"""Canonical repository root and data path resolution.

This module provides a single source of truth for resolving paths inside the
Nexus repository, independent of the current working directory or caller
location.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def get_nexus_repo_root() -> Path:
    """Return the canonical repository root.

    Resolution order:
    1. NEXUS_REPO_ROOT environment variable, if it points to a valid repo.
    2. The directory containing this file, walked upward until a marker is found.
    3. Fail with a clear error if no valid root is found.
    """
    env_root = os.environ.get("NEXUS_REPO_ROOT")
    if env_root:
        candidate = Path(env_root).resolve()
        if _is_repo_root(candidate):
            return candidate

    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if _is_repo_root(parent):
            return parent

    raise RuntimeError(
        "Nexus repository root not found. Set NEXUS_REPO_ROOT or place this "
        "module inside the repository."
    )


def nexus_data_path(*parts: str) -> Path:
    """Return a path inside the repository's data/ directory."""
    return get_nexus_repo_root() / "data" / Path(*parts)


def nexus_research_state_root() -> Path:
    """Resolve durable Research state independently from an immutable release.

    Canonical checkouts retain their established ``data/`` store. Packaged
    releases default to the stable user state directory unless the service
    explicitly points at the existing canonical store or an isolated
    certification namespace.
    """
    configured = os.environ.get("NEXUS_RESEARCH_STATE_ROOT", "").strip()
    if configured:
        root = Path(configured).expanduser()
        if not root.is_absolute():
            raise ValueError("NEXUS_RESEARCH_STATE_ROOT_MUST_BE_ABSOLUTE")
        root = root.resolve()
    else:
        repo = get_nexus_repo_root()
        if (repo / "RELEASE_MANIFEST.sha256").is_file():
            root = Path.home() / ".nexus" / "state" / "research"
        else:
            root = repo / "data"
    repo = get_nexus_repo_root().resolve()
    if (repo / "RELEASE_MANIFEST.sha256").is_file() and root.resolve().is_relative_to(repo):
        raise ValueError("RESEARCH_RUNTIME_STATE_CANNOT_LIVE_INSIDE_IMMUTABLE_RELEASE")
    return root


def nexus_research_state_path(*parts: str) -> Path:
    """Return a contained path under the configured, version-independent state root."""
    root = nexus_research_state_root()
    relative = Path(*parts)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("RESEARCH_STATE_PATH_MUST_REMAIN_UNDER_STATE_ROOT")
    target = root / relative
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("RESEARCH_STATE_PATH_ESCAPES_STATE_ROOT")
    return target


def nexus_reports_path(*parts: str) -> Path:
    """Return a path inside the repository's reports/ directory."""
    return get_nexus_repo_root() / "reports" / Path(*parts)


def _is_repo_root(path: Path) -> bool:
    """Heuristic: a directory looks like the Nexus repo root."""
    return (
        (path / "data").is_dir()
        and (path / "scripts").is_dir()
        and (path / "reports").is_dir()
    )
