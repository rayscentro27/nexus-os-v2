"""R10 Research tier-routing: deterministic admission gates, duplicate reuse,
low-information output gate, failure circuit-breaker, tier classifier, and a
Research-specific Tier-1 free-model adapter.

HARD provider separation: this module NEVER uses Nova's Hermes profile, Nova's
session, or Nova's fallback model (nvidia/nemotron-3.5-super-vl:free). The
Research Tier-1 model is a SEPARATE OpenRouter :free model with its own config.
Codex (TIER_3) remains the deep-research engine. No paid models. No new DB/queue.
"""
from __future__ import annotations
import os, re, json, hashlib, time, urllib.parse

# ---- Nova isolation guard (asserted by tests) ----
NOVA_PROTECTED_MODEL = "nvidia/nemotron-3.5-super-vl:free"
RESEARCH_TIER1_PROVIDER = "openrouter"
# CERTIFIED 2026-11-09 (research_tier1_free_provider_certification): primary + backup.
# Both are :free, zero-cost, and emit DIRECT structured content when reasoning is
# disabled. The prior gemma/cohere chain failed (gemma persistent 429; reasoning models
# spent the whole output budget on hidden reasoning -> empty/truncated JSON). The decisive
# fix is TIER1_REQUEST_CONFIG below (reasoning disabled + json_object response_format).
RESEARCH_TIER1_MODEL = os.environ.get("RESEARCH_TIER1_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")
RESEARCH_TIER1_BACKUP_MODEL = "nvidia/nemotron-3.5-lightning:free"
assert RESEARCH_TIER1_MODEL != NOVA_PROTECTED_MODEL, "Research must not use Nova's protected fallback model"
# Research-specific free-model chain (certified primary -> backup). Nova's model excluded.
RESEARCH_TIER1_MODEL_CHAIN = [m for m in [
    RESEARCH_TIER1_MODEL,
    RESEARCH_TIER1_BACKUP_MODEL,
] if m != NOVA_PROTECTED_MODEL]
# Certified request config: disable hidden reasoning so the output budget produces the
# structured answer, and force a JSON object. max_tokens=1500 covers the observed max
# completion (1360) with headroom. These are what turned 0/17 into 17/17 parseable.
TIER1_REQUEST_CONFIG = {
    "reasoning": {"enabled": False},
    "response_format": {"type": "json_object"},
    "temperature": 0,
    "max_tokens": 1500,
}

# ---------------------------------------------------------------- PRECHECKS (Phase 2)
_EXAMPLE = re.compile(r"(^|//|\.)example\.(com|org|net)(/|$)|example domain", re.I)
_HELLO = re.compile(r"github\.com/octocat/Hello-World|^octocat/Hello-World$|hello-world", re.I)
_FIXTURE = re.compile(r"\btest[-_ ]?fixture\b|\bdummy\b|\bplaceholder\b|\blorem ipsum\b|\bfoo/bar\b", re.I)

def _norm_url(u: str) -> str:
    try:
        p = urllib.parse.urlsplit(u.strip())
        host = (p.hostname or "").lower().lstrip("www.")
        path = p.path.rstrip("/")
        q = urllib.parse.parse_qsl(p.query)
        # keep only identity-bearing query keys (e.g. youtube v=)
        keep = {k: v for k, v in q if k in ("v", "id", "list")}
        qs = urllib.parse.urlencode(sorted(keep.items()))
        return f"{host}{path}" + (f"?{qs}" if qs else "")
    except Exception:
        return u.strip().lower()

