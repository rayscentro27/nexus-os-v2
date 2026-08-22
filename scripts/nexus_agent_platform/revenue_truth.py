"""GoClear Revenue Truth Layer.

Read/aggregate only.  Observations are append-only, source-linked, deduplicated,
and explicitly classified so test money, synthetic money, pipeline, estimates,
and unknown data cannot become actual revenue by arithmetic accident.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

from nexus_agent_platform.governed import persistence
from nexus_agent_platform.opportunities.engine import opportunity_portfolio, opportunity_rankings

REVENUE_OBSERVATION_SCHEMA = "nexus.revenue-observation.v1"
REVENUE_SNAPSHOT_SCHEMA = "nexus.revenue-snapshot.v1"
TRUTH_CLASSES = frozenset({"ACTUAL", "TEST", "SYNTHETIC", "PIPELINE", "OPPORTUNITY_ESTIMATE", "FORECAST", "MANUAL_VERIFIED", "UNKNOWN", "NOT_CONNECTED"})
FRESHNESS_CLASSES = frozenset({"CURRENT", "AGING", "STALE", "UNKNOWN"})
METRIC_KEYS = (
    "readiness_review_leads", "readiness_review_purchases_97", "upgrade_purchases_297_497",
    "subscription_prospects", "active_subscriptions", "monthly_recurring_revenue",
    "funding_applications", "funding_pipeline", "funding_commissions_actual",
    "funding_commissions_pipeline", "commission_opportunities", "affiliate_referral_clicks",
    "affiliate_referral_conversions", "affiliate_commissions_actual", "seo_content_leads",
    "booked_calls", "estimated_revenue_potential", "actual_revenue",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _parse(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result if result.tzinfo else result.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def freshness_status(observed_at: Any, *, now: Optional[datetime] = None, aging_days: int = 7, stale_days: int = 30) -> str:
    parsed = _parse(observed_at)
    if not parsed:
        return "UNKNOWN"
    age = max(0.0, ((now or datetime.now(timezone.utc)) - parsed.astimezone(timezone.utc)).total_seconds() / 86400)
    return "CURRENT" if age <= aging_days else "AGING" if age <= stale_days else "STALE"


def _safe_number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) and result >= 0 else None


def build_revenue_observation(*, metric_key: str, value: Any, unit: str, truth_class: str, source_system: str, source_record_ref: str, business_id: str = "goclear", occurred_at: Optional[str] = None, observed_at: Optional[str] = None, attribution: Optional[Dict[str, Any]] = None, status: str = "OBSERVED", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not metric_key or metric_key not in METRIC_KEYS and metric_key not in {"test_revenue", "synthetic_revenue"}:
        raise ValueError("invalid metric_key")
    truth_class = str(truth_class).upper()
    if truth_class not in TRUTH_CLASSES:
        raise ValueError("invalid truth_class")
    number = _safe_number(value)
    if number is None:
        raise ValueError("monetary/count observation must be a finite non-negative number")
    if not source_system or not source_record_ref:
        raise ValueError("source_system and source_record_ref are required")
    observed = observed_at or _now()
    return {
        "schema_version": REVENUE_OBSERVATION_SCHEMA,
        "observation_id": "revobs_" + _hash([business_id, metric_key, source_system, source_record_ref])[:24],
        "business_id": business_id,
        "metric_key": metric_key,
        "value": int(number) if number.is_integer() else number,
        "unit": unit,
        "truth_class": truth_class,
        "source_system": source_system,
        "source_record_ref": source_record_ref,
        "proof_event_ref": None,
        "occurred_at": occurred_at or observed,
        "observed_at": observed,
        "period_start": None,
        "period_end": None,
        "attribution": {key: value for key, value in (attribution or {}).items() if key in {"offer_id", "opportunity_id", "client_ref_safe", "campaign_ref", "partner_ref", "attribution_class"}},
        "status": status,
        "freshness": freshness_status(observed),
        "metadata": metadata or {},
    }


def validate_revenue_observation(observation: Dict[str, Any]) -> Dict[str, Any]:
    required = ("schema_version", "observation_id", "business_id", "metric_key", "value", "unit", "truth_class", "source_system", "source_record_ref", "observed_at")
    if not isinstance(observation, dict):
        return {"valid": False, "reason": "not_object"}
    missing = [field for field in required if field not in observation]
    if missing:
        return {"valid": False, "reason": "missing_fields", "fields": missing}
    if observation.get("schema_version") != REVENUE_OBSERVATION_SCHEMA:
        return {"valid": False, "reason": "invalid_schema"}
    if observation.get("truth_class") not in TRUTH_CLASSES:
        return {"valid": False, "reason": "invalid_truth_class"}
    if _safe_number(observation.get("value")) is None:
        return {"valid": False, "reason": "invalid_value"}
    return {"valid": True, "reason": "valid"}


def list_revenue_observations() -> List[Dict[str, Any]]:
    seen: set[str] = set()
    rows: List[Dict[str, Any]] = []
    for row in persistence.read_records("revenue_observations"):
        key = str(row.get("observation_id"))
        if key and key not in seen:
            seen.add(key)
            rows.append(row)
    return rows


def record_revenue_observation(observation: Dict[str, Any]) -> Dict[str, Any]:
    valid = validate_revenue_observation(observation)
    if not valid["valid"]:
        raise ValueError("invalid revenue observation: " + valid["reason"])
    existing = next((row for row in list_revenue_observations() if row.get("observation_id") == observation["observation_id"]), None)
    if existing:
        persistence.emit_audit_event({"type": "revenue_observation_duplicate_suppressed", "observation_id": observation["observation_id"], "source_system": observation["source_system"], "external_action_performed": False})
        return {"status": "DUPLICATE_SUPPRESSED", "observation": existing}
    persistence.append_record("revenue_observations", observation)
    event = persistence.emit_audit_event({"type": "revenue_observation_recorded", "observation_id": observation["observation_id"], "metric_key": observation["metric_key"], "truth_class": observation["truth_class"], "source_system": observation["source_system"], "external_action_performed": False})
    return {"status": "RECORDED", "observation": observation, "event": event}


def _window_start(period: str, now: datetime) -> Optional[datetime]:
    period = period.upper()
    if period == "TODAY":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period in {"7 DAYS", "7D"}:
        return now - timedelta(days=7)
    if period in {"30 DAYS", "30D"}:
        return now - timedelta(days=30)
    if period == "MTD":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if period == "QUARTER":
        month = ((now.month - 1) // 3) * 3 + 1
        return now.replace(month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
    return None


def _within(row: Dict[str, Any], start: Optional[datetime], end: datetime) -> bool:
    occurred = _parse(row.get("occurred_at") or row.get("observed_at"))
    return bool(occurred and (start is None or occurred >= start) and occurred <= end)


def aggregate_metric(metric_key: str, *, period: str = "30 DAYS", now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    rows = [row for row in list_revenue_observations() if row.get("metric_key") == metric_key and _within(row, _window_start(period, now), now)]
    if not rows:
        return {"value": None, "truth_class": "UNKNOWN", "source_status": "NOT_CONNECTED", "observation_count": 0, "observed_zero": False, "freshness": "UNKNOWN", "source_refs": []}
    truth_classes = sorted({row.get("truth_class") for row in rows})
    value = sum(float(row.get("value", 0)) for row in rows)
    truth = truth_classes[0] if len(truth_classes) == 1 else "MIXED"
    return {"value": int(value) if value.is_integer() else value, "truth_class": truth, "truth_classes": truth_classes, "source_status": "CONNECTED", "observation_count": len(rows), "observed_zero": value == 0, "freshness": "STALE" if any(row.get("freshness") == "STALE" for row in rows) else "CURRENT", "source_refs": [row.get("source_record_ref") for row in rows]}


def _actual_metric(metric_key: str, *, period: str, now: datetime) -> Dict[str, Any]:
    rows = [row for row in list_revenue_observations() if row.get("metric_key") == metric_key and row.get("truth_class") == "ACTUAL" and _within(row, _window_start(period, now), now)]
    if not rows:
        return {"value": None, "truth_class": "UNKNOWN", "source_status": "NOT_CONNECTED", "observation_count": 0, "observed_zero": False, "freshness": "UNKNOWN", "source_refs": []}
    value = sum(float(row["value"]) for row in rows)
    return {"value": int(value) if value.is_integer() else value, "truth_class": "ACTUAL", "source_status": "CONNECTED", "observation_count": len(rows), "observed_zero": value == 0, "freshness": "CURRENT", "source_refs": [row.get("source_record_ref") for row in rows]}


def _truth_revenue_class(metric: str, truth: str) -> str:
    return "ACTUAL" if truth == "ACTUAL" else "TEST" if truth == "TEST" else "SYNTHETIC" if truth == "SYNTHETIC" else truth


def source_statuses() -> Dict[str, Dict[str, str]]:
    observations = list_revenue_observations()
    has_actual = any(row.get("truth_class") == "ACTUAL" for row in observations)
    has_test = any(row.get("truth_class") == "TEST" for row in observations)
    return {
        "form_leads": {"status": "CONNECTED" if any(row.get("metric_key") in {"readiness_review_leads", "seo_content_leads"} for row in observations) else "NOT_CONNECTED", "truth": "OBSERVED" if observations else "UNKNOWN"},
        "booked_calls": {"status": "CONNECTED" if any(row.get("metric_key") == "booked_calls" for row in observations) else "NOT_CONNECTED", "truth": "OBSERVED" if observations else "UNKNOWN"},
        "stripe_live": {"status": "CONNECTED" if has_actual else "NOT_CONNECTED", "truth": "ACTUAL" if has_actual else "UNKNOWN"},
        "stripe_test": {"status": "CONNECTED_TEST" if has_test else "TEST_ONLY", "truth": "TEST" if has_test else "UNKNOWN"},
        "funding_outcomes": {"status": "PARTIAL", "truth": "PIPELINE_ONLY"},
        "affiliate": {"status": "NOT_CONNECTED", "truth": "UNKNOWN"},
        "opportunity_engine": {"status": "CONNECTED", "truth": "OPPORTUNITY_ESTIMATE_OR_PIPELINE"},
        "alpha": {"status": "CONNECTED", "truth": "EVIDENCE_BACKED_RESEARCH"},
    }


def build_revenue_snapshot(*, period: str = "30 DAYS", now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    metrics = {key: aggregate_metric(key, period=period, now=now) for key in METRIC_KEYS}
    metrics["actual_revenue"] = _actual_metric("actual_revenue", period=period, now=now)
    test_revenue = aggregate_metric("actual_revenue", period=period, now=now)
    test_rows = [row for row in list_revenue_observations() if row.get("metric_key") == "actual_revenue" and row.get("truth_class") == "TEST" and _within(row, _window_start(period, now), now)]
    synthetic_rows = [row for row in list_revenue_observations() if row.get("metric_key") == "actual_revenue" and row.get("truth_class") == "SYNTHETIC" and _within(row, _window_start(period, now), now)]
    portfolio = opportunity_portfolio()
    rankings = opportunity_rankings()
    needs_ray = rankings.get("needs_ray", [])
    snapshot = {
        "schema_version": REVENUE_SNAPSHOT_SCHEMA,
        "snapshot_id": "revsnap_" + _hash([period, now.isoformat(), len(list_revenue_observations())])[:24],
        "generated_at": now.isoformat(), "business": "GoClear", "period": period, "timezone": "UTC",
        "metrics": metrics,
        "test_revenue": {"value": sum(float(row["value"]) for row in test_rows) if test_rows else None, "truth_class": "TEST" if test_rows else "UNKNOWN", "observation_count": len(test_rows)},
        "synthetic_revenue": {"value": sum(float(row["value"]) for row in synthetic_rows) if synthetic_rows else None, "truth_class": "SYNTHETIC" if synthetic_rows else "UNKNOWN", "observation_count": len(synthetic_rows)},
        "pipeline": {"value": None, "truth_class": "PIPELINE", "source_status": "NOT_CONNECTED", "note": "No authoritative operating pipeline source connected."},
        "opportunity_pipeline": {"count": portfolio.get("total_active", 0), "qualified": portfolio.get("counts", {}).get("QUALIFIED", 0), "needs_ray": len(needs_ray), "value": portfolio.get("pipeline_value_estimate", {}).get("expected_total"), "truth_class": "OPPORTUNITY_ESTIMATE" if portfolio.get("pipeline_value_estimate", {}).get("status") == "ESTIMATED" else "UNKNOWN", "status": "CONNECTED"},
        "source_statuses": source_statuses(),
        "unknown_metrics": [key for key, metric in metrics.items() if metric.get("truth_class") == "UNKNOWN"],
        "needs_ray": [{"opportunity_id": row.get("opportunity_id"), "title": row.get("title"), "truth_class": "OPPORTUNITY_ESTIMATE", "reason": "explicit Ray review required"} for row in needs_ray],
        "revenue_truth": "CONNECTED" if metrics["actual_revenue"]["truth_class"] == "ACTUAL" else "NOT_CONNECTED",
        "freshness": "CURRENT" if list_revenue_observations() else "UNKNOWN",
        "external_action_performed": False,
    }
    snapshot["priority_items"] = priority_view(snapshot)
    return snapshot


def refresh_revenue_snapshot(*, period: str = "30 DAYS") -> Dict[str, Any]:
    snapshot = build_revenue_snapshot(period=period)
    persistence.append_record("revenue_snapshots", snapshot)
    persistence.emit_audit_event({"type": "revenue_snapshot_refreshed", "snapshot_id": snapshot["snapshot_id"], "observation_count": len(list_revenue_observations()), "truth_classes": sorted({row.get("truth_class") for row in list_revenue_observations()}), "external_action_performed": False})
    return snapshot


def priority_view(snapshot: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    snapshot = snapshot or build_revenue_snapshot()
    rows = []
    if snapshot.get("needs_ray"):
        rows.append({"priority": "P2", "title": "Review pending opportunity decisions", "why": "Phase K opportunity is awaiting Ray", "source": "governed opportunities", "truth_class": "OPPORTUNITY_ESTIMATE", "next_governed_action": "Ray review"})
    if snapshot.get("revenue_truth") == "NOT_CONNECTED":
        rows.append({"priority": "P2", "title": "Connect an authoritative actual-revenue read source", "why": "Actual revenue cannot be inferred from pipeline or test data", "source": "Revenue Truth Layer", "truth_class": "UNKNOWN", "next_governed_action": "Bounded read-only source review"})
    rows.append({"priority": "P4", "title": "Keep funding and affiliate outcomes classified", "why": "Expected commissions are not earned commissions", "source": "Revenue Truth Layer", "truth_class": "PIPELINE", "next_governed_action": "Manual verified import or approved connector review"})
    return rows


def answer_revenue_question(question: str, snapshot: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    snapshot = snapshot or build_revenue_snapshot()
    text = str(question).lower()
    if "pipeline" in text:
        return {"answer": f"Opportunity pipeline has {snapshot['opportunity_pipeline']['count']} active item(s); it is not actual revenue. Actual revenue remains {snapshot['metrics']['actual_revenue']['value'] if snapshot['metrics']['actual_revenue']['value'] is not None else 'UNKNOWN / NOT_CONNECTED'}.", "truth_class": snapshot["opportunity_pipeline"]["truth_class"], "source": "Phase K opportunity portfolio + Revenue Truth Layer"}
    if "actual" in text or "made" in text or "revenue" in text:
        metric = snapshot["metrics"]["actual_revenue"]
        return {"answer": f"Actual revenue is {metric['value'] if metric['value'] is not None else 'UNKNOWN / NOT_CONNECTED'}.", "truth_class": metric["truth_class"], "source": metric["source_status"]}
    if "approval" in text or "ray" in text:
        return {"answer": f"{len(snapshot.get('needs_ray', []))} opportunity decision(s) need Ray.", "truth_class": "OPPORTUNITY_ESTIMATE", "source": "governed opportunities"}
    if "focus" in text or "today" in text or "best" in text:
        return {"answer": priority_view(snapshot)[0]["title"] if priority_view(snapshot) else "No governed priority recorded.", "truth_class": priority_view(snapshot)[0]["truth_class"] if priority_view(snapshot) else "UNKNOWN", "source": "Revenue Truth Layer"}
    return {"answer": "Revenue Hub distinguishes actual, test, synthetic, pipeline, opportunity estimate, and unknown values.", "truth_class": "UNKNOWN", "source": "Revenue Truth Layer"}
