"""Fallback source acquisition over public HTTP and injectable Nexus tools."""
from __future__ import annotations

import re
import hashlib
import os
import re
import urllib.request
import uuid
from typing import Any
from urllib.parse import urlparse


class SourceTools:
    def __init__(self, methods: list[tuple[str, Any]] | None = None, timeout: float = 12,
                 search_routes: list[tuple[str, Any]] | None = None,
                 attempt_recorder: Any = None):
        self.methods = methods or [("PUBLIC_HTTP", self._http)]
        self.timeout = timeout
        self.search_routes = search_routes if search_routes is not None else self._default_search_routes()
        self.attempt_recorder = attempt_recorder

    @staticmethod
    def _default_search_routes() -> list[tuple[str, Any]]:
        """Use existing bounded, zero-cost Nexus discovery adapters only."""
        def proactive(query: str) -> dict[str, Any]:
            from nexus_agent_platform.proactive_discovery import web_search
            return web_search(query, 5)

        def hermes_free(query: str) -> dict[str, Any]:
            from hermes.hermes_web_search import web_search_free
            return web_search_free(query, 5)

        def github(query: str) -> dict[str, Any]:
            from nexus_agent_platform.proactive_discovery import github_repository_search
            if not any(term in query.casefold() for term in ("nexus", "operator", "migration", "software", "workflow")):
                return {"provider": "github_public_repository_search", "status": "NOT_APPLICABLE", "results": []}
            return {"provider": "github_public_repository_search", "status": "OK",
                    "results": github_repository_search(query, 5)}

        return [("NEXUS_PROACTIVE_DISCOVERY", proactive),
                ("HERMES_FREE_SEARCH", hermes_free),
                ("GITHUB_PUBLIC_REPOSITORY_SEARCH", github)]

    @staticmethod
    def focused_query(objective: str, question: str) -> str:
        """Remove control prose and keep a short, material query."""
        stop = {"which", "claims", "materially", "affect", "requested", "decision", "what", "important",
                "remain", "uncertain", "supports", "them", "and", "the", "for", "with", "from", "that",
                "this", "should", "could", "would", "about", "into", "existing", "research", "case",
                "continue", "leave", "open", "question", "explicitly", "citation", "verification"}
        objective_terms = [x for x in re.findall(r"[A-Za-z0-9][A-Za-z0-9._-]+", objective)
                           if len(x) > 2 and x.casefold() not in stop]
        question_terms = [x for x in re.findall(r"[A-Za-z0-9][A-Za-z0-9._-]+", question)
                          if len(x) > 2 and x.casefold() not in stop]
        selected = list(dict.fromkeys(objective_terms[:5] + question_terms[:8]))
        return " ".join(selected)[:240]

    def _record_attempt(self, attempt: dict[str, Any]) -> None:
        if self.attempt_recorder:
            self.attempt_recorder(dict(attempt))

    @staticmethod
    def _relevant_terms(question: str, text: str) -> list[str]:
        stop = {"which", "claims", "materially", "affect", "requested", "decision", "what", "important",
                "remain", "uncertain", "supports", "them", "and", "the", "for", "with", "from", "that",
                "this", "should", "could", "would", "about", "into", "existing", "research", "case",
                "continue", "leave", "open", "question", "explicitly", "citation", "verification"}
        terms = {x.casefold() for x in re.findall(r"[A-Za-z0-9][A-Za-z0-9._-]+", question)
                 if len(x) > 3 and x.casefold() not in stop}
        folded = text.casefold()
        return sorted(term for term in terms if term in folded)

    def research_questions(self, objective: str, questions: list[dict[str, Any]]) -> dict[str, Any]:
        """Bounded search→read→evidence path; every route writes an attempt receipt."""
        reports, failures, attempts = [], [], []
        for question_row in [row for row in questions if isinstance(row, dict)][:3]:
            question = " ".join(str(question_row.get("question") or "").split())
            question_id = str(question_row.get("production_question_id") or question_row.get("question_id") or "")
            if not question or not question_id:
                continue
            query = self.focused_query(objective, question)
            for provider, route in self.search_routes:
                attempt_id = "rrsrcatt_" + uuid.uuid4().hex[:20]
                attempt = {"attempt_id": attempt_id, "case_id": str(question_row.get("case_id") or ""),
                    "question_id": question_id, "query": query, "provider": provider, "result": "STARTED",
                    "error_code": None, "error_summary": None, "source_url": None, "source_id": None,
                    "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}
                attempts.append(attempt)
                self._record_attempt(attempt)
                try:
                    result = route(query)
                    candidates = result.get("results") if isinstance(result, dict) else None
                    candidates = [row for row in (candidates or []) if isinstance(row, dict)
                                  and str(row.get("url") or "").startswith(("https://", "http://"))]
                    if not candidates:
                        status = str((result or {}).get("status") or "NO_RESULTS").upper()
                        attempt.update({"result": "SEARCH_SUCCEEDED_NO_RELEVANT_RESULT" if status not in {"ERROR", "UNAVAILABLE", "NOT_CONFIGURED"} else "SEARCH_FAILED",
                            "error_code": status if status in {"ERROR", "UNAVAILABLE", "NOT_CONFIGURED"} else None,
                            "error_summary": "; ".join((result or {}).get("notes") or [])[:300] or None})
                        failures.append(dict(attempt))
                        self._record_attempt(attempt)
                        continue
                    candidate = candidates[0]
                    url = str(candidate.get("url") or "").strip()
                    attempt["source_url"] = url
                    try:
                        page = self.acquire(url, objective=question)
                    except Exception as exc:
                        page = {"status": "PAGE_READ_FAILED", "text": "", "error": exc}
                    body = str(page.get("text") or "")
                    if not body:
                        err = page.get("error")
                        code = getattr(err, "code", None) or type(err).__name__ if err else "PAGE_READ_EMPTY"
                        summary = getattr(err, "detail", None) or (str(err) if err else "Page reader returned no extracted text.")
                        attempt.update({"result": "PAGE_READ_FAILED", "error_code": str(code)[:100],
                                        "error_summary": str(summary)[:300]})
                        failures.append(dict(attempt)); self._record_attempt(attempt)
                        continue
                    evidence_terms = self._relevant_terms(question, body)
                    if len(body.strip()) < 120 or not evidence_terms:
                        attempt.update({"result": "EVIDENCE_NOT_MATERIAL", "error_code": "EVIDENCE_NOT_MATERIAL",
                                        "error_summary": "Retrieved page did not contain enough question-specific evidence."})
                        failures.append(dict(attempt)); self._record_attempt(attempt)
                        continue
                    source_id = "rrsrc_" + hashlib.sha256(url.encode()).hexdigest()[:20]
                    text_claims = [re.sub(r"\s+", " ", part).strip()[:600]
                        for part in re.split(r"(?<=[.!?])\s+", body) if len(part.strip()) >= 35
                        and any(term in part.casefold() for term in evidence_terms)][:8]
                    source = {"status": "SOURCE_ACQUIRED", "url": url,
                        "title": str(page.get("title") or candidate.get("title") or url)[:240],
                        "text": body[:16000], "summary": str(page.get("summary") or " ".join(text_claims[:3]))[:1800],
                        "source_type": page.get("source_type") or "WEB", "method": provider,
                        "source_content_hash": hashlib.sha256(body.encode("utf-8", errors="replace")).hexdigest(),
                        "source_character_count": len(body), "claims": text_claims,
                        "evidence_terms": evidence_terms, "question_id": question_id,
                        "attempt_id": attempt_id, "source_id": source_id,
                        "source_refs": [{"url": url, "question_id": question_id, "source_id": source_id}]}
                    attempt.update({"result": "SOURCE_ACQUIRED", "error_code": None, "error_summary": None,
                                    "source_id": source_id})
                    self._record_attempt(attempt)
                    reports.append(source)
                    break
                except Exception as exc:
                    code = getattr(exc, "code", None) or type(exc).__name__
                    detail = getattr(exc, "detail", None) or getattr(exc, "state", None) or str(exc)
                    attempt.update({"result": "SEARCH_FAILED", "error_code": str(code)[:100],
                                    "error_summary": str(detail)[:300]})
                    failures.append(dict(attempt)); self._record_attempt(attempt)
        status = "SOURCE_ACQUIRED" if reports else "SOURCE_INCOMPLETE"
        combined = "\n\n".join(str(row.get("text") or "") for row in reports)
        return {"status": status, "sources": reports, "source_reports": reports,
            "source_attempts": attempts, "text": combined[:16000],
            "summary": "\n".join(str(row.get("summary") or "") for row in reports)[:1800],
            "method_failures": failures,
            "limitation": None if reports else "No authorized zero-cost route returned material, readable evidence."}

    @classmethod
    def from_nexus(cls, *, web_search: Any = None, browser: Any = None,
                   research_adapter: Any = None, youtube_transcript: Any = None,
                   notebooklm: Any = None, timeout: float = 12) -> "SourceTools":
        """Compose available Nexus source capabilities into ordered fallbacks.

        The adapters are injected to keep imports side-effect free and let
        callers use the existing governed source clients. NotebookLM is only
        included for long-form sources and is always optional.
        """
        methods = []
        def add(name: str, adapter: Any) -> None:
            if adapter is None:
                return
            def call(url: str | None, *, objective: str = "") -> dict[str, Any]:
                if callable(adapter):
                    value = adapter(url=url, objective=objective)
                elif hasattr(adapter, "get_source_information"):
                    value = adapter.get_source_information(url=url, objective=objective)
                elif hasattr(adapter, "acquire"):
                    value = adapter.acquire(url=url, objective=objective)
                else:
                    raise TypeError(f"UNSUPPORTED_SOURCE_ADAPTER:{name}")
                if not isinstance(value, dict):
                    raise TypeError(f"SOURCE_ADAPTER_RESULT_MUST_BE_OBJECT:{name}")
                return value
            methods.append((name, call))

        if youtube_transcript is not None:
            # Keep the regular ordered methods first; prepend transcript and
            # optional notebook digestion only for YouTube URLs at call time.
            add("YOUTUBE_TRANSCRIPT", youtube_transcript)
        add("EXISTING_RESEARCH_ADAPTER", research_adapter)
        add("BROWSER", browser)
        add("WEB_SEARCH", web_search)
        methods.append(("PUBLIC_HTTP", lambda url, objective="": cls(timeout=timeout)._http(url, objective=objective)))
        if notebooklm is not None:
            add("NOTEBOOKLM_SOURCE_DIGESTION", notebooklm)
        if not methods:
            methods.append(("PUBLIC_HTTP", lambda url, objective="": cls(timeout=timeout)._http(url, objective=objective)))
        return cls(methods=methods, timeout=timeout)

    def acquire(self, url: str | None, *, objective: str = "") -> dict[str, Any]:
        failures = []
        is_youtube = bool(url and any(host in (urlparse(url).hostname or "").lower()
            for host in ("youtube.com", "youtu.be")))
        is_long_form = is_youtube or bool(url and any(x in url.lower() for x in (".pdf", "transcript", "video")))
        methods = list(self.methods)
        if is_youtube:
            methods.sort(key=lambda item: 0 if item[0] == "YOUTUBE_TRANSCRIPT" else 1)
        else:
            methods = [item for item in methods if item[0] != "YOUTUBE_TRANSCRIPT"]
        if not is_long_form:
            methods = [item for item in methods if item[0] != "NOTEBOOKLM_SOURCE_DIGESTION"]
        for name, method in methods:
            try:
                result = method(url, objective=objective)
                if result and result.get("text"):
                    source_text = str(result.get("text") or "")
                    return {"status": "SOURCE_ACQUIRED", "method": name, **result,
                            "source_content_hash": hashlib.sha256(source_text.encode("utf-8", errors="replace")).hexdigest(),
                            "source_character_count": len(source_text),
                            "summary": str(result.get("summary") or source_text[:1800]),
                            "method_failures": failures}
                failures.append({"method": name, "status": "EMPTY_RESULT"})
            except Exception as exc:
                failures.append({"method": name, "status": "UNAVAILABLE",
                                 "error": f"{type(exc).__name__}: {exc}"})
        return {"status": "SOURCE_INCOMPLETE", "url": url, "text": "",
                "method_failures": failures,
                "limitation": "No configured source method returned content."}

    def _http(self, url: str | None, *, objective: str = "") -> dict[str, Any]:
        if not url:
            return {"url": None, "title": objective[:160], "text": objective, "source_type": "SUBJECT"}
        def fetch():
            request = urllib.request.Request(url, headers={"User-Agent": "NexusResearchRoom/1.0", "Accept": "text/html,text/plain"})
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read(1_000_000).decode("utf-8", errors="replace")
                title_match = re.search(r"<title[^>]*>(.*?)</title>", raw, re.I | re.S)
                title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else url
                text = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", raw, flags=re.I | re.S)
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()
                return {"url": url, "title": title, "text": text[:16000],
                        "source_type": "WEB", "http_status": getattr(response, "status", 200)}
        from nexus_agent_platform.provider_enforcement import execute
        host = urlparse(url).hostname or "unknown"
        result = execute("PUBLIC_WEB", host, "RESEARCH_READ",
            {"requests": 1, "operations": 1, "bytes": 1_000_000, "runtime_seconds": self.timeout,
             "cost": 0, "billable": False}, fetch,
            job_id=os.environ.get("NEXUS_DURABLE_JOB_ID"),
            job_type=os.environ.get("NEXUS_JOB_TYPE", "RESEARCH_CASE_CONTINUATION"),
            project_id=os.environ.get("NEXUS_PROJECT_ID"),
            correlation_id=os.environ.get("NEXUS_CORRELATION_ID"),
            purpose=f"research-room-source:{os.environ.get('NEXUS_RESEARCH_ROOM_CALL_ID', 'unscoped')}:{hashlib.sha256(url.encode()).hexdigest()[:16]}",
            actual_usage=lambda value: {"requests": 1, "operations": 1,
                "bytes": len(str(value.get("text") or "").encode()), "runtime_seconds": self.timeout, "cost": 0})
        return result
