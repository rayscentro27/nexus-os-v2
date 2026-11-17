"""Bounded, read-only query adapter for the public OpenAffiliate registry."""
from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://openaffiliate.dev/api"
MAX_RESULTS = 10
MAX_RESPONSE_BYTES = 512_000


class OpenAffiliateError(RuntimeError):
    pass


def _get(path: str, params: dict[str, Any] | None = None, *, timeout: float = 8.0) -> dict[str, Any]:
    query = urlencode({key: value for key, value in (params or {}).items() if value not in (None, "")})
    url = f"{BASE_URL}{path}" + (f"?{query}" if query else "")
    request = Request(url, headers={"Accept": "application/json", "API-Version": "1",
                                    "User-Agent": "Nexus-Opportunities/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise OpenAffiliateError(f"OpenAffiliate returned HTTP {response.status}")
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except OpenAffiliateError:
        raise
    except Exception as exc:
        raise OpenAffiliateError(f"OpenAffiliate request failed ({type(exc).__name__})") from exc
    if len(body) > MAX_RESPONSE_BYTES:
        raise OpenAffiliateError("OpenAffiliate response exceeded the bounded response size")
    try:
        value = json.loads(body)
    except (TypeError, json.JSONDecodeError) as exc:
        raise OpenAffiliateError("OpenAffiliate returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise OpenAffiliateError("OpenAffiliate response was not an object")
    return value


def _normalize(program: dict[str, Any]) -> dict[str, Any]:
    slug = str(program.get("slug") or "").strip()
    name = str(program.get("name") or "").strip()
    if not slug or not name:
        raise OpenAffiliateError("OpenAffiliate program lacks a stable name or slug")
    commission = program.get("commission") if isinstance(program.get("commission"), dict) else {}
    payout = program.get("payout") if isinstance(program.get("payout"), dict) else {}
    restrictions = program.get("restrictions") or program.get("programRestrictions") or []
    if isinstance(restrictions, str):
        restrictions = [restrictions]
    if not isinstance(restrictions, list):
        restrictions = []
    approval = program.get("approval")
    approval_requirements = approval if approval is not None else program.get("approvalTime")
    program_url = str(program.get("programUrl") or program.get("url") or
                      f"https://openaffiliate.dev/programs/{slug}")
    verified = program.get("verified") is True
    return {
        "title": name,
        "candidate_name": name,
        "opportunity_type": "AFFILIATE",
        "subcategory": str(program.get("category") or "BUSINESS_SERVICES"),
        "summary": str(program.get("description") or program.get("tagline") or
                        f"Affiliate program listed in OpenAffiliate under {program.get('category') or 'an unclassified category'}.")[:2000],
        "revenue_model": "Affiliate referral commission",
        "revenue_details": {"commission": commission, "payout": payout},
        "source_type": "OPENAFFILIATE",
        "source_name": "OpenAffiliate",
        "source_reference": program_url,
        "source_external_id": slug,
        "source_summary": str(program.get("answer") or program.get("description") or "")[:2000],
        "verification_state": "VERIFIED" if verified else "PARTIAL",
        "metadata": {
            "slug": slug,
            "category": program.get("category"),
            "commission": commission,
            "cookie_duration_days": program.get("cookieDays"),
            "restrictions": [str(item)[:500] for item in restrictions[:20]],
            "approval_requirements": approval_requirements,
            "program_url": program_url,
            "verification_state": "VERIFIED" if verified else "PARTIAL",
            "payout": payout,
        },
    }


def search(*, keyword: str = "", category: str = "", limit: int = 5) -> dict[str, Any]:
    bounded_limit = max(1, min(int(limit), MAX_RESULTS))
    query = str(keyword or "").strip()[:120]
    selected_category = str(category or "").strip()[:80]
    if not query and not selected_category:
        raise ValueError("keyword_or_category_required")
    payload = _get("/programs", {"q": query, "category": selected_category,
                                  "limit": bounded_limit, "include_description": "true"})
    rows = payload.get("programs")
    if not isinstance(rows, list):
        raise OpenAffiliateError("OpenAffiliate response did not contain a program list")
    programs = [_normalize(row) for row in rows[:bounded_limit] if isinstance(row, dict)]
    return {"status": "OK", "source": "OpenAffiliate", "count": len(programs),
            "total": payload.get("total"), "programs": programs}


def get_program(slug: str) -> dict[str, Any]:
    clean_slug = str(slug or "").strip()
    if not clean_slug or len(clean_slug) > 120 or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in clean_slug):
        raise ValueError("valid_program_slug_required")
    payload = _get(f"/programs/{clean_slug}")
    return _normalize(payload)


def health() -> dict[str, Any]:
    payload = _get("/categories", timeout=4.0)
    categories = payload.get("categories")
    if not isinstance(categories, (dict, list)):
        raise OpenAffiliateError("OpenAffiliate categories response was incomplete")
    return {"status": "PASS", "endpoint": BASE_URL, "category_count": len(categories)}

