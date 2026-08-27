"""Bounded Oracle Ollama/Gemma advisory provider; deterministic code remains authoritative."""
from __future__ import annotations
import json, time, urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/nexus_oracle_ollama.json"
CANONICAL = {"MARKET_DATA_UNAVAILABLE","MARKET_DATA_STALE","MARKET_DATA_INSUFFICIENT","NO_VALID_SETUP","SIGNAL_CANDIDATE","SIGNAL_REJECTED","PRACTICE_EXECUTION_ELIGIBLE","PRACTICE_ORDER_FILLED","PRACTICE_ORDER_REJECTED","TRADE_MONITORING","TRADE_CLOSED"}
DENIED = ("place a trade", "enable live trading", "place an order", "provision oracle", "change billing", "modify secrets", "execute arbitrary code")

def config() -> dict[str, Any]: return json.loads(CONFIG.read_text())

def validate_review(value: dict[str, Any], *, expected_status: str | None = None) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("status") not in CANONICAL or value.get("risk") not in {"LOW","MEDIUM","HIGH"} or not isinstance(value.get("recommendation"), str) or not isinstance(value.get("evidence_refs"), list):
        return {"valid": False, "reason": "malformed_or_out_of_vocabulary", "provider": "oracle_ollama_gemma"}
    if expected_status and value["status"] != expected_status: return {"valid": False, "reason": "deterministic_status_mismatch", "provider": "oracle_ollama_gemma"}
    if any(term in value["recommendation"].lower() for term in DENIED): return {"valid": False, "reason": "authority_policy_rejected", "provider": "oracle_ollama_gemma"}
    return {"valid": True, "provider": "oracle_ollama_gemma", "model": config()["model"], "review": value}

def health(base_url: str | None = None) -> dict[str, Any]:
    base = base_url or "http://127.0.0.1:11435"; started=time.monotonic()
    try:
        with urllib.request.urlopen(base.rstrip("/")+"/api/version", timeout=3) as response: version=json.loads(response.read().decode() or "{}")
        with urllib.request.urlopen(base.rstrip("/")+"/api/tags", timeout=5) as response: tags=json.loads(response.read().decode() or "{}")
        models=[x.get("name") for x in tags.get("models",[]) if x.get("name")]; model=config()["model"]
        return {"status":"ORACLE_AI_READY" if model in models else "ORACLE_MODEL_UNAVAILABLE", "provider":"oracle_ollama_gemma", "model":model, "ollama_version":version.get("version"), "models":models, "latency_ms":round((time.monotonic()-started)*1000,2), "endpoint":base, "public_exposure":False, "cost_bearing":False}
    except TimeoutError: return {"status":"ORACLE_AI_TIMEOUT","provider":"oracle_ollama_gemma","latency_ms":round((time.monotonic()-started)*1000,2)}
    except Exception as exc: return {"status":"ORACLE_TUNNEL_UNAVAILABLE","provider":"oracle_ollama_gemma","error":exc.__class__.__name__,"latency_ms":round((time.monotonic()-started)*1000,2)}

def review(evidence: dict[str, Any], *, expected_status: str, timeout: int | None = None) -> dict[str, Any]:
    cfg=config(); started=time.monotonic(); prompt=("Return ONLY one JSON object, no markdown. Required exact types: status must be the literal " + expected_status + ", risk must be the literal LOW, recommendation must be a non-empty string, evidence_refs must be a JSON array of strings. Example: {\"status\":\"" + expected_status + "\",\"risk\":\"LOW\",\"recommendation\":\"Continue scanning.\",\"evidence_refs\":[]}. Never use null. Never claim orders, fills, P&L, or authority. Evidence: " + json.dumps(evidence, separators=(",",":"))[:12000])
    payload=json.dumps({"model":cfg["model"],"prompt":prompt,"stream":False,"format":"json","options":{"temperature":0,"num_predict":180}}).encode()
    try:
        req=urllib.request.Request("http://127.0.0.1:11435/api/generate",data=payload,headers={"Content-Type":"application/json"},method="POST")
        with urllib.request.urlopen(req,timeout=timeout or cfg["timeout_seconds"]) as response: raw=json.loads(response.read().decode() or "{}")
        text=raw.get("response",""); parsed=json.loads(text); checked=validate_review(parsed,expected_status=expected_status)
        return {"status":"ORACLE_AI_READY" if checked.get("valid") else "ORACLE_AI_INVALID_OUTPUT", "provider":"oracle_ollama_gemma", "model":cfg["model"], "latency_ms":round((time.monotonic()-started)*1000,2), "validation":checked, "raw_text":text[:4000], "cost_bearing":False}
    except TimeoutError: return {"status":"ORACLE_AI_TIMEOUT","provider":"oracle_ollama_gemma","latency_ms":round((time.monotonic()-started)*1000,2),"fallback_required":True}
    except Exception as exc: return {"status":"ORACLE_OLLAMA_UNAVAILABLE","provider":"oracle_ollama_gemma","error":exc.__class__.__name__,"latency_ms":round((time.monotonic()-started)*1000,2),"fallback_required":True}
