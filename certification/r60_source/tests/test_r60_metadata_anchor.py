from __future__ import annotations

import pytest

from nexus_agent_platform.research_only_execution import (
    _answer_excerpt,
    _strip_source_policy_metadata,
    assignment_anchors,
    execute_research_only,
)
from nexus_agent_platform.research_parent_adapters import _extract_public_html


QUESTION = (
    "According to the official Python documentation, what does "
    "pathlib.Path.is_file() return when the path does not exist?"
)
SOURCE_URL = "https://docs.python.org/3/library/pathlib.html"
ANNOTATED_QUESTION = QUESTION + " Allowed source URL: " + SOURCE_URL


def _fixture() -> dict:
    html = f"""<html><body>
    <nav><h2>Table of Contents</h2><p>Path.is_file() navigation</p></nav>
    <main><section id="pathlib.Path.is_file"><dl>
      <dt id="pathlib.Path.is_file"><code>Path.is_file()</code></dt>
      <dd><p>Return <code>True</code> if the path points to a regular file.
      Return <code>False</code> if the path does not exist or is a broken symbolic link.</p></dd>
    </dl></section></main></body></html>"""
    return _extract_public_html(html)


@pytest.mark.parametrize("label", ["Allowed source URL:", "Approved source URL:"])
def test_exact_stored_assignment_shape_selects_grounded_pathlib_definition(label):
    question = QUESTION + f" {label} {SOURCE_URL}"
    parsed = _fixture()
    anchors = assignment_anchors(question)
    selected = _answer_excerpt(question, parsed["text"], parsed["sections"])
    assert anchors["condition_tokens"] == {"not", "exist"}
    assert selected and "Path.is_file()" in selected
    assert "False" in selected and "does not exist" in selected
    assert "Table of Contents" not in selected
    # The original assignment value remains unchanged for storage and source-policy handling.
    assert question == QUESTION + f" {label} {SOURCE_URL}"


def test_r59_failure_is_reproduced_with_pre_fix_anchor_input(monkeypatch):
    import nexus_agent_platform.research_only_execution as execution

    monkeypatch.setattr(execution, "_strip_source_policy_metadata", lambda value: str(value or ""))
    anchors = assignment_anchors(ANNOTATED_QUESTION)
    assert anchors["condition_tokens"] == {"allowed", "exist", "not", "source", "url"}
    parsed = _fixture()
    assert _answer_excerpt(ANNOTATED_QUESTION, parsed["text"], parsed["sections"]) is None


@pytest.mark.parametrize("question", [
    "The source is allowed only when Path.is_file() returns False when the path does not exist.",
    "A source URL is allowed when Path.is_file() returns False when the path does not exist.",
])
def test_ordinary_source_and_allowed_prose_are_not_stripped(question):
    assert _strip_source_policy_metadata(question) == question
    anchors = assignment_anchors(question)
    assert "not" in anchors["condition_tokens"]
    assert "exist" in anchors["condition_tokens"]


def test_user_url_content_and_non_metadata_text_are_not_stripped():
    question = "Path.is_file() returns False when the path does not exist; see " + SOURCE_URL
    assert _strip_source_policy_metadata(question) == question
    assert assignment_anchors(question)["condition_tokens"] == {"not", "exist", "see"}


def test_unrecognized_source_label_is_not_stripped():
    question = QUESTION + " Allowed source: " + SOURCE_URL
    assert _strip_source_policy_metadata(question) == question


def test_recognized_label_inside_ordinary_prose_is_not_stripped():
    question = QUESTION + " The phrase Allowed source URL: " + SOURCE_URL + " is being discussed here."
    assert _strip_source_policy_metadata(question) == question


def test_execution_preserves_stored_assignment_and_source_validation(monkeypatch):
    from nexus_agent_platform import evidence_ingestion, research_parent_adapters
    from research import research_case_engine, proactive_research_memory

    original_question = ANNOTATED_QUESTION
    work = {"work_id": "project-r60", "objective_id": "objective-r60",
        "project_id": "project-r60", "original_objective": "Bounded API lookup",
        "question": original_question, "source_url": SOURCE_URL,
        "requested_intent": "RESEARCH_ONLY"}
    original_work = dict(work)
    case_calls, validated, reads, persisted = [], [], [], []
    monkeypatch.setattr(research_case_engine, "open_or_join_case", lambda **kwargs:
        case_calls.append(kwargs) or {"case": {"case_id": "case-r60"}})
    monkeypatch.setattr(research_parent_adapters, "_fallback_public_page", lambda *_args, **_kwargs:
        reads.append(1) or {"url": SOURCE_URL, "title": "docs", "text": "generic pathlib intro",
                            "sections": [], "bytes": 128, "status": "COMPLETED"})
    monkeypatch.setattr(evidence_ingestion, "validate_public_url", lambda url:
        validated.append(url) or (url, None))
    monkeypatch.setattr(proactive_research_memory, "persist_state", lambda row:
        persisted.append(dict(row)) or row)

    result = execute_research_only(work, job_id="job-r60-metadata")
    assert result["research_result"]["result_status"] == "SOURCE_INSUFFICIENT"
    assert len(reads) == 1
    assert validated == [SOURCE_URL]
    assert case_calls[0]["primary_question"] == original_question
    assert work == original_work
    assert persisted


@pytest.mark.parametrize(("question", "symbol", "answer", "condition"), [
    ("What does pathlib.Path.exists() return for a broken symbolic link?", "Path.exists", "False", "broken"),
    ("What does pathlib.Path.is_dir() return when the path does not exist?", "Path.is_dir", "False", "exist"),
    ("What does pathlib.Path.is_symlink() return when the path does not exist?", "Path.is_symlink", "False", "exist"),
    ("What does os.path.exists() return for a missing path?", "os.path.exists", "False", "missing"),
    ("What does Response.ok indicate for an HTTP response?", "Response.ok", "True", "below 400"),
])
def test_generalized_api_question_fixtures(question, symbol, answer, condition):
    if symbol == "Path.exists":
        body = "Path.exists() returns False for a broken symbolic link."
    elif symbol == "os.path.exists":
        body = "os.path.exists() returns False when the path is missing."
    elif symbol == "Response.ok":
        body = "Response.ok returns True when the status code is below 400."
    else:
        body = f"{symbol} returns {answer} when the path does not exist."
    parsed = _extract_public_html(f"<section><h3>{symbol}</h3><p>{body}</p></section>")
    selected = _answer_excerpt(question, parsed["text"], parsed["sections"])
    assert selected and symbol in selected and answer in selected
    assert condition.casefold() in selected.casefold()


def test_navigation_dominant_source_does_not_outvote_definition():
    parsed = _fixture()
    selected = _answer_excerpt(ANNOTATED_QUESTION, parsed["text"], parsed["sections"])
    assert selected and "False" in selected and "Table of Contents" not in selected


def test_weak_evidence_remains_insufficient():
    assert _answer_excerpt(QUESTION, "The pathlib module provides object-oriented filesystem paths.") is None
