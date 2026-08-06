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
