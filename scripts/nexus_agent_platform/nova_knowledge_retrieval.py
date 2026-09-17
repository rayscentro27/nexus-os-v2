"""Bounded, read-only knowledge-plane selection for Nova.

This module searches existing repository and Git sources on demand. It is not
a second knowledge store and deliberately returns small, provenance-labelled
excerpts instead of injecting the repository into every prompt.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MAX_REPO_RESULTS = 6
MAX_REPO_CONTEXT_CHARS = 9000
MAX_HISTORY_COMMITS = 6
MAX_HISTORY_CONTEXT_CHARS = 6000

_SENSITIVE_PATH_PARTS = {".env", ".env.local", ".env.production", "credentials", "secrets", "private", "node_modules"}
_SECRET_VALUE = re.compile(r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret|cookie)\s*[:=]\s*[^\s,;]+")


def classify_question_layers(text: str, history: list[dict[str, str]] | None = None) -> list[str]:
    """Return ordered retrieval planes using deterministic lexical signals."""
    current = re.sub(r"\s+", " ", str(text or "")).strip().lower()
    prior = " ".join(str(item.get("content", "")) for item in (history or [])[-6:] if isinstance(item, dict)).lower()
    combined = f"{current} {prior}".strip()
    layers: list[str] = []

    def add(value: str) -> None:
        if value not in layers:
            layers.append(value)

    if current in {"yes", "yes please", "sure", "tell me more", "go on", "continue"} or re.search(r"\b(?:tell me more|more about that|what about that|explain that|interested)\b", current):
        add("CONVERSATION_FOLLOWUP")
    if any(term in combined for term in ("what is running", "right now", "currently", "today", "live state", "scheduler", "runtime health", "active operations")):
        add("CURRENT_STATE")
    if any(term in combined for term in ("research", "mission", "project", "decision", "approval", "work order", "blocked", "department", "capabilit")):
        add("GOVERNED_BUSINESS_STATE")
    if any(term in current for term in ("architecture", "source code", "config", "configuration", "repository", "repo", "how does", "what is the code", "not using hermes")) or ("hermes" in current and any(term in current for term in ("admin", "runtime", "using", "moved"))):
        add("REPOSITORY_ARCHITECTURE")
    if any(term in current for term in ("what happened", "when did", "last week", "changed", "change history", "commit", "previous implementation", "why was", "moved to direct")):
        add("DEVELOPMENT_HISTORY")
    if not layers:
        add("CONVERSATION_CONTEXT" if history else "GENERAL_REASONING")
    return layers


def _safe_path(path: str) -> bool:
    parts = set(Path(path).parts)
    return not parts.intersection(_SENSITIVE_PATH_PARTS) and not path.endswith((".pem", ".key"))


def _redact(value: str) -> str:
    return _SECRET_VALUE.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)


def repository_search(query: str, *, max_results: int = MAX_REPO_RESULTS) -> dict[str, Any]:
    """Search relevant tracked source areas with bounded safe output."""
    terms = [term for term in re.findall(r"[A-Za-z0-9_/-]{4,}", query.lower()) if term not in {"what", "does", "have", "with", "that", "this", "from"}]
    terms = list(dict.fromkeys(terms))[:8]
    if not terms:
        return {"status": "NO_QUERY", "results": [], "source": "repository_rg_search"}
    pattern = "|".join(re.escape(term) for term in terms)
    roots = ["README.md", "docs", "config", "configs", "architecture", "scripts/nexus_agent_platform", "scripts/nova", "src/admin", "src/components", "reports/hermes_modernization", "reports/runtime"]
    try:
        result = subprocess.run(
            ["git", "grep", "-n", "-i", "-E", pattern, "--", *roots],
            cwd=ROOT, capture_output=True, text=True, timeout=12, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "UNAVAILABLE", "results": [], "source": "repository_rg_search"}
    results: list[str] = []
    for line in result.stdout.splitlines():
        path = line.split(":", 1)[0]
        if _safe_path(path):
            results.append(_redact(line[:900]))
        if len(results) >= max_results:
            break
    return {"status": "OK", "results": results, "source": "repository_rg_search", "terms": terms}


def development_history_search(query: str, *, max_commits: int = MAX_HISTORY_COMMITS) -> dict[str, Any]:
    """Return matching commit summaries and changed-file names, not huge diffs."""
    terms = [term for term in re.findall(r"[A-Za-z0-9_/-]{4,}", query.lower()) if term not in {"what", "does", "have", "with", "that", "this", "from"}]
    commits: list[dict[str, Any]] = []
    try:
        log = subprocess.run(["git", "log", "--all", "--date=short", "--format=%H%x09%ad%x09%s", "-n", "40"], cwd=ROOT, capture_output=True, text=True, timeout=8, check=False)
        for line in log.stdout.splitlines():
            parts = line.split("\t", 2)
            if len(parts) != 3:
                continue
            sha, date, subject = parts
            haystack = f"{subject} {date}".lower()
            if terms and not any(term in haystack for term in terms):
                continue
            files = subprocess.run(["git", "show", "--format=", "--name-only", sha], cwd=ROOT, capture_output=True, text=True, timeout=5, check=False).stdout.splitlines()
            commits.append({"commit": sha, "date": date, "subject": _redact(subject[:240]), "files": [item for item in files if item and _safe_path(item)][:12]})
            if len(commits) >= max_commits:
                break
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "UNAVAILABLE", "commits": [], "source": "git_log"}
    return {"status": "OK", "commits": commits, "source": "git_log", "terms": terms}


def retrieve_knowledge(query: str, layers: list[str]) -> dict[str, Any]:
    """Select only repository/history planes requested by the classifier."""
    result: dict[str, Any] = {"layers": layers, "repository": None, "development_history": None}
    if "REPOSITORY_ARCHITECTURE" in layers:
        result["repository"] = repository_search(query)
    if "DEVELOPMENT_HISTORY" in layers:
        result["development_history"] = development_history_search(query)
    return result


def format_knowledge_for_prompt(retrieval: dict[str, Any]) -> str:
    """Serialize selected knowledge planes into a compact prompt block."""
    blocks: list[str] = []
    repo = retrieval.get("repository") or {}
    if repo.get("results"):
        blocks.append("REPOSITORY KNOWLEDGE (documentation/code/config excerpts; structural, not live state):\n" + "\n".join(repo["results"]))
    history = retrieval.get("development_history") or {}
    if history.get("commits"):
        rows = [f"- {item['commit'][:12]} {item['date']} {item['subject']} | files: {', '.join(item['files'])}" for item in history["commits"]]
        blocks.append("DEVELOPMENT HISTORY (Git summaries; historical):\n" + "\n".join(rows))
    return "\n\n".join(blocks)[:MAX_REPO_CONTEXT_CHARS + MAX_HISTORY_CONTEXT_CHARS]
