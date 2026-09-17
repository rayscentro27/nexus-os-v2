"""Bounded, provenance-aware knowledge selection for the direct Nova runtime.

This read-only projection searches existing repository/Git/governed records; it
does not create a second store or inject the whole repository into a prompt.
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MAX_REPO_RESULTS = 6
MAX_REPO_CONTEXT_CHARS = 9000
MAX_HISTORY_COMMITS = 6
MAX_GOVERNED_RESULTS = 5
_STOP = {"what", "does", "have", "with", "that", "this", "from", "are", "can", "the", "and", "for", "you", "why", "how", "was"}
_SENSITIVE = {".env", ".env.local", ".env.production", "credentials", "secrets", "private", "node_modules"}
_SECRET = re.compile(r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret|cookie)\s*[:=]\s*[^\s,;]+")


def _intent(query: str) -> str:
    text = str(query or "").lower()
    if any(x in text for x in ("mcp", "gmail", "email", "calendar", "drive", "connected", "capability", "available")):
        return "CAPABILITY"
    if "stedman" in text or "mission" in text or "blocked" in text:
        return "GOVERNED_ENTITY"
    if "department" in text:
        return "DEPARTMENT"
    if any(x in text for x in ("hermes", "architecture", "runtime", "not using", "what happened to")):
        return "ARCHITECTURE_HISTORY"
    if any(x in text for x in ("when did", "last week", "commit", "changed", "change history")):
        return "DEVELOPMENT_HISTORY"
    return "GENERAL"


def classify_question_layers(text: str, history: list[dict[str, str]] | None = None) -> list[str]:
    current = re.sub(r"\s+", " ", str(text or "")).strip().lower()
    prior = " ".join(str(item.get("content", "")) for item in (history or [])[-6:] if isinstance(item, dict)).lower()
    combined = f"{current} {prior}"
    layers: list[str] = []
    def add(value: str) -> None:
        if value not in layers: layers.append(value)
    if current in {"yes", "yes please", "sure", "tell me more", "go on", "continue"} or re.search(r"\b(?:tell me more|more about that|what about that|explain that|interested)\b", current): add("CONVERSATION_FOLLOWUP")
    if any(x in combined for x in ("what is running", "right now", "currently", "today", "live state", "scheduler", "runtime health", "active operations")): add("CURRENT_STATE")
    if any(x in combined for x in ("research", "mission", "project", "decision", "approval", "work order", "blocked", "department", "capabilit")): add("GOVERNED_BUSINESS_STATE")
    if _intent(current) == "DEPARTMENT": add("DEPARTMENT_KNOWLEDGE")
    if _intent(current) in {"ARCHITECTURE_HISTORY", "DEVELOPMENT_HISTORY"}: add("REPOSITORY_ARCHITECTURE")
    if _intent(current) in {"ARCHITECTURE_HISTORY", "DEVELOPMENT_HISTORY"} or any(x in current for x in ("what happened", "when did", "last week", "changed", "commit", "previous implementation", "why was", "moved to direct")): add("DEVELOPMENT_HISTORY")
    if _intent(current) == "CAPABILITY": add("CURRENT_CAPABILITY_STATE")
    if not layers: add("CONVERSATION_CONTEXT" if history else "GENERAL_REASONING")
    return layers


def _terms(query: str) -> list[str]:
    text = str(query or "").lower()
    terms = [x for x in re.findall(r"[a-z0-9_/-]{4,}", text) if x not in _STOP]
    extra: list[str] = []
    if "department" in text: extra += ["department", "intelligence fabric", "readiness", "department router"]
    if "hermes" in text: extra += ["hermes", "nova_admin_server", "get_nova_graph", "llmgatewayadapter", "openrouter", "runtime"]
    if "stedman" in text: extra += ["stedman waiters", "blocked_external_final", "yt-dlp", "captions", "transcript", "audio acquisition"]
    return list(dict.fromkeys(terms + extra))[:18]


def _safe(path: str) -> bool:
    return not set(Path(path).parts).intersection(_SENSITIVE) and not path.endswith((".pem", ".key"))


def _redact(value: str) -> str:
    return _SECRET.sub(lambda m: f"{m.group(1)}=[REDACTED]", value)


def _candidate(path: str, excerpt: str, plane: str, source_type: str, score: float, current: str) -> dict[str, Any]:
    return {"path": path, "excerpt": _redact(excerpt[:900]), "source_plane": plane, "source_type": source_type, "generated_at": datetime.now(timezone.utc).isoformat(), "freshness": "current" if current == "CURRENT" else "historical", "canonicality": "canonical" if source_type in {"GOVERNED_RECORD", "DEPARTMENT_REGISTRY", "RUNTIME_SOURCE"} else "supporting", "question_relevance": round(min(1.0, max(0.0, score / 30)), 3), "current_vs_historical": current, "score": round(score, 2)}


def _governed_search(query: str) -> list[dict[str, Any]]:
    terms = _terms(query); found: list[dict[str, Any]] = []
    for rel in ("data/governed/research_v2_missions.jsonl", "data/governed/research_v2_mission_items.jsonl", "data/governed/research_v2_mission_reports.jsonl", "data/governed/research_v2_investigations.jsonl", "data/governed/research_v2_strategies.jsonl"):
        path = ROOT / rel
        if not path.exists(): continue
        try: rows = path.read_text(errors="ignore").splitlines()[-2500:]
        except OSError: continue
        for raw in rows:
            try: row = json.loads(raw)
            except json.JSONDecodeError: continue
            blob = json.dumps(row, ensure_ascii=False).lower(); hits = sum(1 for term in terms if term in blob)
            if hits: found.append(_candidate(rel, json.dumps(row, ensure_ascii=False), "GOVERNED_BUSINESS_STATE", "GOVERNED_RECORD", 18 + hits * 4, "CURRENT"))
    return sorted(found, key=lambda x: x["score"], reverse=True)[:MAX_GOVERNED_RESULTS]


def _department_search() -> list[dict[str, Any]]:
    """Project the canonical department registry without relying on nav labels."""
    path = ROOT / "data/runtime/nexus_department_registry.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    rows = payload.get("departments", []) if isinstance(payload, dict) else []
    result = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        projection = {key: row.get(key) for key in ("department_id", "name", "purpose", "status", "authority_class", "human_review_policy")}
        result.append(_candidate("data/runtime/nexus_department_registry.json", json.dumps(projection, ensure_ascii=False), "GOVERNED_BUSINESS_STATE", "DEPARTMENT_REGISTRY", 42, "CURRENT"))
    report = ROOT / "reports/rebuild/NEXUS_DEPARTMENT_INTELLIGENCE_FABRIC_R1_REPORT.md"
    if report.exists():
        try:
            text = report.read_text(errors="ignore")
            result.append(_candidate(str(report.relative_to(ROOT)), "Canonical department fabric report: " + " ".join(text.splitlines()[145:158]), "REPOSITORY_KNOWLEDGE", "REPOSITORY_EXCERPT", 34, "HISTORICAL"))
        except OSError:
            pass
    return result[:MAX_GOVERNED_RESULTS + 1]


def repository_search(query: str, *, max_results: int = MAX_REPO_RESULTS) -> dict[str, Any]:
    terms = _terms(query)
    if not terms: return {"status": "NO_QUERY", "results": [], "candidates": [], "source": "repository_rg_search"}
    pattern = "|".join(re.escape(x) for x in terms); candidates: list[dict[str, Any]] = []
    roots = ["README.md", "docs", "config", "configs", "scripts/nexus_agent_platform", "scripts/nova", "src/admin", "src/components", "reports/rebuild", "reports/hermes_modernization", "reports/runtime"]
    try:
        for root in roots:
            result = subprocess.run(["rg", "-n", "-i", "--with-filename", "-e", pattern, str(ROOT / root), "--glob", "!*.lock", "--glob", "!*.db", "--glob", "!data/runtime/**", "--glob", "!data/cache/**"], cwd=ROOT, capture_output=True, text=True, timeout=3, check=False)
            for line in result.stdout.splitlines()[:160]:
                raw_path = line.split(":", 1)[0]
                path = str(Path(raw_path).relative_to(ROOT)) if raw_path.startswith(str(ROOT)) else raw_path
                if not _safe(path): continue
                low = path.lower(); score = sum(3 for term in terms if term in low) + sum(2 for term in terms if term in line.lower())
                if path == "reports/rebuild/NEXUS_DEPARTMENT_INTELLIGENCE_FABRIC_R1_REPORT.md": score += 28
                if "nova_admin_server.py" in low or "nova.py" in low: score += 16
                if "reports/hermes_modernization/" in low and _intent(query) == "ARCHITECTURE_HISTORY": score -= 8
                candidates.append(_candidate(path, line, "REPOSITORY_KNOWLEDGE", "RUNTIME_SOURCE" if "nova_admin_server.py" in low else "REPOSITORY_EXCERPT", score, "HISTORICAL"))
            if len(candidates) >= 500: break
    except (OSError, subprocess.TimeoutExpired):
        if not candidates: return {"status": "UNAVAILABLE", "results": [], "candidates": [], "source": "repository_rg_search"}
    # Always inspect the exact runtime files for architecture questions.  This
    # avoids broad README matches crowding out the trace that proves the path.
    if _intent(query) == "ARCHITECTURE_HISTORY":
        trace_lines: list[str] = []
        for rel in ("scripts/nova/nova_admin_server.py", "scripts/nexus_agent_platform/agents/nova.py", "scripts/nexus_agent_platform/workflows/litellm_adapter.py"):
            path = ROOT / rel
            if not path.exists(): continue
            try: lines = path.read_text(errors="ignore").splitlines()
            except OSError: continue
            for number, line in enumerate(lines, 1):
                if any(term in line.lower() for term in ("get_nova_graph", "llmgatewayadapter", "openrouter", "nova_admin")):
                    trace_lines.append(f"{rel}:{number}: {line.strip()}")
        if trace_lines:
            candidates.append(_candidate("RUNTIME_ARCHITECTURE_TRACE", " ".join(trace_lines[:18]), "REPOSITORY_KNOWLEDGE", "RUNTIME_SOURCE", 90, "CURRENT"))
    candidates.sort(key=lambda x: x["score"], reverse=True); selected = candidates[:max_results]
    return {"status": "OK", "results": [x["path"] + ": " + x["excerpt"] for x in selected], "candidates": selected, "source": "repository_rg_search", "terms": terms}


def development_history_search(query: str, *, max_commits: int = MAX_HISTORY_COMMITS) -> dict[str, Any]:
    terms = _terms(query); commits: list[dict[str, Any]] = []
    try:
        log = subprocess.run(["git", "log", "--all", "--date=short", "--format=%H%x09%ad%x09%s", "-n", "80"], cwd=ROOT, capture_output=True, text=True, timeout=10, check=False)
        for line in log.stdout.splitlines():
            parts = line.split("\t", 2)
            if len(parts) != 3: continue
            sha, date, subject = parts; hits = sum(1 for term in terms if term in f"{subject} {date}".lower())
            if terms and not hits: continue
            files = subprocess.run(["git", "show", "--format=", "--name-only", sha], cwd=ROOT, capture_output=True, text=True, timeout=5, check=False).stdout.splitlines()
            commits.append({"commit": sha, "date": date, "subject": _redact(subject[:240]), "files": [x for x in files if x and _safe(x)][:12], "score": 12 + hits * 5})
            if len(commits) >= max_commits: break
    except (OSError, subprocess.TimeoutExpired): return {"status": "UNAVAILABLE", "commits": [], "source": "git_log"}
    return {"status": "OK", "commits": commits, "source": "git_log", "terms": terms}


def retrieve_knowledge(query: str, layers: list[str]) -> dict[str, Any]:
    intent = _intent(query); result: dict[str, Any] = {"layers": layers, "intent": intent, "repository": None, "development_history": None, "governed": None, "source_planes_used": [], "conflicts": []}
    if "DEPARTMENT_KNOWLEDGE" in layers or intent == "DEPARTMENT":
        result["governed"] = {"status": "OK", "candidates": _department_search(), "source": "department_registry"}
    elif any(x in layers for x in ("GOVERNED_BUSINESS_STATE",)) or intent == "GOVERNED_ENTITY":
        result["governed"] = {"status": "OK", "candidates": _governed_search(query), "source": "governed_jsonl"}
    if "DEPARTMENT_KNOWLEDGE" in layers or intent in {"DEPARTMENT", "ARCHITECTURE_HISTORY", "DEVELOPMENT_HISTORY"}: result["repository"] = repository_search(query)
    if "DEVELOPMENT_HISTORY" in layers or intent == "ARCHITECTURE_HISTORY": result["development_history"] = development_history_search(query)
    for key, plane in (("governed", "GOVERNED_BUSINESS_STATE"), ("repository", "REPOSITORY_KNOWLEDGE"), ("development_history", "DEVELOPMENT_HISTORY")):
        data = result.get(key) or {}
        if data.get("candidates") or data.get("commits"): result["source_planes_used"].append(plane)
    return result


def format_knowledge_for_prompt(retrieval: dict[str, Any]) -> str:
    blocks: list[str] = []; governed = retrieval.get("governed") or {}; repo = retrieval.get("repository") or {}; history = retrieval.get("development_history") or {}
    if governed.get("candidates"): blocks.append("GOVERNED BUSINESS RECORDS (canonical entity-specific evidence; prefer over generic summaries):\n" + "\n".join(f"- {x['path']}: {x['excerpt']}" for x in governed["candidates"]))
    if repo.get("candidates"): blocks.append("REPOSITORY KNOWLEDGE (architecture/documentation; structural, not live state):\n" + "\n".join(f"- {x['path']}: {x['excerpt']}" for x in repo["candidates"]))
    if history.get("commits"): blocks.append("DEVELOPMENT HISTORY (Git summaries; historical):\n" + "\n".join(f"- {x['commit'][:12]} {x['date']} {x['subject']} | files: {', '.join(x['files'])}" for x in history["commits"]))
    if retrieval.get("intent") == "ARCHITECTURE_HISTORY" and repo.get("candidates"):
        blocks.append("RUNTIME ARCHITECTURE READING: The Admin HTTP handler calls get_nova_graph(). The Nova graph calls LlmGatewayAdapter and the configured OpenRouter model. No Hermes Agent CLI/profile invocation appears in this Admin request path; the separate Hermes runtime must not be substituted for this direct path.")
    if blocks: blocks.append("SOURCE PRECEDENCE: exact governed records outrank generic summaries; current runtime truth outranks repository/history; repository architecture and Git explain historical behavior. Documented or historical capability never implies active runtime connectivity.")
    return "\n\n".join(blocks)[:MAX_REPO_CONTEXT_CHARS + 6000]
