"""Deterministic model selection for the Nexus REA Kaggle worker: manual | auto | fallback. Pure functions."""
from __future__ import annotations

LOADABLE = {"CERTIFIED", "APPROVED", "APPROVED_FALLBACK"}
PROFILES = ("general_rea", "code_analysis", "deep_reasoning", "long_context", "fast_tool_loop", "coding", "security_analysis")
JSON_RANK = {"high": 3, "medium": 2, "low": 1}

AUTO_RULES_TEXT = {
    "general_rea": "highest reasoning+code; CERTIFIED preferred; then speed",
    "fast_tool_loop": "highest speed; then JSON reliability",
    "code_analysis": "highest code strength",
    "coding": "highest code strength",
    "deep_reasoning": "highest reasoning strength that fits",
    "security_analysis": "highest reasoning+code (authorized defensive analysis)",
    "long_context": "largest trained context that fits the requested context",
}


def _rank(profile: str, m: dict) -> tuple:
    certified = m["STATUS"] == "CERTIFIED"
    if profile == "fast_tool_loop":
        return (m["EXPECTED_SPEED"], JSON_RANK[m["JSON_RELIABILITY"]], certified)
    if profile in ("code_analysis", "coding"):
        return (m["CODE_STRENGTH"], certified, m["EXPECTED_SPEED"])
    if profile == "deep_reasoning":
        return (m["REASONING_STRENGTH"], certified, m["EXPECTED_SPEED"])
    if profile == "long_context":
        return (m["CONTEXT_LIMIT"], certified, m["EXPECTED_SPEED"])
    return (certified, m["REASONING_STRENGTH"] + m["CODE_STRENGTH"], m["EXPECTED_SPEED"])


def fit(model: dict, gpus_free_mb: list[int], requested_context: int | None, cal: dict) -> dict:
    """Memory/context fit check calibrated on the measured Qwen3-30B-A3B run (est 25498 vs 25550 MiB @32K)."""
    ctx = int(requested_context or model["operating_context"])
    weights = model["file_gb"] * 1024 * cal["weights_overhead_factor"]
    kv = model["kv_bytes_per_token"] * ctx / 1048576
    compute = max(cal["min_compute_mb"], cal["compute_bytes_per_token"] * ctx / 1048576)
    need = weights + kv + compute + cal["per_extra_gpu_overhead_mb"] * max(0, len(gpus_free_mb) - 1)
    free = sum(gpus_free_mb)
    reasons = []
    if not gpus_free_mb:
        reasons.append("NO_GPU")
    if ctx > model["CONTEXT_LIMIT"]:
        reasons.append(f"CONTEXT_EXCEEDS_TRAINED:{ctx}>{model['CONTEXT_LIMIT']}")
    if need > free * cal["headroom_factor"]:
        reasons.append(f"GPU_MEMORY:{round(need)}MiB>{round(free * cal['headroom_factor'])}MiB")
    if model["STATUS"] not in LOADABLE:
        reasons.append("STATUS_NOT_LOADABLE:" + model["STATUS"])
    return {"model": model["key"], "context": ctx, "estimated_mb": round(need), "estimated_kv_mb": round(kv),
            "free_mb": free, "headroom_mb": round(free - need), "fits": not reasons, "reasons": reasons}


def _eligible(m: dict, job: dict) -> bool:
    if job.get("tool_count", 1) and JSON_RANK[m["JSON_RELIABILITY"]] < 2:
        return False                          # tool loops need acceptable structured-output reliability
    return True


def select(catalog: dict, *, mode: str, gpus_free_mb: list[int], model_key: str | None = None,
           fallback_key: str | None = None, profile: str = "general_rea", job: dict | None = None) -> dict:
    """Return {status, selected, fallback, context, fit, considered}. Never raises for a bad choice."""
    job = dict(job or {})
    models = {m["key"]: m for m in catalog["models"]}
    cal = catalog["calibration"]
    req_ctx = job.get("required_context")
    fallback_key = fallback_key or catalog["default_fallback"]
    considered = []

    def check(key):
        m = models.get(key)
        if not m:
            considered.append({"model": key, "fits": False, "reasons": ["NOT_IN_CATALOG"]})
            return None
        f = fit(m, gpus_free_mb, req_ctx, cal)
        if not _eligible(m, job):
            f["fits"] = False
            f["reasons"].append("JSON_RELIABILITY_INSUFFICIENT")
        considered.append(f)
        return f if f["fits"] else None

    if mode == "manual":
        primary = model_key or catalog["default_model"]
        ok = check(primary)
        if ok:
            return {"status": "SELECTED", "selected": primary, "fallback": fallback_key, "context": ok["context"],
                    "fit": ok, "considered": considered}
        fb = check(fallback_key) if fallback_key != primary else None
        if fb:
            return {"status": "REJECTED_DOES_NOT_FIT_USING_FALLBACK", "selected": fallback_key, "fallback": None,
                    "context": fb["context"], "fit": fb, "considered": considered}
        return {"status": "NO_MODEL_FITS", "selected": None, "fallback": None, "context": None, "fit": None, "considered": considered}
    if mode != "auto":
        return {"status": "INVALID_MODE", "selected": None, "fallback": None, "context": None, "fit": None, "considered": []}
    if profile not in PROFILES:
        profile = "general_rea"
    candidates = [m for m in catalog["models"] if profile in m["TASK_PROFILES"]] or list(catalog["models"])
    candidates.sort(key=lambda m: _rank(profile, m), reverse=True)
    for m in candidates:
        ok = check(m["key"])
        if ok:
            fb = fallback_key if fallback_key != m["key"] else catalog["default_model"]
            return {"status": "SELECTED", "selected": m["key"], "fallback": fb, "context": ok["context"], "fit": ok,
                    "profile": profile, "rule": AUTO_RULES_TEXT[profile], "considered": considered}
    return {"status": "NO_MODEL_FITS", "selected": None, "fallback": None, "context": None, "fit": None,
            "profile": profile, "considered": considered}
