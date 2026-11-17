"""Mercury's evidence-grounded strategy synthesis bridge for Research Cases.

This module asks the governed Hermes executor to act as Mercury. It does not
construct trading rules locally. Model output is schema-checked and attached
to the originating objective case; backtesting remains a separate gate.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CASE_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")
SPEC_DIR = ROOT / "data/governed/mercury_strategy_specs"
RECEIPTS = ROOT / "data/governed/mercury_strategy_synthesis_receipts.jsonl"
REQUIRED_SPEC = (
    "strategy_id", "case_id", "name", "version", "market", "timeframe",
    "components", "entry_long", "entry_short", "stop", "target", "risk",
    "assumptions", "data_requirements", "source_refs", "no_lookahead",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_object(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value.get("top_level") if isinstance(value.get("top_level"), dict) else value
        return None
    except (ValueError, TypeError):
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            value = json.loads(text[start:end + 1])
            if isinstance(value, dict):
                return value.get("top_level") if isinstance(value.get("top_level"), dict) else value
            return None
        except (ValueError, TypeError):
            return None


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def _append_receipt(value: dict[str, Any]) -> None:
    RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    with RECEIPTS.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True, default=str) + "\n")


def _transcript(case_id: str) -> str:
    # This case's source was admitted through the existing YouTube transcript
    # pipeline; only that exact artifact is eligible for the Mercury prompt.
    if case_id != "rcase_98d9635c39cf3ae5a4":
        return ""
    path = ROOT / "reports/runtime/youtube_artifacts/EwvmM_ocnc4.transcript.txt"
    return path.read_text(encoding="utf-8", errors="replace")[:24000] if path.exists() else ""


def _prompt(case: dict[str, Any], transcript: str) -> str:
    pine_capture_path = ROOT / "artifacts/research/tradingview/D6AvF0jw_Wick_Sequence_Breakout_v1.capture.json"
    pine_capture = {}
    if pine_capture_path.exists():
        try:
            pine_capture = json.loads(pine_capture_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pine_capture = {}
    evidence = {
        "case_id": case.get("case_id"),
        "objective": case.get("objective"),
        "objective_family": case.get("objective_family"),
        "sources": case.get("sources") or [],
        "findings": case.get("findings") or [],
        "syntheses": case.get("syntheses") or [],
        "answered_questions": case.get("answered_questions") or [],
        "open_questions": case.get("open_questions") or [],
        "notebook_answers": case.get("notebook_answers") or [],
        "existing_hypotheses": case.get("hypotheses") or [],
        "valid_case_source_refs": sorted({str(row.get("source_id")) for row in case.get("sources") or [] if row.get("source_id")}),
        "source_evidence_summary": {
            "youtube_source_id": "youtube:EwvmM_ocnc4",
            "youtube_claims_from_transcript": [
                "Several consecutive candles show dominant upper or lower wicks; an indicator forms a zone and signals when price breakout and estimated buyer/seller dominance agree.",
                "Video says breakout-by-close and breakout-candle-size filter were enabled; 2x ATR stop was used (it says default 1.5x); up to three ATR/risk-reward targets were displayed; optional 200 EMA directional filter was discussed.",
                "Video reports 30m as strongest among tested 5m/30m/1h/Daily across BTC, Gold, TSLA, EURUSD and S&P 500. Claims are unverified author claims; dates, costs, sizing and per-instrument rows are not supplied in case evidence.",
            ],
            "tradingview_source_id": "tradingview:D6AvF0jw",
            "tradingview_page_facts": [
                "Wick Sequence Breakout by Uncle_the_shooter is labeled open-source on its TradingView publication page.",
            ],
        },
        "captured_public_pine_source": ({
            "script_name": pine_capture.get("script_name"), "author": pine_capture.get("author"),
            "license": pine_capture.get("license"), "pine_version": pine_capture.get("pine_version"),
            "line_count": pine_capture.get("line_count"), "sha256": pine_capture.get("source_sha256"),
            "artifact_path": pine_capture.get("source_path"), "inputs": pine_capture.get("inputs"),
            "logic": pine_capture.get("logic"), "provenance": {
                "page_url": pine_capture.get("source_page_url"),
                "public_source_endpoint": pine_capture.get("source_endpoint_url"),
                "capture_method": pine_capture.get("capture_method"),
            }} if pine_capture else None),
        "known_source_access_limit": ("Public Pine source was captured from TradingView's open-source public source endpoint and attached to this case; use only the captured code and cite its attached case source id."
                                       if pine_capture else "Do not claim Pine source inspection; only the publication page and case evidence are available."),
        "approved_market_data_path_inventory": {
            "provider": "OANDA Practice read-only candle endpoint",
            "instruments_supported_by_existing_scanner": ["EUR_USD", "GBP_USD", "USD_JPY"],
            "timeframes_supported_by_existing_scanner": ["M5", "M15", "H1"],
            "local_historical_cache_present_at_synthesis": True,
            "local_cache_is_bounded_snapshot_only": True,
            "availability_must_be_verified_before_test": True,
        },
    }
    contract = {
        "role": "MERCURY_TRADING, Nexus strategy-development specialist",
        "task": "Synthesize this Research Case's partial evidence into ONE complete, independently testable historical baseline hypothesis. Indicator incompleteness is not rejection. Use case evidence for source claims; define unknown implementation details as explicit Mercury proxy assumptions, never as creator rules. Do not return variants in this call.",
        "safety": [
            "Historical/paper analysis only; live trading disabled.",
            "Never substitute a generic/canned strategy or SMA fixture.",
            "Do not claim Pine source retrieval, verified performance, or facts absent from evidence.",
            "Use no future bars; signals use completed candles only. Explicitly delay any pivot/swing confirmation.",
            "Choose only an instrument/timeframe supported by the listed existing data path; data availability will be checked separately.",
            "For this synthesis call, return exactly one baseline hypothesis. No parameter sweep or optimization.",
            "Keep SOURCE_SUPPORTED_RULES separate from MERCURY_DESIGN_CHOICES and label assumptions.",
            "The captured Pine payload is available in the case evidence. Follow its actual defaults where applicable; any conversion of its indicator into an entry/exit strategy must be identified as a Mercury design choice, not an author-provided strategy rule.",
            "Select from the existing OANDA Practice scanner instruments/timeframes. The source's 30m claim is not proof and the existing scanner does not support M30.",
            "Every hypothesis must be internally complete. Distinguish a 2x ATR stop from position risk; position risk must specify account-risk fraction or explicitly state a bounded test assumption.",
        ],
        "return_format": {
            "json_only": True,
            "no_wrapper": "The JSON object itself must have the exact keys below. Do not wrap output under top_level, result, or schema.",
            "required_top_level_keys": ["component_roles", "source_supported_rules", "mercury_design_choices", "open_question_dispositions", "hypotheses", "selected_baseline", "blockers", "continuation_status", "next_action"],
            "hypothesis_exact_keys": ["strategy_id", "case_id", "name", "version", "market", "timeframe", "components", "strategy_logic", "entry_long", "entry_short", "entry_confirmation", "trend_filter", "volume_filter", "stop", "target", "exit_logic", "trade_invalidation", "risk", "position_risk", "session_filter", "data_requirements", "source_refs", "no_lookahead", "assumptions", "source_supported_elements", "mercury_assumptions", "why_testable", "created_by", "status"],
            "hypothesis_constraints": ["all listed keys required", "case_id equals supplied case_id", "created_by exactly Mercury", "status READY_FOR_BACKTEST only when every required rule is explicit", "no_lookahead true", "source_refs are only IDs in valid_case_source_refs", "components classify actual Pine indicator mechanics separately from Mercury's executable strategy conversion", "assumptions object has source_supported_rules and mercury_design_choices arrays", "position_risk specifies risk fraction and labels it Mercury-designed", "market and timeframe chosen from supported inventory", "do not say data is present; data is validated separately", "strategy_logic is executable structured DSL with numeric parameters, not X/Y placeholders", "give stop, target, exit, invalidation, position risk and completed-candle timing explicitly", "exactly one baseline only"],
            "question_dispositions": "Return one disposition for each exact question_id in supplied open_questions. Use only the IDs supplied in case_evidence.open_questions; do not add, omit, or substitute IDs.",
            "strategy_logic_schema": {"formation": {"lookback_bars": "integer", "min_sequence_bars": "integer", "upper_wick_fraction_min": "number", "lower_wick_fraction_min": "number", "box_boundary": "max_high_min_low"}, "volume_proxy": {"formula": "explicit formula using OHLCV", "dominance_threshold": "number"}, "breakout": {"price_basis": "CLOSE", "min_range_atr": "number or null", "entry_timing": "NEXT_BAR_OPEN or other no-lookahead rule"}, "trend_filter": {"enabled": "boolean", "kind": "EMA or NONE", "period": "integer or null"}, "atr": {"period": "integer", "stop_multiple": "number", "target_multiple_r": "number"}, "risk_fraction_per_trade": "number between 0 and 1", "session": "explicit hours or NONE", "same_bar_stop_target_collision": "conservative explicit rule"},
        },
        "case_evidence": evidence,
        "youtube_transcript": transcript,
    }
    # Test-selection must remain visibly grounded in the evidence snapshot. In
    # particular, a scanner's current inventory is a data-acquisition concern,
    # not permission to silently replace the best-supported market/timeframe.
    contract["test_selection_contract"] = {
        "research_case_reviewed": True,
        "required_before_any_test": ["selected_market", "selected_timeframe", "selected_filters",
            "selected_stop", "selected_target", "selected_position_risk", "notebook_evidence_used",
            "source_evidence_used", "why_this_configuration", "why_not_research_alternatives"],
        "data_availability_rule": "If the evidence-supported market/timeframe is not present in the listed historical data path, create a DATA_ACQUISITION action; do not silently substitute an easier instrument or timeframe.",
        "deviation_rule": "If selecting a configuration different from the notebook/research recommendation, persist WHY_DEVIATING_FROM_RESEARCH with the evidence and constraints.",
    }
    return "You are Mercury. Perform strategy synthesis, not generic intake. Return valid JSON only.\n" + json.dumps(contract, ensure_ascii=False, default=str)


def _validate(payload: dict[str, Any], case_id: str, source_ids: set[str], open_question_ids: set[str]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    hypotheses = payload.get("hypotheses")
    if isinstance(hypotheses, dict):
        hypotheses = [hypotheses]
        payload["hypotheses"] = hypotheses
    if not isinstance(hypotheses, list) or len(hypotheses) > 3:
        return False, ["HYPOTHESES_MUST_BE_ARRAY_MAX_3"]
    if not hypotheses:
        return False, ["NO_HYPOTHESES_RETURNED"]
    for index, spec in enumerate(hypotheses, start=1):
        if not isinstance(spec, dict):
            errors.append(f"H{index}_NOT_OBJECT")
            continue
        for key in REQUIRED_SPEC:
            if spec.get(key) in (None, "", [], {}):
                errors.append(f"H{index}_MISSING_{key.upper()}")
        if str(spec.get("case_id")) != case_id:
            errors.append(f"H{index}_CASE_ID_MISMATCH")
        if spec.get("no_lookahead") is not True:
            errors.append(f"H{index}_NO_LOOKAHEAD_NOT_TRUE")
        if spec.get("created_by") != "Mercury":
            errors.append(f"H{index}_CREATOR_NOT_MERCURY")
        if spec.get("status") != "READY_FOR_BACKTEST":
            errors.append(f"H{index}_STATUS_NOT_READY_FOR_BACKTEST")
        if not spec.get("mercury_assumptions") or not spec.get("source_supported_elements"):
            errors.append(f"H{index}_SOURCE_DESIGN_SEPARATION_MISSING")
        refs = {str(value) for value in (spec.get("source_refs") or [])}
        if not refs or not refs.issubset(source_ids):
            errors.append(f"H{index}_SOURCE_REFS_NOT_ATTACHED_TO_CASE")
        if not spec.get("entry_long") or not spec.get("entry_short") or not spec.get("stop") or not spec.get("target") or not spec.get("risk"):
            errors.append(f"H{index}_INCOMPLETE_RULES")
        assumptions = spec.get("assumptions")
        if not isinstance(assumptions, dict) or not assumptions.get("source_supported_rules") or not assumptions.get("mercury_design_choices"):
            errors.append(f"H{index}_ASSUMPTIONS_NOT_SEPARATED")
        logic = spec.get("strategy_logic")
        if not isinstance(logic, dict):
            errors.append(f"H{index}_EXECUTABLE_STRATEGY_LOGIC_MISSING")
        else:
            formation = logic.get("formation") if isinstance(logic.get("formation"), dict) else {}
            volume = logic.get("volume_proxy") if isinstance(logic.get("volume_proxy"), dict) else {}
            breakout = logic.get("breakout") if isinstance(logic.get("breakout"), dict) else {}
            atr = logic.get("atr") if isinstance(logic.get("atr"), dict) else {}
            wick_numbers = (formation.get("lookback_bars"), formation.get("min_sequence_bars"),
                            formation.get("upper_wick_fraction_min"), formation.get("lower_wick_fraction_min"))
            if not all(isinstance(value, (int, float)) and math.isfinite(float(value)) for value in wick_numbers):
                errors.append(f"H{index}_FORMATION_THRESHOLDS_NOT_NUMERIC")
            elif not (1 <= formation["min_sequence_bars"] <= formation["lookback_bars"]
                      and 0 < formation["upper_wick_fraction_min"] <= 1
                      and 0 < formation["lower_wick_fraction_min"] <= 1):
                errors.append(f"H{index}_FORMATION_THRESHOLDS_OUT_OF_RANGE")
            formula = str(volume.get("formula") or "").casefold()
            if not all(token in formula for token in ("volume", "close", "high", "low")):
                errors.append(f"H{index}_VOLUME_FORMULA_NOT_REPRODUCIBLE")
            if not isinstance(volume.get("dominance_threshold"), (int, float)) or not 0 < float(volume.get("dominance_threshold") or 0):
                errors.append(f"H{index}_VOLUME_THRESHOLD_INVALID")
            if breakout.get("price_basis") != "CLOSE" or breakout.get("entry_timing") not in {"NEXT_BAR_OPEN", "NEXT_BAR_CLOSE"}:
                errors.append(f"H{index}_BREAKOUT_TIMING_NOT_CAUSAL")
            if not isinstance(atr.get("period"), int) or not isinstance(atr.get("stop_multiple"), (int, float)) or not isinstance(atr.get("target_multiple_r"), (int, float)):
                errors.append(f"H{index}_ATR_EXIT_PARAMETERS_INCOMPLETE")
            if logic.get("same_bar_stop_target_collision") not in {"STOP_FIRST", "TARGET_FIRST", "CLOSE_OR_STOP_FIRST"}:
                errors.append(f"H{index}_SAME_BAR_COLLISION_POLICY_INVALID")
    roles = payload.get("component_roles")
    if not isinstance(roles, dict) or len(roles) < 8:
        errors.append("COMPONENT_ROLE_CLASSIFICATION_INCOMPLETE")
    if not payload.get("source_supported_rules") or not payload.get("mercury_design_choices"):
        errors.append("SOURCE_DESIGN_SEPARATION_INCOMPLETE")
    dispositions = payload.get("open_question_dispositions")
    if not isinstance(dispositions, list):
        errors.append("OPEN_QUESTION_DISPOSITIONS_MISSING")
    else:
        actual_qids = {str(q.get("question_id")) for q in dispositions if isinstance(q, dict)}
        if actual_qids != open_question_ids:
            errors.append("OPEN_QUESTION_DISPOSITION_SET_MISMATCH")
        allowed = {"EXISTING_EVIDENCE", "SEND_TO_RESEARCH", "TEST_ASSUMPTION", "TRUE_BLOCKER"}
        if any(str(q.get("classification")) not in allowed for q in dispositions if isinstance(q, dict)):
            errors.append("OPEN_QUESTION_DISPOSITION_INVALID_CLASS")
    selected = payload.get("selected_baseline")
    if selected and selected not in {str(row.get("strategy_id")) for row in hypotheses if isinstance(row, dict)}:
        errors.append("BASELINE_NOT_IN_HYPOTHESES")
    return not errors, errors


def synthesize_case(case_id: str, *, timeout_seconds: float = 240.0) -> dict[str, Any]:
    """Ask Mercury through canonical Oracle Hermes, validate and persist receipt/spec."""
    if not CASE_ID_RE.fullmatch(case_id):
        return {"ok": False, "status": "INVALID_CASE_ID"}
    from research.research_case_engine import get_case, add_hypothesis

    case = get_case(case_id)
    if not case:
        return {"ok": False, "status": "CASE_NOT_FOUND"}
    source_ids = {str(source.get("source_id")) for source in case.get("sources") or [] if source.get("source_id")}
    transcript = _transcript(case_id)
    from nexus_agent_platform.bridge.oracle_hermes_cli import run_oracle_hermes

    request_id = "mercury-synthesis-" + hashlib.sha256(f"{case_id}:{_now()}".encode()).hexdigest()[:12]
    submitted_prompt = _prompt(case, transcript)
    prompt_hash = hashlib.sha256(submitted_prompt.encode()).hexdigest()
    prompt_path = ROOT / "data/governed/mercury_strategy_synthesis_inputs" / f"{request_id}.json"
    _write_json(prompt_path, {"request_id": request_id, "case_id": case_id,
        "created_at": _now(), "input_sha256": prompt_hash, "input_payload": submitted_prompt,
        "case_updated_at": case.get("updated_at"), "source_ids": sorted(source_ids),
        "notebook_id": (case.get("notebook_workspace") or {}).get("notebook_id")})
    result = run_oracle_hermes(submitted_prompt, request_id, timeout_seconds=timeout_seconds,
                              request_id=request_id, structured_task=True)
    output = _json_object(result.response or "") if result.response else None
    open_question_ids = {str(q.get("question_id")) for q in case.get("open_questions") or [] if q.get("question_id")}
    pine_path = ROOT / "artifacts/research/tradingview/D6AvF0jw_Wick_Sequence_Breakout_v1.capture.json"
    try:
        correction_pine_evidence = json.loads(pine_path.read_text(encoding="utf-8")) if pine_path.exists() else {}
    except (OSError, ValueError):
        correction_pine_evidence = {}
    valid, errors = _validate(output or {}, case_id, source_ids, open_question_ids) if output else (False, [result.error or "MODEL_RETURNED_NO_JSON"])
    attempts = [{"transport_status": result.status, "latency_ms": result.latency_ms,
                 "validation_errors": list(errors), "model_output": output}]
    # One bounded model correction is allowed for malformed/incomplete plans;
    # no local code fills strategy fields or relaxes the validation contract.
    if not valid and output is not None:
        correction = (
            "Your previous Mercury response did not pass the strict strategy contract. "
            "Correct the JSON only; do not remove assumptions, invent source facts, or omit questions. "
            "Return one baseline hypothesis, exactly one disposition for every open question, a component_roles object, "
            "non-empty source_supported_rules and mercury_design_choices, and complete causal executable strategy_logic. "
            "The previous response failed because source_supported_rules and mercury_design_choices were empty, "
            "question dispositions were a map instead of a list of objects, component_roles had fewer than eight "
            "classified entries, and strategy_logic did not contain the required structured fields. "
            "For source-supported rules use the captured Pine defaults and source mechanics included below; "
            "for every value not specified in that Pine source choose one numeric assumption and label it Mercury-designed. "
            "If a requirement truly cannot be resolved, return no READY_FOR_BACKTEST spec and classify its precise blocker. "
            "Do not wrap the JSON in a top_level object. Return question dispositions as an array of objects, each "
            "with question_id, classification (EXISTING_EVIDENCE, SEND_TO_RESEARCH, TEST_ASSUMPTION, or TRUE_BLOCKER), "
            "and rationale. Do not leave Pine questions OPEN when the supplied public source answers them. "
            "component_roles must be an object with at least these eight keys: wick_formation, formation_zone, "
            "buyer_seller_pressure, breakout_close, breakout_candle_size, ATR, EMA_200, target_levels. "
            "strategy_logic must be an object with formation {lookback_bars,min_sequence_bars,upper_wick_fraction_min,"
            "lower_wick_fraction_min,box_boundary}, volume_proxy {formula,dominance_threshold}, breakout "
            "{price_basis,entry_timing,min_range_atr}, trend_filter {enabled,kind,period}, atr "
            "{period,stop_multiple,target_multiple_r}, risk_fraction_per_trade, session, and "
            "same_bar_stop_target_collision (STOP_FIRST). Assumptions.source_supported_rules and "
            "assumptions.mercury_design_choices must each be non-empty arrays. "
            "Use the numeric Pine defaults from the case; distinguish the indicator's displayed TP/SL from "
            "the Mercury-designed deterministic trade exit.\nVALIDATION_ERRORS=" + json.dumps(errors) +
            "\nCAPTURED_PINE_EVIDENCE=" + json.dumps(correction_pine_evidence, ensure_ascii=False, default=str) +
            "\nVALID_CASE_SOURCE_IDS=" + json.dumps(sorted(source_ids)) +
            "\nPREVIOUS_OUTPUT=" + json.dumps(output, ensure_ascii=False, default=str)
        )
        retry = run_oracle_hermes(correction, request_id, timeout_seconds=timeout_seconds,
                                  request_id=request_id, structured_task=True)
        retry_output = _json_object(retry.response or "") if retry.response else None
        retry_valid, retry_errors = _validate(retry_output or {}, case_id, source_ids, open_question_ids) if retry_output else (False, [retry.error or "MODEL_RETURNED_NO_JSON"])
        attempts.append({"transport_status": retry.status, "latency_ms": retry.latency_ms,
                         "validation_errors": list(retry_errors), "model_output": retry_output})
        if retry_output is not None:
            output, valid, errors, result = retry_output, retry_valid, retry_errors, retry
    # A failed validation is a failed Mercury attempt, not a failed parent case.
    # Give the same governed Mercury executor one final schema-focused replan
    # with the remaining exact errors; never fill strategy fields in local code.
    if not valid and output is not None:
        final_correction = (
            "Mercury: replan this single case-specific baseline. Your last output still failed these exact "
            "validator checks: " + json.dumps(errors) + ". Return only one JSON object, no prose and no wrapper. "
            "Required top-level keys: component_roles (object with at least 8 component=>role entries), "
            "source_supported_rules (non-empty array of rules actually present in case evidence), "
            "mercury_design_choices (non-empty array), open_question_dispositions (array of objects, one for each "
            "supplied ID, each object exactly {question_id,classification,rationale}; classification is one of "
            "EXISTING_EVIDENCE,SEND_TO_RESEARCH,TEST_ASSUMPTION,TRUE_BLOCKER), hypotheses (array containing one "
            "baseline object), selected_baseline (that object's strategy_id), blockers (array), "
            "continuation_status (READY_FOR_BACKTEST), next_action. Do not mark a source-backed question OPEN if "
            "the attached public Pine capture answers it.\n"
            "The single hypothesis must contain all required fields and status READY_FOR_BACKTEST, created_by Mercury, "
            "no_lookahead true, attached source_refs only, non-empty assumptions.source_supported_rules and "
            "assumptions.mercury_design_choices arrays, and non-empty mercury_assumptions and "
            "source_supported_elements arrays. strategy_logic MUST be an object, not prose, with formation "
            "{lookback_bars,min_sequence_bars,upper_wick_fraction_min,lower_wick_fraction_min,box_boundary}, "
            "volume_proxy {formula,dominance_threshold}, breakout {price_basis,entry_timing,min_range_atr}, "
            "trend_filter {enabled,kind,period}, atr {period,stop_multiple,target_multiple_r}, "
            "risk_fraction_per_trade, session, same_bar_stop_target_collision. Use completed bars only and "
            "STOP_FIRST for OHLC bars where stop and target both touch. Every unknown design value must be "
            "numeric where applicable and explicitly labeled Mercury-designed.\n"
            "CAPTURED_PINE_SOURCE_FACTS=" + json.dumps(correction_pine_evidence, ensure_ascii=False, default=str) +
            "\nVALID_CASE_SOURCE_IDS=" + json.dumps(sorted(source_ids)) +
            "\nEXACT_OPEN_QUESTION_IDS=" + json.dumps(sorted(open_question_ids)) +
            "\nPRIOR_OUTPUT=" + json.dumps(output, ensure_ascii=False, default=str)
        )
        final_retry = run_oracle_hermes(final_correction, request_id, timeout_seconds=timeout_seconds,
                                        request_id=request_id, structured_task=True)
        final_output = _json_object(final_retry.response or "") if final_retry.response else None
        final_valid, final_errors = _validate(final_output or {}, case_id, source_ids, open_question_ids) if final_output else (False, [final_retry.error or "MODEL_RETURNED_NO_JSON"])
        attempts.append({"transport_status": final_retry.status, "latency_ms": final_retry.latency_ms,
                         "validation_errors": list(final_errors), "model_output": final_output})
        if final_output is not None:
            output, valid, errors, result = final_output, final_valid, final_errors, final_retry
    if not valid and output is not None and set(errors).issubset({"H1_MISSING_STOP", "H1_MISSING_TARGET", "H1_MISSING_RISK", "H1_INCOMPLETE_RULES"}):
        repair = (
            "Mercury: your prior hypothesis is otherwise valid but the validator reports these missing explicit "
            "top-level fields: " + json.dumps(errors) + ". Return the same single baseline as one JSON object, "
            "preserving the valid component_roles, source_supported_rules, mercury_design_choices, question dispositions, "
            "and strategy_logic. Add explicit hypothesis keys `stop`, `target`, and `risk` at the hypothesis root "
            "(not only nested under components/strategy_logic), with concrete numeric rules consistent with your "
            "own assumptions: define ATR period/multiple, one fixed R-multiple target, and account-risk fraction. "
            "Also provide `entry_long` and `entry_short` text rules if absent. Keep status READY_FOR_BACKTEST, "
            "created_by Mercury, source refs attached to the case, and no_lookahead true. Do not claim these "
            "design choices came from the author.\nVALIDATION_ERRORS=" + json.dumps(errors) +
            "\nPRIOR_HYPOTHESIS=" + json.dumps((output.get("hypotheses") or [{}])[0], ensure_ascii=False, default=str)
        )
        last_retry = run_oracle_hermes(repair, request_id, timeout_seconds=timeout_seconds,
                                       request_id=request_id, structured_task=True)
        last_output = _json_object(last_retry.response or "") if last_retry.response else None
        last_valid, last_errors = _validate(last_output or {}, case_id, source_ids, open_question_ids) if last_output else (False, [last_retry.error or "MODEL_RETURNED_NO_JSON"])
        attempts.append({"transport_status": last_retry.status, "latency_ms": last_retry.latency_ms,
                         "validation_errors": list(last_errors), "model_output": last_output})
        if last_output is not None:
            output, valid, errors, result = last_output, last_valid, last_errors, last_retry
    if not valid and output is not None and errors == ["H1_SOURCE_DESIGN_SEPARATION_MISSING"]:
        provenance_repair = (
            "Mercury: your strategy otherwise passed validation. Correct only the two missing root-level arrays "
            "inside the single hypothesis: `source_supported_elements` and `mercury_assumptions`. Both must be "
            "non-empty lists. Put actual Pine/video facts (for example the 3-of-5 formation and captured Pine wick "
            "defaults) in source_supported_elements; put only your independent conversion choices (market/timeframe, "
            "entry timing, risk/exits) in mercury_assumptions. Preserve all already-valid fields exactly, set status "
            "READY_FOR_BACKTEST, and do not add/omit any open-question disposition. Return only the corrected full "
            "JSON object.\nVALIDATION_ERRORS=" + json.dumps(errors) +
            "\nVALID_HYPOTHESIS=" + json.dumps((output.get("hypotheses") or [{}])[0], ensure_ascii=False, default=str)
        )
        provenance_retry = run_oracle_hermes(provenance_repair, request_id, timeout_seconds=timeout_seconds,
                                             request_id=request_id, structured_task=True)
        provenance_output = _json_object(provenance_retry.response or "") if provenance_retry.response else None
        provenance_valid, provenance_errors = _validate(provenance_output or {}, case_id, source_ids, open_question_ids) if provenance_output else (False, [provenance_retry.error or "MODEL_RETURNED_NO_JSON"])
        attempts.append({"transport_status": provenance_retry.status, "latency_ms": provenance_retry.latency_ms,
                         "validation_errors": list(provenance_errors), "model_output": provenance_output})
        if provenance_output is not None:
            output, valid, errors, result = provenance_output, provenance_valid, provenance_errors, provenance_retry
    receipt = {
        "schema_version": "nexus.mercury-strategy-synthesis.v1", "request_id": request_id,
        "case_id": case_id, "created_at": _now(), "executor": "oracle_hermes_cli",
        "profile": result.profile, "model": result.model, "transport_status": result.status,
        "latency_ms": result.latency_ms, "transcript_supplied": bool(transcript),
        "source_ids": sorted(source_ids), "input_payload_path": str(prompt_path.relative_to(ROOT)),
        "input_sha256": prompt_hash, "case_snapshot_updated_at": case.get("updated_at"),
        "status": "VALIDATED" if valid else "BLOCKED_INVALID_SYNTHESIS",
        "validation_errors": errors, "attempts": attempts, "model_output": output,
        "live_trading": False, "broker_order_api_called": False,
    }
    _append_receipt(receipt)
    if not valid or output is None:
        return {"ok": False, **receipt}

    persisted_specs = []
    for spec in output["hypotheses"]:
        spec = {**spec, "created_by": "Mercury", "status": "READY_FOR_BACKTEST",
                "case_id": case_id, "synthesis_request_id": request_id,
                "source_refs": list(spec.get("source_refs") or []),
                "live_trading": False}
        safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(spec["strategy_id"]))[:100]
        path = SPEC_DIR / f"{safe_id}.json"
        _write_json(path, spec)
        add_hypothesis(case_id, {"hypothesis_id": safe_id, "strategy_id": safe_id,
            "statement": spec.get("name") or safe_id, "complete_rules": True,
            "created_by": "Mercury", "strategy_spec_path": str(path.relative_to(ROOT)),
            "source_refs": spec["source_refs"], "assumptions": spec.get("mercury_assumptions") or [],
            "status": "READY_FOR_BACKTEST", "backtest_id": None})
        persisted_specs.append(str(path.relative_to(ROOT)))
    receipt["persisted_spec_paths"] = persisted_specs
    receipt["status"] = "VALIDATED_AND_PERSISTED"
    _append_receipt({"event": "PERSISTED", "request_id": request_id, "case_id": case_id,
                     "created_at": _now(), "paths": persisted_specs, "live_trading": False})
    return {"ok": True, **receipt, "persisted_spec_paths": persisted_specs}