def precheck_source(source: dict | str, evidence=None) -> dict:
    """Deterministic admission. Returns {'admit':bool,'reason':<code>}.
    Rejects ONLY unambiguous non-research inputs; legitimate simple sites and
    real GitHub repos pass."""
    url = source if isinstance(source, str) else str((source or {}).get("canonical_uri") or (source or {}).get("url") or "")
    url = url.strip()
    if not url and not evidence:
        return {"admit": False, "reason": "EMPTY_EVIDENCE"}
    if url:
        if not re.match(r"^[a-z]+://", url, re.I) and "." not in url and "/" not in url:
            return {"admit": False, "reason": "MALFORMED_INPUT"}
        if _EXAMPLE.search(url):
            return {"admit": False, "reason": "INVALID_SOURCE_EXAMPLE_DOMAIN"}
        if _HELLO.search(url):
            return {"admit": False, "reason": "TEST_FIXTURE_HELLO_WORLD"}
    blob = url + " " + json.dumps(evidence or "")
    if _FIXTURE.search(blob):
        return {"admit": False, "reason": "TEST_FIXTURE"}
    # zero-information: no url AND evidence is trivially empty/whitespace
    if not url and isinstance(evidence, str) and len(evidence.strip()) < 8:
        return {"admit": False, "reason": "ZERO_INFORMATION_INPUT"}
    return {"admit": True, "reason": "ADMITTED"}

# ---------------------------------------------------------------- SOURCE IDENTITY / DEDUP (Phase 3)
def source_identity(source: dict | str) -> str:
    url = source if isinstance(source, str) else str((source or {}).get("canonical_uri") or (source or {}).get("url") or "")
    url = url.strip()
    m = re.search(r"(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{6,})", url)
    if m:
        return "yt:" + m.group(1)
    gh = re.search(r"github\.com/([^/]+/[^/]+?)(?:/|$)", url, re.I)
    if gh:
        ref = ""
        if isinstance(source, dict):
            ref = str(source.get("commit") or source.get("ref") or "")
        return "gh:" + gh.group(1).lower() + (("@" + ref) if ref else "")
    if url:
        return "url:" + _norm_url(url)
    if isinstance(source, dict) and source.get("content_hash"):
        return "hash:" + str(source["content_hash"])
    return "raw:" + hashlib.sha256(json.dumps(source, sort_keys=True, default=str).encode()).hexdigest()[:16]

def duplicate_reuse_decision(identity: str, library_lookup, *, force_refresh=False,
                             new_evidence=False, stale=False) -> dict:
    """library_lookup(identity) -> prior record or None. Reuse a materially
    identical, high-quality prior result; allow re-research on change/stale/refresh."""
    if force_refresh or new_evidence or stale:
        return {"reuse": False, "reason": "REFRESH_" + ("FORCED" if force_refresh else "NEW_EVIDENCE" if new_evidence else "STALE")}
    prior = None
    try:
        prior = library_lookup(identity)
    except Exception:
        prior = None
    if prior and prior.get("quality_ok") and prior.get("promoted"):
        return {"reuse": True, "reason": "ALREADY_ANALYZED_IDENTICAL_SOURCE", "prior_id": prior.get("id")}
    return {"reuse": False, "reason": "NO_REUSABLE_RESULT"}

# ---------------------------------------------------------------- LOW-INFORMATION OUTPUT GATE (Phase 4)
_LOWINFO = re.compile(
    r"structured research assessment completed|no attributable evidence|no evidence was supplied|"
    r"findings remain unverified|does not support a trend assessment|failed youtube metadata retrieval|"
    r"assessment completed; no evidence|research completed; no", re.I)

def promotion_gate(result: dict) -> dict:
    """Decide if a result may be promoted downstream, else a truthful terminal state."""
    text = json.dumps(result.get("structured") or result.get("result_summary") or result or {}, default=str)
    if not result.get("source_valid", True):
        return {"promote": False, "terminal_state": "INVALID_SOURCE"}
    if _LOWINFO.search(text):
        return {"promote": False, "terminal_state": "LOW_INFORMATION_OUTPUT"}
    if len(text.strip()) < 140:
        return {"promote": False, "terminal_state": "INSUFFICIENT_EVIDENCE"}
    findings = result.get("findings") or (result.get("structured") or {}).get("findings")
    if not findings and not result.get("explicit_no_finding"):
        return {"promote": False, "terminal_state": "NO_ACTIONABLE_FINDING"}
    return {"promote": True, "terminal_state": "PROMOTED"}

