from __future__ import annotations

import re
from html.parser import HTMLParser

import pytest

from nexus_agent_platform.research_parent_adapters import _extract_public_html
from nexus_agent_platform.research_only_execution import (
    HANDOFF_MAX_BYTES, SELECTED_EVIDENCE_MAX_BYTES, _answer_excerpt,
    assignment_anchors, compact_handoff, execute_research_only,
)


PATHLIB_QUESTION = (
    "According to the official Python documentation, what does "
    "pathlib.Path.is_file() return when the path does not exist?"
)


def _pathlib_html() -> str:
    filler = "General pathlib module introduction and examples. " * 280
    return f"""<!doctype html><html><head><title>pathlib docs</title></head><body>
    <nav><h2>Table of Contents</h2><a>Path.is_file() examples</a></nav>
    <aside class="sidebar">Sidebar mentions Path.is_file() but not its answer.</aside>
    <main><h1>pathlib — Object-oriented filesystem paths</h1>
    <p>{filler}</p>
    <section id="pathlib.Path.is_file">
      <dl class="py method">
        <dt id="pathlib.Path.is_file"><code>Path.is_file()</code></dt>
        <dd><p>Return <code>True</code> if the path points to a regular file. Return
        <code>False</code> if the path does not exist or is a broken symbolic link.</p></dd>
      </dl>
    </section>
    <section id="pathlib.Path.is_dir"><dl><dt id="pathlib.Path.is_dir">Path.is_dir()</dt>
      <dd><p>Return False if the path does not exist or is not a directory.</p></dd></dl></section>
    </main></body></html>"""


def _legacy_r57_excerpt(question: str, text: str) -> str:
    """Offline reproduction of R57's token-overlap selector and 12KB truncation."""
    stop = {"according", "official", "documentation", "document", "what", "does", "do",
            "return", "returns", "when", "the", "a", "an", "to", "for", "of", "in", "on",
            "this", "that", "is", "are", "be", "it", "path"}
    terms = {token for token in re.findall(r"[a-z0-9_]+", question.casefold())
             if len(token) > 2 and token not in stop}
    identifiers = {value.casefold() for value in re.findall(
        r"\b(?:[A-Za-z_]\w*\.)+[A-Za-z_]\w*\b", question)}
    terms.update(identifiers)
    sentences = [" ".join(part.split()) for part in
        re.split(r"(?<=[.!?])\s+|\s{2,}", text[:12000]) if part.strip()]
    ranked = []
    for index, sentence in enumerate(sentences):
        score = sum(1 for term in terms if term in sentence.casefold())
        if score:
            ranked.append((score, -index, sentence))
    return " ".join(item[2] for item in sorted(ranked, reverse=True)[:3])[:1200]


def test_r57_excerpt_failure_is_reproduced_from_long_pathlib_page_fixture():
    class _LegacyFlatten(HTMLParser):
        def __init__(self):
            super().__init__()
            self.skipped = 0
            self.parts = []
        def handle_starttag(self, tag, attrs):
            if tag in {"script", "style", "noscript", "svg"}:
                self.skipped += 1
        def handle_endtag(self, tag):
            if tag in {"script", "style", "noscript", "svg"} and self.skipped:
                self.skipped -= 1
        def handle_data(self, data):
            if not self.skipped and data.strip():
                self.parts.append(data.strip())
    legacy = _LegacyFlatten()
    legacy.feed(_pathlib_html())
    old = _legacy_r57_excerpt(PATHLIB_QUESTION, " ".join(legacy.parts))
    assert old
    assert "Table of Contents" in old
    assert "Path.is_file" in old
    assert "False" not in old


def test_r58_golden_pathlib_result_selects_method_definition_and_answers_question():
    parsed = _extract_public_html(_pathlib_html())
    result = _answer_excerpt(PATHLIB_QUESTION, parsed["text"], parsed["sections"])
    assert result
    assert "Path.is_file" in result
    assert "does not exist" in result
    assert "False" in result
    assert len(result.encode("utf-8")) <= SELECTED_EVIDENCE_MAX_BYTES


@pytest.mark.parametrize(("question", "symbol", "answer"), [
    ("What does pathlib.Path.exists() return for a broken symbolic link?",
     "Path.exists", "False"),
    ("What does pathlib.Path.is_dir() return when the path does not exist?",
     "Path.is_dir", "False"),
    ("What does pathlib.Path.is_symlink() return when the path does not exist?",
     "Path.is_symlink", "False"),
    ("What does pathlib.Path.is_file() return when the path does not exist?",
     "Path.is_file", "False"),
])
def test_selector_prefers_exact_pathlib_api_section(question, symbol, answer):
    method = symbol.split(".")[-1]
    html = f"""<nav><h2>Table of Contents</h2><p>{symbol} navigation link</p></nav>
      <section id="pathlib.{symbol.split('.')[-1]}"><dl>
      <dt id="pathlib.{symbol}">{symbol}()</dt><dd><p>Return {answer} if the path does not exist or is a broken symbolic link.</p></dd>
      </dl></section>"""
    parsed = _extract_public_html(html)
    result = _answer_excerpt(question, parsed["text"], parsed["sections"])
    assert result and symbol in result and answer in result
    assert method in assignment_anchors(question)["method"]
    assert "Table of Contents" not in result


