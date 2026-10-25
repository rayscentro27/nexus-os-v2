#!/usr/bin/env python3
"""Shared non-Alpha Research document processing.

This is deliberately local-first and report-only.  It does not call Alpha,
create opportunities/work orders, publish, or write Supabase records.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import urllib.parse
import urllib.request
import ssl
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from common import ROOT, score_research_text

ROOT_ARTIFACTS = ROOT / "reports" / "runtime" / "research_artifacts"
VERSION = "research-document-v1"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()


def clean(value: str) -> str:
    value = html.unescape(re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", value, flags=re.I))
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def sentences(text: str) -> list[str]:
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+", text) if len(x.strip()) > 45]


def matches(text: str, terms: list[str], limit: int = 5) -> list[str]:
    found = []
    for sentence in sentences(text):
        if any(term.lower() in sentence.lower() for term in terms) and sentence not in found:
            found.append(sentence[:600])
    return found[:limit] or ["NOT_PRESENT"]


def extract(text: str, source_type: str) -> dict[str, Any]:
    fields = {
        "company_organization": ["company", "organization", "inc.", "llc"],
        "products_services": ["product", "service", "platform", "course", "tool"],
        "pricing": ["price", "pricing", "$", "per month", "cost"],
        "revenue_claims": ["revenue", "profit", "made $", "million", "per month"],
        "marketing_methods": ["marketing", "content", "audience", "campaign", "seo"],
        "lead_generation": ["lead", "funnel", "traffic", "customer", "signup"],
        "sales_methods": ["sales", "sell", "offer", "conversion", "checkout"],
        "tools_platforms": ["github", "api", "python", "javascript", "youtube", "google", "open source"],
        "technologies_ai_methods": ["ai", "automation", "model", "agent", "machine learning"],
        "seo_methods": ["seo", "keyword", "search intent", "serp", "backlink", "schema"],
        "funding_credit": ["funding", "loan", "credit", "lender", "grant"],
        "real_estate": ["real estate", "property", "housing", "mortgage"],
        "compliance_references": ["compliance", "legal", "regulation", "policy", "privacy", "license"],
        "risks": ["risk", "limitation", "caveat", "security", "warning", "cost"],
        "tactics_recommendations": ["should", "recommend", "step", "method", "use", "implement"],
    }
    result = {key: matches(text, terms) for key, terms in fields.items()}
    result["follow_up_questions"] = [
        "Which substantive claims require independent primary-source verification?",
        "What implementation, security, licensing, or compliance constraints apply?",
    ]
    result["source_specific_type"] = source_type
    return result


def fetch(url: str, accept: str = "text/html", *, max_bytes: int = 750_000) -> tuple[str, dict[str, Any]]:
    # Research retrieval is a provider call too. Enforce durable-job identity,
    # reservation, and footprint before opening a socket; unknown hosts deny.
    import os
    from urllib.parse import urlsplit
    from nexus_agent_platform.provider_enforcement import execute
    parsed_url=urlsplit(url)
    host = (parsed_url.hostname or "").lower()
    if parsed_url.scheme not in {"http","https"} or not host:
        raise ValueError("RESEARCH_SOURCE_URL_INVALID")
    if host.endswith("github.com") or host == "api.github.com":
        provider = "GITHUB"
    elif host.endswith("youtube.com") or host.endswith("googleapis.com"):
        provider = "GOOGLE"
    elif host.endswith("supabase.co") or host.endswith("supabase.com"):
        provider = "SUPABASE"
    else:
        provider = "PUBLIC_WEB"

    def request():
        req = urllib.request.Request(url, headers={"User-Agent": "NexusResearch/1.0", "Accept": accept})
        context = None
        try:
            import certifi
            context = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            context = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=25, context=context) as response:
            body = response.read(max(1, int(max_bytes)))
            return body.decode("utf-8", "replace"), {"status": response.status, "content_type": response.headers.get("Content-Type", ""),
                "raw_source_truncated": len(body) >= max(1, int(max_bytes)), "response_bytes": len(body)}

    # A retry of a safe GET under the same durable job must receive a fresh
    # reservation identity after a prior response was a 404/transport failure.
    # Keep same-attempt duplicate reads deduplicated, while allowing the
    # controller's explicit next attempt to re-fetch its repaired source.
    attempt = os.environ.get("NEXUS_JOB_ATTEMPT_COUNT", "1")
    url_fingerprint = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return execute(
        provider, host, "RESEARCH_READ",
        # Public, read-only HTML retrieval has zero incremental charge. Marking
        # it billable caused the governor to reject this path even though its
        # estimated and actual cash costs are both zero.
        {"requests": 1, "api_calls": 1, "bytes": max(1, int(max_bytes)), "billable": False, "cost": 0},
        request, job_id=os.environ.get("NEXUS_DURABLE_JOB_ID"),
        job_type=os.environ.get("NEXUS_JOB_TYPE"),
        correlation_id=os.environ.get("NEXUS_CORRELATION_ID"),
        purpose=f"RESEARCH_READ:{host}:{url_fingerprint}:attempt:{attempt}",
        actual_usage=lambda result: {"requests":1,"api_calls":1,
                                     "bytes":int((result[1] or {}).get("response_bytes",len(result[0].encode("utf-8")))),
                                     "cost":0},
    )


def _write(path: Path, value: Any, text_mode: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if text_mode else json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def process_document(source_type: str, source_id: str, url: str, title: str, raw: str, *, author: str = "", published_at: str | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    source_dir = ROOT_ARTIFACTS / source_type.lower().replace("-", "_")
    base = source_dir / re.sub(r"[^A-Za-z0-9_.-]+", "_", source_id)[:120]
    normalized = clean(raw)
    raw_hash, normalized_hash = digest(raw), digest(normalized)
    state_path = base.with_suffix(".state.json")
    if state_path.exists():
        prior = json.loads(state_path.read_text())
        if prior.get("raw_content_hash") == raw_hash and prior.get("normalized_content_hash") == normalized_hash and prior.get("processing_status") == "FULLY_PROCESSED":
            return {**prior, "duplicate_status": "DUPLICATE_UNCHANGED", "processing_status": "DUPLICATE_UNCHANGED", "new_artifact_set_created": False}
    parts = [normalized[i:i + 12000] for i in range(0, len(normalized), 12000)] or [""]
    overview = " ".join(parts[:8])
    lines = sentences(overview)
    topic = "SEO/search demand" if source_type.lower() == "seo" else "GitHub repository architecture" if source_type.lower() == "github" else "web source intelligence"
    summary = {
        "executive_summary": (lines[0] if lines else normalized[:500])[:700],
        "main_topic": topic,
        "key_themes": [x for x, terms in (("architecture", ["architecture", "workflow", "pipeline"]), ("recency", ["recent", "last 30", "date"]), ("SEO", ["seo", "keyword", "search"]), ("security", ["security", "permission", "token"])) if any(t in normalized.lower() for t in terms)] or ["source content"],
        "key_findings": lines[:8] or ["NOT_PRESENT"],
        "unanswered_questions": ["What independent evidence supports the material claims?", "What changed since the retrieval date?"],
        "content_segments": len(parts),
    }
    extraction = extract(overview, source_type)
    scores = score_research_text(f"{title} {overview}", topic)
    priority = "HIGH" if scores["overall_score"] >= 75 else "MEDIUM" if scores["overall_score"] >= 50 else "LOW"
    disposition = "DEEP_RESEARCH" if source_type.lower() == "github" else "FOLLOW_UP_RESEARCH" if priority == "HIGH" else "MONITOR"
    retrieved = now()
    raw_path, normalized_path = base.with_suffix(".raw.txt"), base.with_suffix(".normalized.txt")
    summary_path, extraction_path = base.with_suffix(".summary.json"), base.with_suffix(".extraction.json")
    score_path, provenance_path = base.with_suffix(".score.json"), base.with_suffix(".provenance.json")
    _write(raw_path, raw, True); _write(normalized_path, normalized, True); _write(summary_path, summary); _write(extraction_path, extraction); _write(score_path, {"scores": scores, "priority": priority, "disposition": disposition})
    provenance = [{"source_url": url, "content_hash": raw_hash, "content_segment_id": i, "source_text_or_bounded_excerpt": part[:800], "retrieved_at": retrieved} for i, part in enumerate(parts[:8])]
    _write(provenance_path, {"references": provenance})
    document = {"research_item_id": f"{source_type.lower()}:{source_id}", "source_type": source_type, "source_id": source_id, "source_url": url, "source_title": title, "source_author_or_channel": author, "published_at": published_at, "discovered_at": retrieved, "retrieved_at": retrieved, "processed_at": retrieved, "raw_content_path": str(raw_path.relative_to(ROOT)), "raw_content_hash": raw_hash, "normalized_content_path": str(normalized_path.relative_to(ROOT)), "normalized_content_hash": normalized_hash, "processing_status": "FULLY_PROCESSED", "processing_version": VERSION, "executive_summary": summary["executive_summary"], "main_topic": topic, "key_themes": summary["key_themes"], "key_findings": summary["key_findings"], "structured_data": extraction, "classification": topic, "scores": scores, "priority": priority, "research_disposition": disposition, "evidence_references": provenance, "provenance": provenance, "risks": extraction["risks"], "limitations": ["Deterministic bounded synthesis; no external AI invoked."], "unknowns": ["Independent validation not performed."], "follow_up_questions": extraction["follow_up_questions"], "novelty_status": "UNASSESSED", "duplicate_status": "NEW", **(extra or {})}
    document_path = base.with_suffix(".document.json")
    follow_up_path = base.with_suffix(".follow-ups.json")
    if disposition in {"FOLLOW_UP_RESEARCH", "DEEP_RESEARCH"}:
        _write(follow_up_path, {"parent_research_item_id": f"{source_type.lower()}:{source_id}", "status": "OPEN", "questions": extraction["follow_up_questions"], "created_at": retrieved, "alpha_invoked": False, "department_handoff": False})
    _write(document_path, document)
    artifacts = (raw_path, normalized_path, summary_path, extraction_path, score_path, provenance_path, document_path) + ((follow_up_path,) if follow_up_path.exists() else ())
    state = {"research_item_id": document["research_item_id"], "raw_content_hash": raw_hash, "normalized_content_hash": normalized_hash, "processing_status": "FULLY_PROCESSED", "processed_at": retrieved, "artifacts": [str(x.relative_to(ROOT)) for x in artifacts]}
    _write(state_path, state)
    return {**document, "new_artifact_set_created": True, "artifact_paths": state["artifacts"]}


def github_deep(repo: str) -> dict[str, Any]:
    meta_raw, _ = fetch(f"https://api.github.com/repos/{repo}", "application/vnd.github+json")
    meta = json.loads(meta_raw)
    branch = meta.get("default_branch", "main")
    tree_raw, _ = fetch(f"https://api.github.com/repos/{repo}/git/trees/{urllib.parse.quote(branch)}?recursive=1", "application/vnd.github+json")
    tree = json.loads(tree_raw).get("tree", [])
    important = [x for x in tree if x.get("type") == "blob" and (Path(x.get("path", "")).name.lower() in {"readme.md", "skill.md", "pyproject.toml", "package.json", "requirements.txt", "setup.py", "workflow.yml", "workflow.yaml"} or x.get("path", "").startswith(("docs/", ".github/workflows/")) or Path(x.get("path", "")).suffix in {".py", ".ts"})][:20]
    files = []
    for item in important[:12]:
        try:
            raw, _ = fetch(f"https://raw.githubusercontent.com/{repo}/{branch}/{urllib.parse.quote(item['path'])}", "text/plain")
            files.append({"path": item["path"], "sha": item.get("sha"), "content": raw[:18000]})
        except Exception as exc:
            files.append({"path": item["path"], "sha": item.get("sha"), "error": str(exc)})
    raw = "\n".join([f"Repository: {meta.get('full_name', repo)}", f"Description: {meta.get('description', '')}", f"Default branch: {branch}", f"Tree files: {len(tree)}", "", "Selected files and contents:", *[f"\n## {x['path']} (sha {x.get('sha')})\n{x.get('content', x.get('error', ''))}" for x in files]])
    return process_document("github", repo.replace("/", "__"), f"https://github.com/{repo}", meta.get("full_name", repo), raw, author=meta.get("owner", {}).get("login", ""), published_at=meta.get("created_at"), extra={"repo_tree_summary": {"file_count": len(tree), "default_branch": branch, "description": meta.get("description")}, "important_files_selected": [x["path"] for x in files], "file_hashes": {x["path"]: x.get("sha") for x in files}, "repo_commit_sha": meta.get("pushed_at")})


def web_page(url: str, source_id: str, *, max_bytes: int = 750_000) -> dict[str, Any]:
    # A failed canonical persistence retry must reuse the source bytes already
    # acquired by Research. Re-fetching would consume provider budget and can
    # hit the same idempotency guard without improving the evidence.
    source_dir = ROOT_ARTIFACTS / "web"
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", source_id)[:120]
    state_path = source_dir / f"{safe_id}.state.json"
    document_path = source_dir / f"{safe_id}.document.json"
    raw_path = source_dir / f"{safe_id}.raw.txt"
    cached = None
    try:
        prior = json.loads(state_path.read_text(encoding="utf-8"))
        document = json.loads(document_path.read_text(encoding="utf-8"))
        retrieved = datetime.fromisoformat(str(document.get("retrieved_at", "")).replace("Z", "+00:00"))
        if retrieved.tzinfo is None:
            retrieved = retrieved.replace(tzinfo=timezone.utc)
        fresh = datetime.now(timezone.utc) - retrieved <= timedelta(hours=24)
        if (fresh and prior.get("processing_status") == "FULLY_PROCESSED"
                and document.get("source_url") == url and raw_path.is_file()):
            cached = raw_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError, TypeError):
        cached = None
    if cached is None:
        raw, headers = fetch(url, max_bytes=max_bytes)
        provider = "urllib"
        content_type = headers.get("content_type")
    else:
        raw = cached
        provider = "NEXUS_RESEARCH_CACHE"
        content_type = "cached-source-artifact"
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw, re.I | re.S)
    title = clean(title_match.group(1)) if title_match else urllib.parse.urlparse(url).netloc
    processed = process_document("web", source_id, url, title, raw, extra={"provider": provider, "provider_content_type": content_type, "cached_source_reused": cached is not None, "raw_source_truncated": bool(headers.get("raw_source_truncated", False)), "chunking_applied": len(raw) > 12000})
    if processed.get("duplicate_status") == "DUPLICATE_UNCHANGED":
        try:
            prior_document = json.loads(document_path.read_text(encoding="utf-8"))
            return {**prior_document, **processed, "cached_source_reused": cached is not None}
        except (OSError, ValueError, TypeError):
            pass
    return processed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--github", action="append", default=[])
    parser.add_argument("--web", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    results = [github_deep(repo) for repo in args.github] + [web_page(url, f"web-{i}") for i, url in enumerate(args.web, 1)]
    print(json.dumps({"ok": True, "alpha_invoked": False, "supabase_persistence": False, "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
