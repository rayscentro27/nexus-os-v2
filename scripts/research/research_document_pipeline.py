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


def fetch(url: str, accept: str = "text/html") -> tuple[str, dict[str, Any]]:
    req = urllib.request.Request(url, headers={"User-Agent": "NexusResearch/1.0", "Accept": accept})
    with urllib.request.urlopen(req, timeout=25) as response:
        body = response.read()
        return body.decode("utf-8", "replace"), {"status": response.status, "content_type": response.headers.get("Content-Type", "")}


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
    _write(document_path, document)
    state = {"research_item_id": document["research_item_id"], "raw_content_hash": raw_hash, "normalized_content_hash": normalized_hash, "processing_status": "FULLY_PROCESSED", "processed_at": retrieved, "artifacts": [str(x.relative_to(ROOT)) for x in (raw_path, normalized_path, summary_path, extraction_path, score_path, provenance_path, document_path)]}
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


def web_page(url: str, source_id: str) -> dict[str, Any]:
    raw, headers = fetch(url)
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw, re.I | re.S)
    title = clean(title_match.group(1)) if title_match else urllib.parse.urlparse(url).netloc
    return process_document("web", source_id, url, title, raw, extra={"provider": "urllib", "provider_content_type": headers.get("content_type"), "raw_source_truncated": False, "chunking_applied": len(raw) > 12000})


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