def test_structural_normalizer_excludes_navigation_sidebar_and_toc():
    parsed = _extract_public_html(_pathlib_html())
    # The legacy flat-text field remains byte-compatible for parent workflow
    # consumers; the Research-only structured blocks omit chrome.
    assert "Table of Contents" in parsed["text"]
    assert "Sidebar mentions" in parsed["text"]
    assert all("Table of Contents" not in block["text"] for block in parsed["sections"])
    assert all("Sidebar mentions" not in block["text"] for block in parsed["sections"])


def test_matching_api_definition_outranks_generic_page_introduction():
    parsed = _extract_public_html(_pathlib_html())
    result = _answer_excerpt(PATHLIB_QUESTION, parsed["text"], parsed["sections"])
    assert result.index("Path.is_file") < result.index("Return")
    assert "General pathlib module introduction" not in result


def test_condition_from_assignment_must_be_covered():
    question = "What does Path.is_file() return when the path does not exist?"
    relevant = "Path.is_file() returns False when the path does not exist."
    unrelated = "Path.is_file() returns True when the path points to a regular file."
    assert _answer_excerpt(question, relevant)
    assert _answer_excerpt(question, unrelated) is None


def test_generic_python_standard_library_api_fixture():
    question = "According to Python documentation, what does os.path.exists() return for a missing path?"
    html = "<dl><dt id='os.path.exists'>os.path.exists(path)</dt><dd><p>Return False if the path does not exist.</p></dd></dl>"
    parsed = _extract_public_html(html)
    answer = _answer_excerpt(question, parsed["text"], parsed["sections"])
    assert answer and "os.path.exists" in answer and "False" in answer


def test_non_python_documentation_api_fixture():
    question = "What does the Response.ok property indicate for an HTTP response?"
    html = "<section id='Response.ok'><h3>Response.ok</h3><p>This property returns True if status is below 400.</p></section>"
    parsed = _extract_public_html(html)
    answer = _answer_excerpt(question, parsed["text"], parsed["sections"])
    assert answer and "Response.ok" in answer and "below 400" in answer


def test_weak_source_returns_no_answer_instead_of_fabricating():
    question = "What does Path.is_file() return when the path does not exist?"
    weak = "The pathlib module provides object-oriented filesystem paths."
    assert _answer_excerpt(question, weak) is None


def test_research_only_executes_one_adapter_call_and_persists_insufficient_evidence(monkeypatch):
    from research import research_case_engine, proactive_research_memory
    from nexus_agent_platform import research_parent_adapters
    reads, saves = [], []
    monkeypatch.setattr(research_case_engine, "open_or_join_case", lambda **_: {"case": {"case_id": "case-r58"}})
    monkeypatch.setattr(research_case_engine, "add_source", lambda *_: {"ok": True})
    monkeypatch.setattr(research_case_engine, "record_research_only_result", lambda *_args, **_kwargs: {"ok": True})
    monkeypatch.setattr(research_parent_adapters, "_fallback_public_page", lambda *_: reads.append(1) or {
        "url": "https://docs.python.org/3/library/pathlib.html", "text": "Path.is_file() returns True for a regular file.",
        "sections": [], "bytes": 100, "status": "COMPLETED"})
    monkeypatch.setattr(proactive_research_memory, "persist_state", lambda row: saves.append(dict(row)) or row)
    from nexus_agent_platform import evidence_ingestion
    monkeypatch.setattr(evidence_ingestion, "validate_public_url", lambda url: (url, None))
    work = {"work_id": "w", "objective_id": "o", "project_id": "p", "original_objective": "Bounded API research",
            "question": "What does Path.is_file() return when the path does not exist?",
            "source_url": "https://docs.python.org/3/library/pathlib.html", "requested_intent": "RESEARCH_ONLY"}
    result = execute_research_only(work, job_id="job-r58")
    assert len(reads) == 1
    assert result["status"] == "BLOCKED"
    assert result["research_result"]["result_status"] == "SOURCE_INSUFFICIENT"
    assert "no answer was inferred" in result["research_result"]["summary"].lower()
    assert saves and len(saves[-1]["summary"].encode()) < SELECTED_EVIDENCE_MAX_BYTES


def test_compact_handoff_from_golden_selection_answers_question_and_stays_bounded():
    parsed = _extract_public_html(_pathlib_html())
    answer = _answer_excerpt(PATHLIB_QUESTION, parsed["text"], parsed["sections"])
    assert answer and "False" in answer and "does not exist" in answer
    handoff = compact_handoff(job_id="j", objective_id="o", project_id="p", case_id="c",
        question=PATHLIB_QUESTION, summary=answer, evidence_refs=["https://docs.python.org/3/library/pathlib.html"])
    encoded = __import__("json").dumps(handoff, ensure_ascii=False, separators=(",", ":")).encode()
    assert "False" in handoff["summary"] and "does not exist" in handoff["summary"]
    assert len(encoded) <= HANDOFF_MAX_BYTES
    assert "source_body" not in handoff and "transcript" not in handoff
