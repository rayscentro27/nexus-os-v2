import json
from pathlib import Path

import model_selector as ms

CAT = json.loads((Path(__file__).resolve().parents[1] / "model_catalog.json").read_text())
T4X2 = [14906, 14918]          # measured free MiB on Kaggle 2xT4


def test_catalog_shape():
    keys = [m["key"] for m in CAT["models"]]
    assert len(keys) == len(set(keys)) == 8
    assert {m["MODEL_FAMILY"] for m in CAT["models"]} >= {"qwen", "llama", "deepseek", "mistral"}
    assert CAT["default_model"] == "qwen3-30b-a3b" and CAT["default_fallback"] == "qwen3-14b"
    for m in CAT["models"]:
        assert len(m["sha256"]) == 64 and m["operating_context"] <= m["CONTEXT_LIMIT"]


def test_calibration_matches_measurement():
    m = next(x for x in CAT["models"] if x["key"] == "qwen3-30b-a3b")
    f32 = ms.fit(m, T4X2, 32768, CAT["calibration"])
    assert f32["fits"] and abs(f32["estimated_mb"] - 25550) < 300
    f64 = ms.fit(m, T4X2, 65536, CAT["calibration"])
    assert not f64["fits"] and any("CONTEXT_EXCEEDS_TRAINED" in r for r in f64["reasons"])


def test_manual_selection_validates_and_falls_back():
    r = ms.select(CAT, mode="manual", gpus_free_mb=T4X2, model_key="qwen3-30b-a3b")
    assert r["status"] == "SELECTED" and r["selected"] == "qwen3-30b-a3b" and r["context"] == 32768
    big = ms.select(CAT, mode="manual", gpus_free_mb=T4X2, model_key="llama-3.3-70b-instruct")
    assert big["status"] == "REJECTED_DOES_NOT_FIT_USING_FALLBACK" and big["selected"] == "qwen3-14b"
    unknown = ms.select(CAT, mode="manual", gpus_free_mb=T4X2, model_key="not-a-model")
    assert unknown["selected"] == "qwen3-14b" and unknown["considered"][0]["reasons"] == ["NOT_IN_CATALOG"]
    none = ms.select(CAT, mode="manual", gpus_free_mb=[], model_key="qwen3-30b-a3b")
    assert none["status"] == "NO_MODEL_FITS" and none["selected"] is None
    assert ms.select(CAT, mode="bogus", gpus_free_mb=T4X2)["status"] == "INVALID_MODE"


def test_auto_rules_are_deterministic_and_respect_fit():
    pick = lambda p, **job: ms.select(CAT, mode="auto", gpus_free_mb=T4X2, profile=p, job=job)["selected"]
    assert pick("general_rea") == "qwen3-30b-a3b"
    assert pick("code_analysis") == "devstral-small-2507"
    assert pick("deep_reasoning") == "qwen3-30b-a3b"            # 70B (5) does not fit 2xT4
    assert pick("fast_tool_loop") == "qwen3-30b-a3b"
    assert pick("security_analysis") == "qwen3-30b-a3b"
    lc = ms.select(CAT, mode="auto", gpus_free_mb=T4X2, profile="long_context", job={"required_context": 65536})
    assert lc["selected"] in {"llama-3.1-8b-instruct", "mistral-small-3.2-24b-instruct"} and lc["fit"]["context"] == 65536
    one_t4 = ms.select(CAT, mode="auto", gpus_free_mb=[14906], profile="general_rea")
    assert one_t4["selected"] != "qwen3-30b-a3b" and one_t4["fit"]["fits"]