# ---------------------------------------------------------------- FAILURE CIRCUIT BREAKER (Phase 5/13)
def circuit_breaker(state: dict, *, max_model_calls=6, max_web_searches=12, max_duration_s=600,
                    max_continuations=4) -> dict:
    """state tracks a job's cumulative counters + last outcome. Returns stop/defer
    decision. Does NOT stop productive long runs (only when no material progress)."""
    mc = int(state.get("model_call_count", 0))
    ws = int(state.get("web_search_count", 0))
    dur = float(state.get("elapsed_duration_s", 0))
    cont = int(state.get("continuation_count", 0))
    repeated_fail = bool(state.get("repeated_failure_reason"))
    new_evidence = bool(state.get("new_evidence_added"))
    unchanged_provider = bool(state.get("provider_condition_unchanged"))
    # No material progress => stop/defer
    if repeated_fail and not new_evidence:
        return {"stop": True, "reason": "REPEATED_FAILURE_NO_NEW_EVIDENCE"}
    if cont >= max_continuations and not new_evidence:
        return {"stop": True, "reason": "CONTINUATION_NO_PROGRESS"}
    if unchanged_provider and state.get("provider_status") in ("USAGE_LIMIT_REACHED", "UNAVAILABLE"):
        return {"stop": True, "reason": "PROVIDER_BLOCKED", "defer": True}
    # Hard safety ceilings (only when also lacking progress signal)
    if (mc >= max_model_calls or ws >= max_web_searches or dur >= max_duration_s) and not new_evidence:
        return {"stop": True, "reason": "BOUNDED_CEILING_NO_PROGRESS"}
    return {"stop": False, "reason": "CONTINUE"}

# ---------------------------------------------------------------- TIER CLASSIFIER (Phase 6)
TIERS = ("TIER_0_DETERMINISTIC", "TIER_1_SIMPLE_RESEARCH", "TIER_2_STANDARD_RESEARCH", "TIER_3_DEEP_RESEARCH")

def classify_tier(job: dict) -> dict:
    """Feature-based tier classification. NOT by department label alone."""
    obj = str(job.get("objective") or "")
    rtype = str(job.get("research_type") or "").upper()
    srcs = job.get("source_refs") or []
    nsrc = len(srcs) if isinstance(srcs, list) else 0
    pre = precheck_source(srcs[0] if nsrc else "", job.get("evidence"))
    if not pre["admit"]:
        return {"tier": "TIER_0_DETERMINISTIC", "reason": "PRECHECK_REJECT:" + pre["reason"]}
    text = (obj + " " + json.dumps(srcs)).lower()
    is_single_video = nsrc == 1 and ("youtube.com/watch" in text or "youtu.be/" in text)
    conflict = bool(re.search(r"conflict|contradict|dispute|reconcile", text))
    technical = rtype in ("TECHNOLOGY", "TECHNICAL") or "github.com" in text or bool(re.search(r"repository|codebase|architecture|benchmark", text))
    commercial_deep = rtype in ("BUSINESS", "MONETIZATION", "COMMERCIAL") or bool(re.search(r"business opportunity|commercial synthesis|viability|unit economics|pricing strategy", text))
    trading = rtype == "TRADING"
    ambiguous_multi = nsrc >= 3 or bool(re.search(r"investigate|ambiguous|deep|comprehensive", text))
    # TIER_3: genuinely deep / high-impact / ambiguous / technical / conflict
    if conflict or technical or commercial_deep or trading or (ambiguous_multi and nsrc >= 3):
        return {"tier": "TIER_3_DEEP_RESEARCH", "reason": "DEEP:" + ("conflict" if conflict else "technical" if technical else "commercial" if commercial_deep else "trading" if trading else "ambiguous_multi")}
    # TIER_1: single-video trend / simple extraction
    if is_single_video and rtype == "TREND":
        return {"tier": "TIER_1_SIMPLE_RESEARCH", "reason": "SINGLE_VIDEO_TREND"}
    if rtype in ("TREND",) and nsrc <= 1:
        return {"tier": "TIER_1_SIMPLE_RESEARCH", "reason": "SIMPLE_TREND"}
    if bool(re.search(r"\b(verify|extract|summari[sz]e|pricing|feature)\b", text)) and nsrc <= 1:
        return {"tier": "TIER_1_SIMPLE_RESEARCH", "reason": "SIMPLE_EXTRACTION"}
    # TIER_2: moderate multi-source synthesis
    return {"tier": "TIER_2_STANDARD_RESEARCH", "reason": "STANDARD_SYNTHESIS"}

