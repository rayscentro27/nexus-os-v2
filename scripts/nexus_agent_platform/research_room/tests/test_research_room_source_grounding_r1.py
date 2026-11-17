"""Test suite for NEXUS_RESEARCH_ROOM_SOURCE_GROUNDING_R1.

Verifies:
1. EXACT_URL_PRESERVED: Exact URL and query parameters are preserved.
2. URL_RETRIEVAL: Ingestion retrieves source content and stores artifact.
3. RESOLVED_URL_RECORDED: Captures resolved_url from HTTP response.
4. SOURCE_PROVENANCE: Full provenance dictionary populated.
5. SOURCE_CONTENT_HASH: SHA-256 hash calculated and stored.
6. ALPHA_BLOCKS_ON_MISSING_SOURCE: Alpha blocks when no source is attached.
7. ALPHA_NO_GUESSING: Alpha returns UNKNOWN when evidence is absent.
8. SAME_NAME_WRONG_SOURCE_PREVENTED: Domain disambiguation prevents attributing digital signage to getadmira.com.
9. ADMIRA_EXACT_SOURCE_TEST: Live/mock exact source test for Admira AI marketing attribution & creative.
10. UNREACHABLE_URL_NEGATIVE_TEST: Unreachable URL sets UNAVAILABLE and Alpha blocks with UNKNOWN.
11. NO_LEGACY_RESEARCH_JOB: No legacy durable research job created.
12. NO_DEEP_RESEARCH_TRIGGERED: Evaluated without deep research loops.
13. NO_PROMOTION: Room remains unpromoted unless explicitly commanded.
14. NO_DOWNSTREAM_DIRECTIVES: Zero marketing/creative/commerce directives created.
15. NO_SPEND: Spend is strictly 0.
16. NO_PUBLISH: External publish is strictly NO.
"""
from __future__ import annotations

import re
import urllib.error
import pytest
from pathlib import Path

from nexus_agent_platform.research_room.room_manager import (
    ResearchRoomStore,
    ResearchRoomManager,
    RoomSource,
    converse_with_alpha,
    calculate_preliminary_score,
    AUTONOMOUS_RESEARCH_OFF,
)
from nova.research_room_dispatch import (
    execute_research_room_request,
    render_nova_research_response,
)


ADMIRA_URL = "https://www.getadmira.com/?r=0"
MOCK_ADMIRA_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Admira – Marketing Attribution for LATAM Lead-Gen Teams</title>
    <link rel="canonical" href="https://www.getadmira.com/" />
</head>
<body>
    <header><h1>Admira</h1></header>
    <main>
        <p>Create Ads, Prove Impact, Scale Winners With Admira's AI-powered platform, you can create on-brand ads, track every touch to revenue with multi-touch attribution, and maximize ROAS without the guesswork or wasted budget.</p>
        <p>Unify data across the funnel to uncover what is working, fix what is not, forecast with confidence, and build new ads with AI.</p>
        <p>Attribution Deep Insights with AI: Uncover which channels, campaigns, and ads deliver real revenue.</p>
        <p>Multi-touch Attribution and AI Admaker: Replace the need to juggle between multiple platforms to track your ad spend. Admira is a single powerful tool that brings clarity to your marketing spend.</p>
        <p>Accelerate Boosted Marketing Outcomes: Empower your strategies with data-driven decisions to enhance productivity, forecast with confidence, and create winning ads end-to-end.</p>
    </main>
