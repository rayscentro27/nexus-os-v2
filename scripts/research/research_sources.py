#!/usr/bin/env python3
"""Manage designated incremental Research monitors in the canonical Alpha registry."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from research.ray_source_intake import _canonical_url, add_designated_source, source_status, set_source_state
from research.youtube_channel_registry import supabase_channels, upsert_supabase
from nexus_agent_platform.governed import persistence
from research.proactive_research_memory import status_snapshot


def _safe(row):
    """Omit internal credentials and scrub URL userinfo/secret query values."""
    import urllib.parse
    clean = dict(row)
    for key in ("url", "source_url", "canonical_url"):
        value = clean.get(key)
        if not value: continue
        parsed = urllib.parse.urlsplit(str(value))
        query = [(k, "[REDACTED]" if any(t in k.lower() for t in ("token", "key", "secret", "auth")) else v)
                 for k, v in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)]
        host = parsed.hostname or ""
        if parsed.port: host += f":{parsed.port}"
        clean[key] = urllib.parse.urlunsplit((parsed.scheme, host, parsed.path,
                                               urllib.parse.urlencode(query), ""))
    for key in tuple(clean):
        if any(word in key.lower() for word in ("credential", "secret", "api_key", "access_token")):
            clean.pop(key, None)
    return clean


def _all_latest_rows() -> list[dict]:
    latest = {}
    for row in reversed(persistence.read_records("alpha_source_registry")):
        sid = str(row.get("source_id") or "")
        if sid:
            latest[sid] = row
    return list(latest.values())


def _latest_rows() -> list[dict]:
    return [row for row in _all_latest_rows() if row.get("monitor_mode") == "NEW_CONTENT_ONLY" and
            row.get("processing_intent") == "CONTINUOUS"]


def import_manifest(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("sources", []) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("manifest_must_be_a_list_or_contain_sources")
    added, duplicates = [], []
    known = {_canonical_url(str(row.get("canonical_url") or row.get("source_url") or row.get("url")))
             for row in _all_latest_rows() if row.get("canonical_url") or row.get("source_url") or row.get("url")}
    for item in rows:
        result = add_designated_source(
            name=str(item.get("name", "")), source_type=str(item.get("type") or item.get("source_type") or "other"),
            url=str(item["url"]), category=str(item.get("category", "GENERAL")),
            priority=int(item.get("priority", 50)), monitor_mode=str(item.get("monitor_mode", "NEW_CONTENT_ONLY")),
            cadence=str(item.get("cadence", "WEEKLY")), target_department=str(item.get("target_department", "RESEARCH")),
            enabled=bool(item.get("enabled", True)), notes=str(item.get("notes", "")))
        (duplicates if result["canonical_url"] in known else added).append(result)
        known.add(result["canonical_url"])
    youtube_rows = [row for row in added + duplicates if str(row.get("source_type", "")).upper() == "YOUTUBE_CHANNEL"]
    if youtube_rows and not upsert_supabase(youtube_rows).get("ok"):
        raise ValueError("supabase_registry_persistence_failed")
    return {"added": added, "duplicates": duplicates, "historical_ingestion": "NOT_REQUESTED"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="op", required=True)
    sub.add_parser("list")
    sub.add_parser("status")
    add = sub.add_parser("add")
    for name in ("name", "type", "url"):
        add.add_argument("--" + name, required=True)
    add.add_argument("--category", default="GENERAL")
    add.add_argument("--priority", type=int, default=50)
    add.add_argument("--monitor-mode", default="NEW_CONTENT_ONLY")
    add.add_argument("--cadence", default="WEEKLY")
    add.add_argument("--target-department", default="RESEARCH")
    add.add_argument("--notes", default="")
    add.add_argument("--external-channel-id", default="")
    add.add_argument("--triage-mode", choices=("AUTO_RESEARCH", "TRIAGE_ONLY", "IGNORE_LOW_RELEVANCE"), default="TRIAGE_ONLY")
    for op in ("disable", "enable", "show"):
        cmd = sub.add_parser(op); cmd.add_argument("source_id")
    update = sub.add_parser("update"); update.add_argument("source_id")
    update.add_argument("--priority", type=int); update.add_argument("--category")
    update.add_argument("--cadence"); update.add_argument("--target-department")
    imp = sub.add_parser("import"); imp.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.op == "list": result = supabase_channels() or _latest_rows()
        elif args.op == "status": result = status_snapshot()
        elif args.op == "add":
            result = add_designated_source(name=args.name, source_type=args.type, url=args.url,
                category=args.category, priority=args.priority, monitor_mode=args.monitor_mode,
                cadence=args.cadence, target_department=args.target_department, notes=args.notes,
                external_channel_id=args.external_channel_id or None, triage_mode=args.triage_mode)
            if args.type.strip().lower() == "youtube_channel":
                persisted = upsert_supabase([result])
                result["supabase_persisted"] = persisted["ok"]
                if not persisted["ok"]: raise ValueError("supabase_registry_persistence_failed")
        elif args.op == "import": result = import_manifest(args.manifest)
        elif args.op == "show": result = source_status(args.source_id)
        elif args.op in {"enable", "disable"}:
            result = set_source_state(args.source_id, "ACTIVE" if args.op == "enable" else "PAUSED")
            if result.get("source_type") == "YOUTUBE_CHANNEL" and not upsert_supabase([result]).get("ok"):
                raise ValueError("supabase_registry_persistence_failed")
        elif args.op == "update":
            current = source_status(args.source_id)
            if not current: raise ValueError("source_not_found")
            result = {**current, "priority": args.priority if args.priority is not None else current.get("priority"),
                      "category": args.category or current.get("category"), "cadence": args.cadence or current.get("cadence"),
                      "target_department": args.target_department or current.get("target_department")}
            persistence.append_record("alpha_source_registry", result)
            if result.get("source_type") == "YOUTUBE_CHANNEL" and not upsert_supabase([result]).get("ok"):
                raise ValueError("supabase_registry_persistence_failed")
        if isinstance(result, list): result = [_safe(row) for row in result]
        elif isinstance(result, dict): result = _safe(result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