# ---------------------------------------------------------------- ESCALATION (Phase 12)
VALID_ESCALATIONS = {"CONFLICTING_EVIDENCE", "FAILED_QUALITY_GATE", "HIGH_AMBIGUITY",
                     "COMPLEX_TECHNICAL_ANALYSIS", "HIGH_COMMERCIAL_IMPACT", "UNRESOLVED_MATERIAL_CLAIM"}

def should_escalate(reason: str) -> bool:
    return reason in VALID_ESCALATIONS

# ---------------------------------------------------------------- TIER-1 ADAPTER (Phase 7/8) — Research-specific free model
def _openrouter_key() -> str:
    for k in ("RESEARCH_OPENROUTER_API_KEY", "OPENROUTER_API_KEY", "NEXUS_OPENROUTER_MODELS_API_KEY"):
        v = os.environ.get(k)
        if v:
            return v
    return ""

# Certified SINGLE-VIDEO TREND contract (matches the piloted/certified behavior).
# trend_signal is CURRENT_ATTENTION_* only — point-in-time counts are NOT growth velocity.
TIER1_EXTRACTION_PROMPT = (
    "You are a Research Tier-1 analyst for SINGLE-VIDEO TREND research. Using ONLY the supplied evidence, "
    "return STRICT JSON with keys: summary, key_findings (array), claims (array), "
    "claim_support (array mapping each claim to the evidence field it rests on), "
    "commercial_relevance (string or \"UNKNOWN\"), "
    "trend_signal (one of \"CURRENT_ATTENTION_HIGH\",\"CURRENT_ATTENTION_LOW\",\"UNKNOWN\"), "
    "risks_limitations (array), open_questions (array), confidence (number 0-1). "
    "HARD RULES: Do NOT invent capabilities, pricing, demand, performance, releases, or entities. "
    "Use \"UNKNOWN\"/[] when unsupported. Point-in-time view/like/comment counts are NOT growth — NEVER say "
    "\"rapidly growing\"/\"trending upward\"/\"accelerating\"; trend_signal describes current attention only.\n\nEVIDENCE:\n")