</body>
</html>"""


@pytest.fixture
def temp_store(tmp_path):
    return ResearchRoomStore(root=tmp_path / "research_rooms")


@pytest.fixture
def room_manager(temp_store):
    return ResearchRoomManager(store=temp_store)


def test_safety_doctrine_and_zero_side_effects():
    """Verify routing safety doctrine constraints."""
    assert AUTONOMOUS_RESEARCH_OFF is True


def test_exact_url_preserved_and_retrieval(room_manager, monkeypatch):
    """Test 1 & 2 & 3 & 4 & 5: Exact URL preserved, retrieved, provenance, hash recorded."""
    # Mock urllib response for deterministic testing
    class MockResponse:
        def __init__(self, body_bytes: bytes, url: str):
            self.body_bytes = body_bytes
            self.url = url
            self.status = 200

        def read(self, limit=-1):
            return self.body_bytes[:limit] if limit > 0 else self.body_bytes

        def geturl(self):
            return self.url

        def info(self):
            class Info:
                def get_content_type(self):
                    return "text/html"
                def get_content_charset(self):
                    return "utf-8"
                def get(self, k, default=None):
                    return "text/html; charset=utf-8"
            return Info()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=10: MockResponse(MOCK_ADMIRA_HTML.encode("utf-8"), "https://www.getadmira.com/?r=0")
    )

    room = room_manager.create_room("Admira Ingestion Test")
    rid = room["room_id"]

    updated = room_manager.add_source(rid, source_type="URL", content_or_url=ADMIRA_URL)
    sources = updated.get("sources", [])
    assert len(sources) == 1
    src = sources[0]

    # 1. EXACT_URL_PRESERVED
    assert src["requested_url"] == ADMIRA_URL
    assert "?r=0" in src["requested_url"]

    # 2. URL_RETRIEVAL
    assert src["retrieval_status"] in ("RETRIEVED", "REDIRECTED_AND_RETRIEVED")
    assert src["status"] == "AVAILABLE"
    assert "Marketing Attribution" in (src.get("page_title") or "")

    # 3. RESOLVED_URL_RECORDED
    assert src["resolved_url"] == ADMIRA_URL
    assert src["canonical_url"] == "https://www.getadmira.com/"
    assert src["domain"] == "www.getadmira.com"

    # 4. SOURCE_PROVENANCE
    prov = src["source_provenance"]
    assert isinstance(prov, dict)
    assert prov["requested_url"] == ADMIRA_URL
    assert prov["resolved_url"] == ADMIRA_URL
    assert prov["domain"] == "www.getadmira.com"
    assert prov["retrieval_status"] in ("RETRIEVED", "REDIRECTED_AND_RETRIEVED")
    assert prov["extracted_text_pointer"] is not None

    # 5. SOURCE_CONTENT_HASH
    assert src["content_hash"] is not None
    assert len(src["content_hash"]) == 64  # SHA-256


def test_alpha_blocks_on_missing_source(room_manager):
    """Test 6: Alpha blocks when no sources are attached to the room."""
    room = room_manager.create_room("Empty Room")
    ans = converse_with_alpha(room, "How could this help Nexus Marketing and Creative?")

    assert ans["metadata"]["grounded"] is False
    assert ans["metadata"]["missing_sources"] is True
    assert "does not have any sources attached yet" in ans["reply"]


def test_alpha_blocks_on_unreachable_url(room_manager, monkeypatch):
    """Test 7 & 10: Negative test with unreachable URL. Alpha blocks and does not guess."""
    def mock_fail(req, timeout=10):
        raise urllib.error.URLError("Name or service not known (simulated DNS failure)")

    monkeypatch.setattr("urllib.request.urlopen", mock_fail)

    room = room_manager.create_room("Unreachable Room")
    rid = room["room_id"]

    updated = room_manager.add_source(rid, source_type="URL", content_or_url="https://nonexistent-domain-404-fail.org/info")
    src = updated["sources"][0]

    assert src["retrieval_status"] == "UNAVAILABLE"
    assert src["status"] == "UNAVAILABLE"
    assert src["retrieval_error"] is not None

    # Converse with Alpha on this room
    ans = converse_with_alpha(updated, "What does this product do?")
    assert ans["metadata"]["grounded"] is False
    assert ans["metadata"]["retrieval_blocked"] is True
    assert "could not retrieve the supplied source URL" in ans["reply"]
    assert "UNKNOWN" in ans["reply"]

    # Check score behavior when URL failed
    score_res = calculate_preliminary_score(updated)
    assert score_res["preliminary_score"] == 0
    assert score_res["score_basis"]["confidence"] == "LOW"


def test_same_name_wrong_source_prevented(room_manager, monkeypatch):
    """Test 8: Disambiguation between getadmira.com (AI attribution) and admira.com (digital signage)."""
    class MockResponse:
        def __init__(self):
            self.status = 200
        def read(self, limit=-1):
            return MOCK_ADMIRA_HTML.encode("utf-8")
        def geturl(self):
            return "https://www.getadmira.com/?r=0"
        def info(self):
            class Info:
                def get_content_type(self):
                    return "text/html"
                def get_content_charset(self):
                    return "utf-8"
                def get(self, k, default=None):
                    return "text/html"
            return Info()
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=10: MockResponse())

    room = room_manager.create_room("Admira Disambiguation")
    rid = room["room_id"]
    updated = room_manager.add_source(rid, source_type="URL", content_or_url=ADMIRA_URL)

    # Ray asks about digital signage / screens
    ans = converse_with_alpha(updated, "Does Admira manage digital signage and screens?")
    reply = ans["reply"]

    # Assert digital signage is explicitly rejected / disambiguated
    assert "digital signage" in reply.lower()
    assert "different entity with the same name" in reply or "admira.com" in reply
    assert "UNKNOWN" in reply or "unsupported" in reply.lower()
    assert ans["metadata"]["grounded"] is True


def test_admira_exact_source_grounding_and_capabilities(room_manager, monkeypatch):
    """Test 9: Admira exact source ground answers Marketing and Creative specifically."""
    class MockResponse:
        def __init__(self):
            self.status = 200
        def read(self, limit=-1):
            return MOCK_ADMIRA_HTML.encode("utf-8")
        def geturl(self):
            return "https://www.getadmira.com/?r=0"
        def info(self):
            class Info:
                def get_content_type(self):
                    return "text/html"
                def get_content_charset(self):
                    return "utf-8"
                def get(self, k, default=None):
                    return "text/html"
            return Info()
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=10: MockResponse())

    room = room_manager.create_room("Admira Marketing and Creative")
    rid = room["room_id"]
    updated = room_manager.add_source(rid, source_type="URL", content_or_url=ADMIRA_URL)

    ans = converse_with_alpha(updated, "How could Admira help Nexus Marketing and Creative?")
    reply = ans["reply"]

    # Marketing verification
    assert "marketing" in reply.lower()
    assert any(term in reply.lower() for term in ("attribution", "multi-touch", "roas", "ad spend"))

    # Creative verification
    assert "creative" in reply.lower()
    assert any(term in reply.lower() for term in ("admaker", "on-brand ads", "winning creative"))

    # Exclusion of wrong entity
    assert "digital signage" not in reply.lower() or "not part of this platform" in reply.lower()
    assert ans["metadata"]["grounded"] is True
    assert ans["metadata"]["alpha_used_exact_source"] is True


def test_nova_dispatch_end_to_end_source_grounding(tmp_path, monkeypatch):
    """Test 11-16: End-to-end dispatch through Nova research room execution."""
    class MockResponse:
        def __init__(self):
            self.status = 200
        def read(self, limit=-1):
            return MOCK_ADMIRA_HTML.encode("utf-8")
        def geturl(self):
            return "https://www.getadmira.com/?r=0"
        def info(self):
            class Info:
                def get_content_type(self):
                    return "text/html"
                def get_content_charset(self):
                    return "utf-8"
                def get(self, k, default=None):
                    return "text/html"
            return Info()
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=10: MockResponse())

    prompt = (
        "Nova, create a Research Room for Admira and have Alpha research how it could help Nexus Marketing and Creative. "
        "Score it, but do not promote or create downstream work yet."
    )
    result = execute_research_room_request(
        prompt,
        objective_id="grounding-test-001",
        repository_root=tmp_path,
    )

    # 1. Output assertions
    assert result["status"] == "COMPLETE"
    assert result["requested_url"] == ADMIRA_URL
    assert result["resolved_url"] == ADMIRA_URL
    assert result["domain"] == "www.getadmira.com"
    assert result["source_retrieved"] is True
    assert result["source_provenance_verified"] is True
    assert result["alpha_used_exact_source"] is True
    assert result["preliminary_score"] > 0

    rendered = render_nova_research_response(result)

    # Required contract lines
    assert "RESEARCH_ROOM_CREATED=YES" in rendered
    assert "ROOM_ID=room_" in rendered
    assert f"REQUESTED_URL={ADMIRA_URL}" in rendered
    assert "DOMAIN=www.getadmira.com" in rendered
    assert "SOURCE_RETRIEVED=YES" in rendered
    assert "SOURCE_PROVENANCE_VERIFIED=YES" in rendered
    assert "ALPHA_USED_EXACT_SOURCE=YES" in rendered
    assert "ALPHA_INVOKED=YES" in rendered
    assert "ALPHA_RESULT_RETURNED=YES" in rendered
    assert "PRELIMINARY_SCORE_RETURNED=YES" in rendered

    # Safety assertions (11-16)
    assert "LEGACY_RESEARCH_JOB_CREATED=NO" in rendered
    assert "PROMOTED=NO" in rendered
    assert "PROJECT_CREATED=NO" in rendered
    assert "MARKETING_DIRECTIVE_CREATED=NO" in rendered
    assert "CREATIVE_DIRECTIVE_CREATED=NO" in rendered
    assert "COMMERCE_DIRECTIVE_CREATED=NO" in rendered
    assert "SPEND=0" in rendered
    assert "PUBLISH=NO" in rendered

    # Ensure no digital signage in alpha result
    assert "digital signage" not in result["alpha_result"].lower() or "excluded" in result["alpha_result"].lower()