def tier1_quality_gate(structured, evidence_text="", view_count=None) -> dict:
    """Certified Phase-6 quality gate. Returns {'pass','autofail','escalation_reason'}.
    Auto-fails on structural incompleteness, unsupported high-impact claims, false trend
    growth, or over-attention on a low-view snapshot."""
    autofail = []
    val = validate_tier1_json(structured if isinstance(structured, dict) else str(structured))
    obj = val.get("obj") if isinstance(structured, str) else (structured or {})
    if not val.get("ok"):
        autofail.append("INCOMPLETE_OR_INVALID_STRUCTURE")
    if detect_false_trend_growth(obj or {}):
        autofail.append("FALSE_TREND_GROWTH")
    if over_attention_claim((obj or {}).get("trend_signal"), view_count):
        autofail.append("OVER_ATTENTION_CLAIM")
    hay = str(evidence_text).lower()
    hi = re.compile(r'(?i)\$\s?\d|\d+\s?%|guarantee|fastest|#1|million|billion|proven to|will (?:earn|make|double|triple)')
    for c in (obj or {}).get("claims") or []:
        toks = [w for w in re.findall(r"[A-Za-z0-9$%.]{4,}", str(c)) if len(w) >= 4][:8]
        grounded = (sum(1 for w in toks if w.lower() in hay) >= max(1, len(toks) // 2)) if toks else True
        if hi.search(str(c)) and not grounded:
            autofail.append("UNSUPPORTED_HIGH_IMPACT_CLAIM"); break
    passed = not autofail
    return {"pass": passed, "autofail": autofail,
            "escalation_reason": ("FAILED_QUALITY_GATE" if not passed else None)}

def tier1_to_role_outputs(structured) -> dict:
    """Map a certified Tier-1 structured result onto the R10 role-output shape so the
    existing result-assembly path (insight bank, result contract, completion event) is
    reused unchanged. Populates RESEARCH_INVESTIGATOR + TREND_SCOUT => Codex role loop
    is skipped for this job."""
    o = structured or {}
    conf = o.get("confidence")
    conf_pct = round(float(conf) * 100) if isinstance(conf, (int, float)) and conf <= 1 else (conf if isinstance(conf, (int, float)) else 70)
    findings = [{"claim": str(c), "statement": str(c)} for c in (o.get("claims") or [])]
    ts = o.get("trend_signal")
    return {
        "RESEARCH_INVESTIGATOR": {
            "findings": findings,
            "confidence": conf_pct,
            "open_questions": o.get("open_questions") or [],
            "evidence_limitations": o.get("risks_limitations") or [],
            "contradictions": [],
            "recommended_next_action": None,
            "commercial_relevance": o.get("commercial_relevance"),
            "summary": o.get("summary"),
            "key_findings": o.get("key_findings") or [],
            "_tier1_provider": True,
        },
        "TREND_SCOUT": {
            "dimensions": {"current_attention": ts},
            "trend_score": None,  # single snapshot => no velocity score (discipline)
            "confidence": {"assessment": "CURRENT_ATTENTION_ONLY", "score": conf_pct},
            "evidence": o.get("claim_support") or [],
            "missing_signals": ["Timestamped view/engagement history for velocity"],
            "trend_stage": ts or "UNKNOWN",
            "_tier1_provider": True,
        },
    }

def tier1_extract(evidence_text: str, *, model: str | None = None, timeout_s: int = 60,
                  search_count: int = 0) -> dict:
    """Call the Research-specific free model for structured single-source extraction.
    Zero web search by default (targeted; SEARCH_COUNT tracked by caller)."""
    import urllib.request
    if model == NOVA_PROTECTED_MODEL:
        return {"ok": False, "error": "NOVA_MODEL_FORBIDDEN"}
    key = _openrouter_key()
    if not key:
        return {"ok": False, "error": "RESEARCH_OPENROUTER_KEY_MISSING"}
    chain = [model] if model else list(RESEARCH_TIER1_MODEL_CHAIN)
    chain = [m for m in chain if m != NOVA_PROTECTED_MODEL]
    started = time.monotonic()
    d = None; content = ""; used = None; last_err = None
    for cand in chain:
        payload = {"model": cand,
                   "messages": [{"role": "user", "content": TIER1_EXTRACTION_PROMPT + str(evidence_text)[:120000]}]}
        payload.update(TIER1_REQUEST_CONFIG)  # reasoning disabled + json_object + headroom (certified)
        body = json.dumps(payload).encode()
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                     headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as r:
                dd = json.loads(r.read())
            cc = (dd.get("choices") or [{}])[0].get("message", {}).get("content", "")
            if cc:
                d = dd; content = cc; used = cand; break
            last_err = "EMPTY_" + cand
        except Exception as e:
            last_err = type(e).__name__ + ":" + cand
            time.sleep(0.6)
            continue
    if d is None:
        return {"ok": False, "error": last_err or "ALL_FREE_MODELS_UNAVAILABLE", "provider": "openrouter", "chain_tried": chain}
    model = used
    usage = d.get("usage", {})
    cost = usage.get("cost")
    structured = None
    mt = re.search(r"\{.*\}", content, re.S)
    if mt:
        try:
            structured = json.loads(mt.group(0))
        except Exception:
            structured = None
    return {"ok": bool(content), "provider": "openrouter", "model": d.get("model") or model,
            "structured": structured, "raw": content[:4000], "cost": cost,
            "zero_cost": (cost == 0), "duration_ms": round((time.monotonic() - started) * 1000, 1),
            "routing_tier": "TIER_1_SIMPLE_RESEARCH", "search_count": search_count,
            "search_stop_reason": "TARGETED_NO_WEB_SEARCH"}

# ---------------------------------------------------------------- PROVIDER-CERTIFICATION VALIDATORS
# Pure helpers used by the Tier-1 free-provider certification and focused tests.
_FALSE_GROWTH = re.compile(
    r"(?i)rapidly growing|trending upward|interest is accelerating|growing fast|surging|"
    r"skyrocket|exploding|gaining momentum|on the rise|accelerat|going viral|blowing up|"
    r"demand is (?:growing|increasing|rising)")
_ALLOWED_TREND_SIGNALS = {"CURRENT_ATTENTION_HIGH", "CURRENT_ATTENTION_LOW", "UNKNOWN"}
TIER1_CONTRACT_FIELDS = ("summary", "key_findings", "claims", "claim_support",
                         "commercial_relevance", "trend_signal", "risks_limitations",
                         "open_questions", "confidence")

def all_models_free() -> bool:
    """Every model in the certified chain is a zero-cost :free model (NO paid routing)."""
    return all(m.endswith(":free") for m in RESEARCH_TIER1_MODEL_CHAIN) and bool(RESEARCH_TIER1_MODEL_CHAIN)

def nova_excluded() -> bool:
    """Nova's protected model never appears in the Research Tier-1 chain."""
    return NOVA_PROTECTED_MODEL not in RESEARCH_TIER1_MODEL_CHAIN

def validate_tier1_json(text, required_fields=TIER1_CONTRACT_FIELDS) -> dict:
    """Parse + structurally validate a Tier-1 structured output. Returns
    {'ok','parsed','missing_fields','bad_trend_signal'}."""
    obj = None
    if isinstance(text, dict):
        obj = text
    else:
        try:
            obj = json.loads(str(text).strip())
        except Exception:
            m = re.search(r"\{.*\}", str(text), re.S)
            if m:
                try:
                    obj = json.loads(m.group(0))
                except Exception:
                    obj = None
    if obj is None:
        return {"ok": False, "parsed": False, "missing_fields": list(required_fields), "bad_trend_signal": None}
    missing = [f for f in required_fields if f not in obj]
    ts = obj.get("trend_signal")
    bad_ts = ts is not None and ts not in _ALLOWED_TREND_SIGNALS
    return {"ok": not missing and not bad_ts, "parsed": True, "missing_fields": missing,
            "bad_trend_signal": bad_ts, "obj": obj}

def detect_false_trend_growth(text) -> list:
    """Return growth-velocity phrases that a single point-in-time snapshot cannot support."""
    return _FALSE_GROWTH.findall(json.dumps(text) if isinstance(text, (dict, list)) else str(text))

def unknown_preserved(obj, field) -> bool:
    """True if an unsupported field is honestly 'UNKNOWN' or empty rather than fabricated."""
    v = obj.get(field) if isinstance(obj, dict) else None
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip().upper() == "UNKNOWN" or v.strip() == ""
    if isinstance(v, (list, dict)):
        return len(v) == 0
    return False

def over_attention_claim(trend_signal, view_count, threshold=10000) -> bool:
    """Flag CURRENT_ATTENTION_HIGH asserted on a low-engagement (low-view) snapshot."""
    try:
        return trend_signal == "CURRENT_ATTENTION_HIGH" and view_count is not None and int(view_count) < threshold
    except Exception:
        return False

def telemetry_fields(*, tier, routing_reason, escalation_reason=None, search_count=None,
                     search_stop_reason=None, model_call_count=None) -> dict:
    """Extra AI-usage telemetry fields layered on top of R15 attribution."""
    return {"ROUTING_TIER": tier, "ROUTING_REASON": routing_reason,
            "ESCALATION_REASON": escalation_reason, "SEARCH_COUNT": search_count,
            "SEARCH_STOP_REASON": search_stop_reason, "MODEL_CALL_COUNT": model_call_count}
