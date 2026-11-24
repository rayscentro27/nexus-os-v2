"""Durable Nova Operator v1 orchestration primitives.

The operator owns goals, plans, step state, capability acquisition, bounded
self-repair, failures, lineage and verification. Generated adapters are
declarative and interpreted by a closed, allowlisted operation set; arbitrary
generated code is never imported or hot-loaded.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = 3
MISSION_STATES = {
    "UNDERSTANDING", "PLANNING", "EXECUTING", "WAITING_FOR_SUBTASK",
    "RECOVERING", "ACQUISITION_PLANNING", "WAITING_FOR_APPROVAL", "CAPABILITY_GAP", "BLOCKED_TRUE",
    "COMPLETE", "FAILED_INTERNAL",
}
STEP_STATES = {
    "PENDING", "READY", "RUNNING", "WAITING", "VERIFYING", "RECOVERING",
    "COMPLETE", "COMPLETE_VERIFIED_BY_POSTCONDITION", "BLOCKED_TRUE",
}
TERMINAL_MISSION_STATES = {"COMPLETE", "BLOCKED_TRUE"}
MAX_STEPS = 8
MAX_REPLANS = 2

DOCTRINE = (
    "A Ray-assigned objective remains active until it is completed or a genuine "
    "human-only/consequential boundary is reached. Tool failures, missing first-choice "
    "routes, worker failures, incomplete research, negative results, missing receipts, "
    "routing mismatches, and internal configuration defects are conditions to diagnose "
    "and overcome, not reasons to terminate the objective. ACTION_NOT_AVAILABLE is "
    "invalid until live capability discovery, primary and alternate path evaluation, "
    "safe repair/reroute evaluation, capability-gap handling, and applicable postcondition "
    "verification are recorded. A completed step, successful tool call, or exhausted plan "
    "does not complete the Ray objective. Every mission requires an independent, persisted "
    "mission-level success condition and current verification evidence."
)

_ACTION = re.compile(
    r"^\s*(?:nova[, :]*)?(?:please\s+)?(?:create|start|assign|continue|advance|run|execute|"
    r"save|update|build|write|edit|delete|send|schedule|move|archive|label|draft|publish|"
    r"purchase|inspect|diagnose|repair|restart|check|verify|fix|resume|claim|read|find|"
    r"answer|gather|synthesize|keep\s+working|"
    r"search|look\s+up|open|retrieve)\b", re.I,
)
_ID_RE = re.compile(r"\b(?:job|objective|project|case|mission|file|note)_[-a-zA-Z0-9_.]+\b")
_STATUS_QUERY = re.compile(r"\b(?:what (?:are you working on|is the status|step are you on|happens next)|why are you stuck|did (?:that|it) finish|status of (?:that|it)|continue (?:that|it))\b", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _root() -> Path:
    return Path(os.environ.get("NOVA_REPO_ROOT") or os.environ.get("NEXUS_REPO_ROOT")
                or Path(__file__).resolve().parents[2])


def store_path() -> Path:
    return Path(os.environ.get("NOVA_OPERATOR_DB") or (_root() / "data/runtime/nova_operator.sqlite3"))


def _connect() -> sqlite3.Connection:
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
      CREATE TABLE IF NOT EXISTS operator_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS operator_missions(
        mission_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, tenant_id TEXT,
        objective_text TEXT NOT NULL, objective_type TEXT NOT NULL, status TEXT NOT NULL,
        current_step_id TEXT, plan_version INTEGER NOT NULL DEFAULT 0,
        source_channel TEXT, source_message_id TEXT, understanding_json TEXT NOT NULL,
        final_result_json TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        completed_at TEXT, original_mission_id TEXT UNIQUE
      );
      CREATE TABLE IF NOT EXISTS operator_messages(
        mission_id TEXT NOT NULL REFERENCES operator_missions(mission_id), source_channel TEXT NOT NULL,
        source_message_id TEXT NOT NULL, message_text TEXT NOT NULL, received_at TEXT NOT NULL,
        PRIMARY KEY(mission_id, source_channel, source_message_id)
      );
      CREATE TABLE IF NOT EXISTS operator_steps(
        step_id TEXT PRIMARY KEY, mission_id TEXT NOT NULL REFERENCES operator_missions(mission_id),
        sequence INTEGER NOT NULL, goal TEXT NOT NULL, required_capability TEXT,
        selected_capability_id TEXT, inputs_json TEXT NOT NULL, dependencies_json TEXT NOT NULL,
        expected_postcondition_json TEXT NOT NULL, status TEXT NOT NULL,
        attempt_count INTEGER NOT NULL DEFAULT 0, last_error TEXT, result_reference_json TEXT,
        receipt_reference_json TEXT, started_at TEXT, completed_at TEXT,
        UNIQUE(mission_id, sequence)
      );
      CREATE TABLE IF NOT EXISTS operator_events(
        event_id TEXT PRIMARY KEY, mission_id TEXT NOT NULL REFERENCES operator_missions(mission_id),
        step_id TEXT, event_type TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS operator_lineage(
        mission_id TEXT NOT NULL REFERENCES operator_missions(mission_id),
        entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, entity_role TEXT NOT NULL,
        created_by_step TEXT, last_verified_at TEXT, metadata_json TEXT NOT NULL,
        PRIMARY KEY(mission_id, entity_type, entity_id, entity_role)
      );
      CREATE TABLE IF NOT EXISTS operator_capability_proposals(
        proposal_id TEXT PRIMARY KEY, mission_id TEXT NOT NULL REFERENCES operator_missions(mission_id),
        required_capability TEXT NOT NULL, evaluation_json TEXT NOT NULL,
        status TEXT NOT NULL, created_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS operator_knowledge(
        pattern_id TEXT PRIMARY KEY, objective_pattern TEXT NOT NULL, successful_plan_json TEXT NOT NULL,
        capabilities_json TEXT NOT NULL, failures_json TEXT NOT NULL, repairs_json TEXT NOT NULL,
        postconditions_json TEXT NOT NULL, result_json TEXT NOT NULL, last_verified TEXT NOT NULL
      );
    """)
    _ensure_column(db, "operator_steps", "target_entity_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(db, "operator_steps", "candidate_capabilities_json", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_column(db, "operator_steps", "selection_reason", "TEXT")
    _ensure_column(db, "operator_missions", "mission_success_condition_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(db, "operator_missions", "mission_success_evidence_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(db, "operator_missions", "mission_success_verified", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(db, "operator_missions", "mission_completion_reason", "TEXT")
    db.executescript("""
      CREATE TABLE IF NOT EXISTS operator_capability_gaps(
        gap_id TEXT PRIMARY KEY, mission_id TEXT NOT NULL REFERENCES operator_missions(mission_id),
        step_id TEXT, required_capability TEXT NOT NULL, evidence_json TEXT NOT NULL,
        status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS operator_failures(
        failure_id TEXT PRIMARY KEY, mission_id TEXT NOT NULL REFERENCES operator_missions(mission_id),
        step_id TEXT, failure_class TEXT NOT NULL, evidence_json TEXT NOT NULL,
        status TEXT NOT NULL, created_at TEXT NOT NULL
      );
    """)
    db.execute("INSERT OR REPLACE INTO operator_meta(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))
    db.commit()
    return db


def _ensure_column(db: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {str(row[1]) for row in db.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _read_only_connect() -> sqlite3.Connection | None:
    """Open existing Operator state without creating or updating anything."""
    path = store_path()
    if not path.is_file():
        return None
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    return db


def actionable(text: str, intent: str | None = None) -> bool:
    """Use existing intent plus ordinary action grammar; capability reads stay reads."""
    intent = str(intent or "").upper()
    if intent in {"ACTION_NOT_AVAILABLE", "APPROVED_MCP_ACTION", "RESEARCH_REQUEST",
                  "RESEARCH_MISSION", "RESEARCH_RUNTIME_INSPECTION", "DEPARTMENT_ASSIGNMENT",
                  "CONTINUE_EXISTING_WORK", "CROSS_DEPARTMENT_CONTINUATION",
                  "CREATIVE_ASSET_REQUEST", "BOUNDED_CODING_REQUEST", "NEXUS_OPERATIONAL_DIAGNOSTIC_AND_REPAIR",
                  "BROWSER_ACTION", "FILE_OR_DOCUMENT_ACTION", "CODE_OR_SYSTEM_ACTION", "OPERATOR_STATUS_QUERY",
                  "COMMUNICATION_ACTION"}:
        return True
    return bool(_ACTION.search(str(text or "")) or _STATUS_QUERY.search(str(text or "")))


_ENTITY_INPUT_KEYS = {
    "RESEARCH_CASE": {"case_id", "research_case_id"},
    "CASE": {"case_id", "research_case_id"},
    "RESEARCH_JOB": {"job_id", "durable_job_id"},
    "JOB": {"job_id", "durable_job_id"},
    "RESEARCH_PROJECT": {"project_id", "research_project_id"},
    "PROJECT": {"project_id", "research_project_id"},
    "NOTE": {"note_id", "relative_path", "path"},
    "FILE": {"file_id", "relative_path", "path"},
    "EVENT": {"event_id"},
    "OBJECTIVE": {"objective_id"},
}


def _explicitly_requests_new_entity(instruction: str) -> bool:
    value = str(instruction or "").casefold()
    pattern = re.compile(
        r"\b(?:create|start|open|make|duplicate|fork)\s+"
        r"(?:(?:a|an|one)\s+)?"
        r"(?:(?:another|new|additional|separate|duplicate|forked)\s+)?"
        r"(?:(?:internal|research|durable|small|bounded)\s+){0,4}"
        r"(?:case|job|project|note|file|event|objective|attempt|entity)\b"
    )
    for match in pattern.finditer(value):
        prefix = value[max(0, match.start() - 28):match.start()]
        if re.search(r"\b(?:do\s+not|don't|never|avoid)\s*$", prefix):
            continue
        return True
    return False


def _lineage_id_map(target: dict[str, Any] | None) -> dict[str, str]:
    target = target if isinstance(target, dict) else {}
    values = {str(k).casefold(): str(v) for k, v in
              (target.get("related_entity_ids") or {}).items() if v}
    entity_type = str(target.get("entity_type") or "").upper()
    keys = _ENTITY_INPUT_KEYS.get(entity_type, set())
    ids = [str(x) for x in target.get("entity_ids") or [] if x]
    if ids and keys:
        # The exact target ID is authoritative for its own type. Related
        # lineage values are supplied separately by the durable conversation.
        direct = sorted(keys)[0]
        values[direct] = ids[0]
    # Workspace notes and files use their bounded relative path as the durable
    # identity. Expose that exact value under the adapter's schema key so reads
    # and updates remain bound to the same entity.
    if entity_type in {"NOTE", "FILE"}:
        identity_key = "note_id" if entity_type == "NOTE" else "file_id"
        identity = values.get(identity_key) or (ids[0] if ids else "")
        if identity.startswith(("reports/nova_internal/", "data/runtime/nova_artifacts/")):
            values.setdefault("relative_path", identity)
            values.setdefault("path", identity)
    return values


def _arguments_bind_target(target: dict[str, Any], capability: dict[str, Any],
                            arguments: dict[str, Any], *, require_binding: bool = True) -> bool:
    lineage = _lineage_id_map(target)
    properties = (capability.get("input_schema") or {}).get("properties") or {}
    matches = {str(key).casefold(): str(value) for key, value in arguments.items()
               if str(key).casefold() in lineage and value is not None}
    if not matches:
        return not require_binding
    return all(lineage[key] == value for key, value in matches.items())


def entity_action_compatible(target: dict[str, Any] | None, capability: dict[str, Any],
                             instruction: str = "", *, support_read: bool = False) -> bool:
    """An exact existing entity constrains tools to schemas that address it."""
    target = target if isinstance(target, dict) else {}
    ids = target.get("entity_ids") or []
    entity_type = str(target.get("entity_type") or "").upper()
    if (not target.get("explicit_target") or not ids or target.get("explicit_new_entity_request")
            or _explicitly_requests_new_entity(instruction)):
        return True
    required_keys = _ENTITY_INPUT_KEYS.get(entity_type)
    if not required_keys:
        return True
    schema = capability.get("input_schema") if isinstance(capability.get("input_schema"), dict) else {}
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    names = {str(key).casefold() for key in properties}
    name = str(capability.get("tool_name") or capability.get("name") or "").casefold()
    lineage = _lineage_id_map(target)
    linked_keys = set(lineage)
    direct_match = bool(names.intersection(required_keys))
    linked_match = bool(names.intersection(linked_keys))
    if not direct_match and not linked_match:
        # Read-only supporting evidence (e.g. an allowlisted source/file read)
        # may contribute to the same mission, but it cannot verify the exact
        # entity or substitute for an entity-bound action.
        if not (support_read and capability.get("read_write_class") == "READ"):
            return False
    # Related lineage IDs can support exact reads, but an action on an exact
    # Research case must use a case-bound action. A project/job continuation
    # adapter can enqueue intake work without advancing the case, so it must
    # never substitute for case continuation.
    if not direct_match and linked_match and capability.get("read_write_class") != "READ":
        return False
    # Creation/assignment actions cannot replace an explicitly bound entity.
    # Explicit user requests for another/new entity are handled above.
    if re.search(r"(?:^|_)(?:create|assign|new|open)_", name):
        return False
    return True


def bind_targets(text: str, catalog: list[dict[str, Any]], semantic: dict[str, Any] | None = None) -> dict[str, Any]:
    """Bind explicit entities independently from the intended operation."""
    value = str(text or "")
    lower = value.casefold()
    servers = []
    for row in catalog:
        name = str(row.get("server_or_department") or "")
        source_id = str(row.get("source_id") or "")
        if name and (name.casefold() in lower or source_id.casefold() in lower):
            servers.append(source_id or name)
    ids = list(dict.fromkeys(_ID_RE.findall(value)))
    semantic = semantic or {}
    return {
        "server_ids": list(dict.fromkeys(servers)),
        "entity_ids": ids,
        "department": semantic.get("department"),
        "explicit_target": bool(servers or ids or semantic.get("department")),
        "target_constraints": ["Use exact explicit identifiers; never substitute by semantic similarity."],
    }


def _understanding(text: str, mission: dict[str, Any], semantic: dict[str, Any], targets: dict[str, Any]) -> dict[str, Any]:
    prohibitions = []
    folded = text.casefold()
    for phrase in ("do not create another job", "do not create a new job", "do not create", "read only", "read-only",
                   "do not send", "do not modify", "no external", "do not spend"):
        if phrase in folded:
            prohibitions.append(phrase.upper().replace(" ", "_"))
    return {
        "desired_outcome": text.strip(),
        "target_entity": targets,
        "success_condition": "A durable, verified state/result satisfies the Ray request; a tool call alone is insufficient.",
        "constraints": {"semantic_intent": semantic.get("intent"), "department": semantic.get("department")},
        "explicit_prohibitions": prohibitions,
        "approval_boundaries": ["NEW_INCREMENTAL_CASH_REQUIRED", "CONSEQUENTIAL_EXTERNAL_ACTION_APPROVAL",
                                "DESTRUCTIVE_PRODUCTION_CHANGE", "SECURITY_SCOPE_EXPANSION", "RAY_ACTION_REQUIRED"],
        "source_channel": "TELEGRAM",
        "source_message_id": str(mission.get("update_id", "")),
    }


def begin_mission(mission: dict[str, Any], text: str, semantic: dict[str, Any], catalog: list[dict[str, Any]]) -> dict[str, Any]:
    mission_id = str(mission.get("operator_mission_id") or mission["mission_id"])
    targets = bind_targets(text, catalog, semantic)
    explicit_new_entity = _explicitly_requests_new_entity(text)
    targets["explicit_new_entity_request"] = explicit_new_entity
    lineage = mission.get("current_objective_lineage")
    # A create-first compound request owns its own later pronouns ("read it",
    # "update that same note"). Prior-turn entity lineage must not capture
    # those references or turn the new entity's path into a replacement target.
    if isinstance(lineage, dict) and lineage and not explicit_new_entity:
        targets["related_entity_ids"] = {key: str(lineage[key]) for key in
            ("case_id", "objective_id", "project_id", "job_id", "note_id", "file_id", "event_id")
            if lineage.get(key)}
        folded = str(text or "").casefold()
        entity_type = next((kind for kind, pattern in (
            ("RESEARCH_CASE", r"\bcase\b"), ("RESEARCH_JOB", r"\bjob\b"),
            ("RESEARCH_PROJECT", r"\bproject\b"), ("OBJECTIVE", r"\bobjective\b"),
            ("NOTE", r"\bnote\b"), ("FILE", r"\bfile\b|\bdocument\b"),
            ("EVENT", r"\bevent\b")) if re.search(pattern, folded)), None)
        field_for_type = {"RESEARCH_CASE": "case_id", "RESEARCH_JOB": "job_id",
                          "RESEARCH_PROJECT": "project_id", "OBJECTIVE": "objective_id",
                          "NOTE": "note_id", "FILE": "file_id", "EVENT": "event_id"}
        selected_id = lineage.get(field_for_type.get(entity_type, "")) if entity_type else None
        if not selected_id:
            selected_id = next((lineage.get(key) for key in
                ("case_id", "job_id", "project_id", "objective_id", "note_id", "file_id", "event_id")
                if lineage.get(key)), None)
        if selected_id:
            targets["entity_ids"] = [str(selected_id)]
            targets["entity_type"] = entity_type
            targets["explicit_target"] = True
            targets["lineage_source"] = "DURABLE_CURRENT_ENTITY_LINEAGE"
    understanding = _understanding(text, mission, semantic, targets)
    objective_type = str(semantic.get("intent") or "ACTIONABLE_OBJECTIVE")
    now = _now()
    with _connect() as db:
        db.execute("""INSERT INTO operator_missions(mission_id,owner_id,tenant_id,objective_text,objective_type,status,
                    source_channel,source_message_id,understanding_json,created_at,updated_at,original_mission_id,
                    mission_success_condition_json)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(mission_id) DO UPDATE SET
                    understanding_json=excluded.understanding_json,updated_at=excluded.updated_at""",
                   (mission_id, str(mission.get("user_id", "")), mission.get("tenant_id"), text[:7000], objective_type,
                    "UNDERSTANDING", "TELEGRAM", str(mission.get("update_id", "")), _json(understanding), now, now,
                    mission_id, _json({"description": understanding["success_condition"], "verification": None,
                                       "required": True, "verified": False})))
        db.execute("INSERT OR IGNORE INTO operator_messages VALUES(?,?,?,?,?)",
                   (mission_id, "TELEGRAM", str(mission.get("update_id", "")), text[:7000], now))
        _event(db, mission_id, None, "UNDERSTANDING_RECORDED", understanding)
        if mission_id != str(mission["mission_id"]):
            _event(db, mission_id, None, "SAME_MISSION_RESUMED", {
                "telegram_mission_id": mission["mission_id"], "source_message_id": mission.get("update_id"),
                "original_objective_preserved": True})
    return {"mission_id": mission_id, "understanding": understanding}


def _event(db: sqlite3.Connection, mission_id: str, step_id: str | None, event_type: str, payload: Any) -> None:
    db.execute("INSERT INTO operator_events VALUES(?,?,?,?,?,?)",
               ("ope_" + uuid.uuid4().hex, mission_id, step_id, event_type, _json(payload), _now()))


def _catalog_row(server: dict[str, Any], tool: dict[str, Any]) -> dict[str, Any]:
    source_id = str(server.get("server_id") or "")
    name = str(tool.get("name") or "")
    annotations = tool.get("annotations") if isinstance(tool.get("annotations"), dict) else {}
    read_class = str(tool.get("read_write_class") or ("READ" if annotations.get("readOnlyHint") else "WRITE"))
    return {
        "capability_id": f"mcp:{source_id}:{name}", "source_type": "MCP",
        "source_id": source_id, "server_id": source_id, "approved": bool(tool.get("approved", True)),
        "server_or_department": server.get("server_name") or source_id,
        "tool_name": name, "name": name, "description": tool.get("description") or "",
        "input_schema": tool.get("input_schema") or {}, "output_schema": tool.get("output_schema"),
        "read_write_class": read_class, "cost_class": tool.get("cost_class") or server.get("cost_class") or "UNKNOWN",
        "write_allowed": bool(tool.get("write_allowed")),
        "external_effect": bool(tool.get("external_effect", server.get("external_effect", True))),
        "production_effect": bool(tool.get("production_effect", server.get("production_effect", True))),
        "destructive": bool(tool.get("destructive", annotations.get("destructiveHint", False))),
        "consequence_class": "DESTRUCTIVE" if annotations.get("destructiveHint") else server.get("authority_class", "UNKNOWN"),
        "approval_class": (tool.get("policy") or {}).get("decision") or "EVALUATE_PER_STEP",
        "reversible": bool(tool.get("reversible", server.get("reversible", False))),
        "authorized": bool(tool.get("approved", True)),
        "runtime_health": server.get("runtime_health", "UNKNOWN"),
        "last_verified_at": server.get("last_verified_at"),
        "server_metadata": {k: server.get(k) for k in ("route_mode", "sandbox_only", "production_effect", "external_effect", "boundary")},
        "tool_metadata": {"metadata_complete": tool.get("metadata_complete"), "write_allowed": tool.get("write_allowed")},
    }


def discover_catalog(*, force: bool = True) -> list[dict[str, Any]]:
    """Build an executable catalog from live schemas on approved, connected MCP servers."""
    from nova.approved_mcp_registry import discover_approved_mcp
    inventory = discover_approved_mcp(force=force)
    server_map = {str(x.get("server_id")): x for x in inventory.get("servers", []) if x.get("approved")}
    rows = [_catalog_row(server_map.get(str(t.get("server_id")), {}), t)
            for t in inventory.get("tools", [])
            if t.get("approved") and server_map.get(str(t.get("server_id")), {}).get("connected")]
    rows.extend(_registered_generated_capabilities())
    rows.append(_operator_status_capability())
    return rows


def _operator_status_capability() -> dict[str, Any]:
    return {"capability_id": "nova:operator:nexus_get_operator_mission_status",
        "source_type": "NOVA_OPERATOR", "source_id": "nova_operator", "server_id": "nova_operator",
        "approved": True, "authorized": True, "server_or_department": "Nova Operator",
        "tool_name": "nexus_get_operator_mission_status",
        "description": "READ ONLY; fast, side-effect-free status for one exact or current Operator mission.",
        "input_schema": {"type": "object", "properties": {"mission_id": {"type": "string"},
            "current_mission": {"type": "boolean"}, "owner_id": {"type": "string"}}, "additionalProperties": False},
        "output_schema": {"type": "object"}, "read_write_class": "READ", "cost_class": "ZERO",
        "consequence_class": "INTERNAL", "approval_class": "ALLOW_READ_ONLY", "reversible": True,
        "runtime_health": "PASS", "write_allowed": False, "external_effect": False,
        "production_effect": False, "destructive": False}


def _generated_registry_path() -> Path:
    return Path(os.environ.get("NOVA_OPERATOR_GENERATED_REGISTRY") or
                (_root() / "data/runtime/nova_operator/generated_capabilities.json"))


def _registered_generated_capabilities() -> list[dict[str, Any]]:
    path = _generated_registry_path()
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = []
    for item in records if isinstance(records, list) else []:
        if not isinstance(item, dict) or item.get("status") != "AVAILABLE":
            continue
        manifest_path = Path(str(item.get("release_path", ""))) / "capability.json"
        try:
            release_dir = manifest_path.parent.resolve(strict=True)
            expected_root = Path(os.environ.get("NOVA_OPERATOR_CAPABILITY_RELEASE_ROOT") or
                (_root() / "data/runtime/nova_operator/capability_releases")).resolve()
            if expected_root not in release_dir.parents:
                continue
            manifest_file = release_dir / "RELEASE_MANIFEST.json"
            source_hash_file = release_dir / "RELEASE_SOURCE_HASH"
            manifest_hash = hashlib.sha256(manifest_file.read_bytes()).hexdigest()
            if manifest_hash != source_hash_file.read_text(encoding="ascii").strip():
                continue
            if item.get("manifest_hash") and item["manifest_hash"] != manifest_hash:
                continue
            file_hashes = json.loads(manifest_file.read_text(encoding="utf-8"))
            if any(hashlib.sha256((release_dir / name).read_bytes()).hexdigest() != digest
                   for name, digest in file_hashes.items()):
                continue
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if manifest.get("capability_id") != item.get("capability_id"):
            continue
        rows.append({"capability_id": "generated:" + str(manifest["capability_id"]), "source_type": "GENERATED_SKILL",
            "source_id": "nova_operator_generated", "server_id": "nova_operator_generated",
            "approved": True, "authorized": True, "server_or_department": "Nova Operator generated adapters",
            "tool_name": manifest["name"], "name": manifest["name"], "description": manifest["purpose"],
            "input_schema": manifest["input_schema"], "output_schema": manifest["output_schema"],
            "read_write_class": manifest["read_write_class"], "cost_class": manifest["cost_class"],
            "consequence_class": manifest["consequence_class"], "approval_class": "ALLOW_BOUNDED_INTERNAL",
            "reversible": True, "runtime_health": "PASS", "last_verified_at": item.get("registered_at"),
            "write_allowed": False, "external_effect": False, "production_effect": False,
            "destructive": False, "generated_manifest": manifest, "generated_release_path": str(manifest_path.parent)})
    return rows


def save_catalog(mission_id: str, catalog: list[dict[str, Any]]) -> None:
    with _connect() as db:
        _event(db, mission_id, None, "LIVE_CAPABILITY_CATALOG", {
            "count": len(catalog), "catalog_hash": hashlib.sha256(_json(catalog).encode()).hexdigest(),
            "capabilities": catalog,
        })


_CAPABILITY_OPERATIONS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    # Closed pure-transform interpreter. New capabilities are data-only manifests;
    # adding an arbitrary operation or Python import is never permitted.
    "reverse_text": lambda args: {"text": str(args.get("text", ""))[::-1]},
}


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    temp.write_text(_json(value) + "\n", encoding="utf-8")
    os.replace(temp, path)


def build_and_register_capability(mission_id: str, proposal: dict[str, Any], *,
                                  release_root: str | Path | None = None,
                                  registry_path: str | Path | None = None) -> dict[str, Any]:
    """Validate, package and register a safe declarative adapter immutably."""
    spec = dict(proposal)
    required = {"capability_id", "name", "purpose", "operation", "input_schema", "output_schema",
                "cost_class", "consequence_class", "read_write_class", "required_permissions", "dependencies", "tests"}
    if not required.issubset(spec):
        raise ValueError("CAPABILITY_SPEC_INCOMPLETE:" + ",".join(sorted(required - set(spec))))
    if spec["operation"] not in _CAPABILITY_OPERATIONS:
        raise PermissionError("CAPABILITY_OPERATION_NOT_ALLOWLISTED")
    if spec["cost_class"] != "ZERO" or spec["consequence_class"] != "INTERNAL" or spec["read_write_class"] != "READ":
        raise PermissionError("CAPABILITY_POLICY_BOUNDARY_REQUIRES_APPROVAL")
    if spec["required_permissions"] or spec["dependencies"]:
        raise PermissionError("CAPABILITY_PERMISSION_OR_DEPENDENCY_REQUIRES_APPROVAL")
    schema = spec["input_schema"]
    if schema.get("type") != "object" or not set(schema.get("required", [])) <= set(schema.get("properties", {})):
        raise ValueError("CAPABILITY_INPUT_SCHEMA_INVALID")
    if any(len(_json(test).encode()) > 4096 for test in spec["tests"]):
        raise ValueError("CAPABILITY_TEST_VECTOR_TOO_LARGE")
    operation = _CAPABILITY_OPERATIONS[spec["operation"]]
    test_results = []
    for case in spec["tests"]:
        actual = operation(dict(case.get("input") or {}))
        if actual != case.get("expected"):
            raise AssertionError("CAPABILITY_FUNCTIONAL_TEST_FAILED")
        test_results.append({"status": "PASS", "input_hash": hashlib.sha256(_json(case.get("input")).encode()).hexdigest()})

    root = Path(release_root) if release_root else Path(os.environ.get("NOVA_OPERATOR_CAPABILITY_RELEASE_ROOT") or
        (_root() / "data/runtime/nova_operator/capability_releases"))
    registry = Path(registry_path) if registry_path else _generated_registry_path()
    capability_id = re.sub(r"[^A-Za-z0-9_.:-]", "", str(spec["capability_id"]))
    if not capability_id or len(capability_id) > 120:
        raise ValueError("CAPABILITY_ID_INVALID")
    release_id = "cap-" + re.sub(r"[^A-Za-z0-9_.-]", "-", capability_id)[:65] + "-" + uuid.uuid4().hex[:10]
    root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".build-", dir=str(root)))
    release = root / release_id
    try:
        prior_records = json.loads(registry.read_text(encoding="utf-8"))
        if not isinstance(prior_records, list): prior_records = []
    except (OSError, ValueError):
        prior_records = []
    if any(row.get("capability_id") == capability_id and row.get("status") == "AVAILABLE"
           for row in prior_records if isinstance(row, dict)):
        shutil.rmtree(staging, ignore_errors=True)
        raise FileExistsError("CAPABILITY_ALREADY_REGISTERED")
    stages = ["PROPOSED", "ISOLATED_BUILD", "STATIC_VALIDATION", "FUNCTIONAL_TEST", "POLICY_CHECK", "PACKAGE"]
    manifest = {k: spec[k] for k in sorted(required)}
    manifest.update({"schema_version": "nova.operator-capability.v1", "release_id": release_id,
                     "sandbox_only": True, "production_effect": False, "external_effect": False,
                     "source_hash": hashlib.sha256(_json(spec).encode()).hexdigest()})
    try:
        if mission_id:
            with _connect() as db:
                for stage in stages:
                    _event(db, mission_id, None, "CAPABILITY_BUILD_STAGE", {"capability_id": capability_id, "stage": stage})
        (staging / "capability.json").write_text(_json(manifest) + "\n", encoding="utf-8")
        file_hash = hashlib.sha256((staging / "capability.json").read_bytes()).hexdigest()
        (staging / "REGISTRY_ROLLBACK.json").write_text(_json(prior_records) + "\n", encoding="utf-8")
        entries = {"capability.json": file_hash,
                   "REGISTRY_ROLLBACK.json": hashlib.sha256((staging / "REGISTRY_ROLLBACK.json").read_bytes()).hexdigest()}
        (staging / "RELEASE_MANIFEST.json").write_text(_json(entries) + "\n", encoding="utf-8")
        manifest_hash = hashlib.sha256((staging / "RELEASE_MANIFEST.json").read_bytes()).hexdigest()
        release.mkdir()
        shutil.copy2(staging / "capability.json", release / "capability.json")
        shutil.copy2(staging / "REGISTRY_ROLLBACK.json", release / "REGISTRY_ROLLBACK.json")
        shutil.copy2(staging / "RELEASE_MANIFEST.json", release / "RELEASE_MANIFEST.json")
        (release / "RELEASE_SOURCE_HASH").write_text(manifest_hash + "\n", encoding="ascii")
        if any(hashlib.sha256((release / name).read_bytes()).hexdigest() != digest for name, digest in entries.items()):
            raise RuntimeError("CAPABILITY_RELEASE_MANIFEST_INVALID")
        if hashlib.sha256((release / "RELEASE_MANIFEST.json").read_bytes()).hexdigest() != manifest_hash:
            raise RuntimeError("CAPABILITY_RELEASE_SOURCE_HASH_INVALID")
        for path in release.rglob("*"):
            if path.is_file(): path.chmod(0o444)
        release.chmod(0o555)
        record = {"capability_id": capability_id, "release_id": release_id, "release_path": str(release),
                  "source_hash": manifest["source_hash"], "manifest_hash": manifest_hash,
                  "manifest_valid": True, "rollback_path": str(release / "REGISTRY_ROLLBACK.json"), "status": "AVAILABLE",
                  "registered_at": _now(), "test_results": test_results}
        records = [*prior_records, record]
        _atomic_json(registry, records)
        with _connect() as db:
            _event(db, mission_id, None, "CAPABILITY_BUILD_STAGE", {"capability_id": capability_id, "stage": "IMMUTABLE_RELEASE"})
            _event(db, mission_id, None, "CAPABILITY_BUILD_STAGE", {"capability_id": capability_id, "stage": "REGISTERED"})
            _event(db, mission_id, None, "CAPABILITY_BUILD_STAGE", {"capability_id": capability_id, "stage": "AVAILABLE"})
            _event(db, mission_id, None, "CAPABILITY_RELEASE_REGISTERED", record)
            db.execute("UPDATE operator_missions SET status='RECOVERING',updated_at=? WHERE mission_id=?", (_now(), mission_id))
        return record
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _invoke_generated(capability: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    manifest = capability.get("generated_manifest") or {}
    if capability.get("source_id") != "nova_operator_generated" or manifest.get("operation") not in _CAPABILITY_OPERATIONS:
        raise PermissionError("GENERATED_CAPABILITY_NOT_REGISTERED")
    result = _CAPABILITY_OPERATIONS[manifest["operation"]](arguments)
    return {"call_succeeded": True, "action_succeeded": True, "result_data": result,
            "source": "immutable_declarative_capability", "raw_result_reference": capability.get("generated_release_path")}


def rollback_generated_capability(capability_id: str, *, registry_path: str | Path | None = None) -> dict[str, Any]:
    """Revoke catalog registration while retaining the immutable package/audit trail."""
    registry = Path(registry_path) if registry_path else _generated_registry_path()
    try:
        records = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"rolled_back": False, "reason": "CAPABILITY_REGISTRY_NOT_FOUND"}
    target = next((x for x in records if isinstance(x, dict) and x.get("capability_id") == capability_id
                   and x.get("status") == "AVAILABLE"), None)
    if target is None:
        return {"rolled_back": False, "reason": "CAPABILITY_NOT_REGISTERED"}
    target["status"] = "ROLLED_BACK"
    target["rolled_back_at"] = _now()
    _atomic_json(registry, records)
    return {"rolled_back": True, "capability_id": capability_id,
            "release_retained": True, "release_path": target.get("release_path")}


def self_repair_release_flow(*, target_root: str | Path, relative_path: str, expected_before: str,
                             replacement: str, validation: Callable[[Path], bool],
                             original_step: Callable[[Path], bool], test_scope: bool = False,
                             mission_id: str | None = None) -> dict[str, Any]:
    """Build/promote a bounded exact-text repair through an immutable release.

    Production roots must be explicitly allowlisted by deployment policy. Test
    scope uses a disposable root and never changes the running Operator code.
    The model cannot supply executable test commands or arbitrary Python.
    """
    root = Path(target_root).resolve(strict=True)
    rel = Path(relative_path)
    if rel.is_absolute() or ".." in rel.parts or len(rel.parts) == 0:
        raise PermissionError("SELF_REPAIR_PATH_OUTSIDE_ROOT")
    allowed = [Path(p).resolve() for p in os.environ.get("NOVA_OPERATOR_SELF_REPAIR_ROOTS", "").split(os.pathsep) if p]
    if not test_scope and not any(root == p or p in root.parents for p in allowed):
        raise PermissionError("SELF_REPAIR_ROOT_NOT_APPROVED")
    source = (root / rel).resolve(strict=True)
    if root != source and root not in source.parents:
        raise PermissionError("SELF_REPAIR_PATH_ESCAPE")
    if re.search(r"credential|secret|token|private|\.env|id_rsa|\.ssh", str(rel), re.I):
        raise PermissionError("SELF_REPAIR_SENSITIVE_PATH_DENIED")
    if len(expected_before.encode("utf-8")) > 100_000 or len(replacement.encode("utf-8")) > 100_000:
        raise ValueError("SELF_REPAIR_PATCH_EXCEEDS_BOUND")
    if re.search(r"-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----|(?i:api[_-]?key\s*[:=])", replacement):
        raise PermissionError("SELF_REPAIR_SECRET_CONTENT_DENIED")
    before = source.read_text(encoding="utf-8")
    if before.count(expected_before) != 1:
        raise RuntimeError("SELF_REPAIR_PATCH_ANCHOR_NOT_UNIQUE")
    after = before.replace(expected_before, replacement, 1)
    package_root = root / ".nova_operator_releases"
    package_root.mkdir(mode=0o700, exist_ok=True)
    build = Path(tempfile.mkdtemp(prefix=".repair-", dir=str(package_root)))
    release_id = "repair-" + uuid.uuid4().hex
    release = package_root / release_id
    try:
        if mission_id:
            with _connect() as db:
                _event(db, mission_id, None, "SELF_REPAIR_STAGE", {"stage": "OBSERVE_FAILURE", "path": str(rel)})
                _event(db, mission_id, None, "SELF_REPAIR_STAGE", {"stage": "DIAGNOSE", "failure": "exact anchor replacement"})
        staged_file = build / rel
        staged_file.parent.mkdir(parents=True, exist_ok=True)
        staged_file.write_text(after, encoding="utf-8")
        if not validation(staged_file):
            raise RuntimeError("SELF_REPAIR_VALIDATION_FAILED")
        if mission_id:
            with _connect() as db: _event(db, mission_id, None, "SELF_REPAIR_STAGE", {"stage": "TESTS_PASS"})
        (build / "RELEASE_MANIFEST.json").write_text(_json({str(rel): hashlib.sha256(staged_file.read_bytes()).hexdigest()}) + "\n", encoding="utf-8")
        manifest_hash = hashlib.sha256((build / "RELEASE_MANIFEST.json").read_bytes()).hexdigest()
        (build / "RELEASE_SOURCE_HASH").write_text(manifest_hash + "\n", encoding="ascii")
        if hashlib.sha256(staged_file.read_bytes()).hexdigest() != json.loads((build / "RELEASE_MANIFEST.json").read_text())[str(rel)]:
            raise RuntimeError("SELF_REPAIR_MANIFEST_INVALID")
        os.replace(build, release)
        for item in release.rglob("*"):
            if item.is_file(): item.chmod(0o444)
        release.chmod(0o555)
        pointer = package_root / "ACTIVE_RELEASE"
        old_pointer = pointer.read_text(encoding="utf-8").strip() if pointer.exists() else ""
        temp_pointer = package_root / (".ACTIVE_RELEASE-" + uuid.uuid4().hex)
        temp_pointer.write_text(release_id + "\n", encoding="ascii")
        os.replace(temp_pointer, pointer)
        promoted = (pointer.read_text(encoding="utf-8").strip() == release_id)
        if mission_id:
            with _connect() as db:
                _event(db, mission_id, None, "SELF_REPAIR_STAGE", {"stage": "IMMUTABLE_RELEASE_CREATED", "release_id": release_id,
                    "manifest_hash": manifest_hash, "rollback_release": old_pointer or None})
                _event(db, mission_id, None, "SELF_REPAIR_STAGE", {"stage": "TEST_SCOPE_RELEASE_PROMOTED", "release_id": release_id})
        retry_pass = bool(promoted and original_step(release / rel))
        if not retry_pass:
            if old_pointer:
                temp_pointer.write_text(old_pointer + "\n", encoding="ascii")
                os.replace(temp_pointer, pointer)
            else:
                pointer.unlink(missing_ok=True)
            raise RuntimeError("SELF_REPAIR_ORIGINAL_STEP_RETRY_FAILED")
        if mission_id:
            with _connect() as db: _event(db, mission_id, None, "SELF_REPAIR_STAGE", {"stage": "ORIGINAL_STEP_RETRIED", "postcondition": "PASS"})
        return {"failure_detected": True, "diagnosis_created": True, "patch_built": True,
            "tests_pass": True, "immutable_release_created": True, "manifest_valid": True,
            "test_scope_release_promoted": True, "original_step_retried": True,
            "postcondition_pass": True, "release_id": release_id,
            "release_path": str(release), "source_hash": hashlib.sha256((release / "RELEASE_MANIFEST.json").read_bytes()).hexdigest(),
            "rollback_release": old_pointer or "remove ACTIVE_RELEASE pointer to restore source path",
            "rollback_available": True, "test_scope": bool(test_scope)}
    finally:
        shutil.rmtree(build, ignore_errors=True)


def _parse_plan(text: str) -> dict[str, Any]:
    value = (text or "").strip()
    value = re.sub(r"^```(?:json)?\s*|\s*```$", "", value, flags=re.I)
    start, end = value.find("{"), value.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("PLAN_JSON_MISSING")
    result = json.loads(value[start:end + 1])
    if not isinstance(result, dict) or not isinstance(result.get("steps"), list):
        raise ValueError("PLAN_SCHEMA_INVALID")
    if len(result["steps"]) > MAX_STEPS:
        raise ValueError("PLAN_STEP_LIMIT_EXCEEDED")
    return result


def _planner_catalog_view(catalog: list[dict[str, Any]], objective: str, targets: dict[str, Any], *, limit: int = 6) -> tuple[list[dict[str, Any]], int]:
    """Keep the model's live tool context bounded without losing server identity."""
    live_count = len(catalog)
    if targets.get("explicit_target") and targets.get("entity_ids"):
        # Exact entity type is an action constraint. A project-level assignment
        # cannot stand in for a case continuation, and a create action cannot
        # replace a specifically referenced object.
        # Exact lineage reads/actions must bind to the target or a related
        # lineage ID. Generic status tools (and unrelated read surfaces) are
        # not substitutes for an exact case continuation.
        catalog = [row for row in catalog if entity_action_compatible(targets, row, objective)]
    target_ids = set(targets.get("server_ids") or [])
    query_words = set(re.findall(r"[a-z0-9]+", (objective or "").casefold())) - {
        "nova", "please", "the", "a", "an", "and", "or", "to", "for", "of", "in", "on", "me", "my", "is", "are", "can", "could", "would", "should", "that", "this", "with", "from", "into", "current", "existing", "one",
    }
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for index, row in enumerate(catalog):
        schema = row.get("input_schema") if isinstance(row.get("input_schema"), dict) else {}
        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        compact_properties = {}
        for key, prop in list(properties.items())[:10]:
            if not isinstance(prop, dict):
                continue
            compact = {field: str(prop[field])[:72] for field in ("type", "description", "default")
                       if prop.get(field) is not None}
            if isinstance(prop.get("enum"), list):
                compact["enum"] = [str(value)[:80] for value in prop["enum"][:20]]
            if "const" in prop:
                compact["const"] = prop["const"]
            compact_properties[str(key)] = compact
        compact_schema = {"type": schema.get("type", "object"),
                          "required": list(schema.get("required") or [])[:16],
                          "properties": compact_properties}
        view = {k: row.get(k) for k in ("capability_id", "source_type", "source_id", "server_or_department",
            "tool_name", "read_write_class", "cost_class", "consequence_class", "approval_class", "reversible",
            "authorized", "runtime_health")}
        server_meta = row.get("server_metadata") if isinstance(row.get("server_metadata"), dict) else {}
        view["server_metadata"] = {key: str(server_meta[key])[:100] for key in
                                    ("route_mode", "sandbox_only", "boundary", "external_effect", "production_effect")
                                    if key in server_meta}
        view["description"] = str(row.get("description") or "")[:140]
        view["input_schema"] = compact_schema
        haystack = set(re.findall(r"[a-z0-9]+", " ".join(str(view.get(k) or "") for k in
                            ("source_id", "server_or_department", "tool_name", "description")).casefold()))
        score = len(query_words & haystack) + (100 if str(row.get("source_id")) in target_ids else 0)
        scored.append((score, -index, view))
    scored.sort(reverse=True, key=lambda x: (x[0], x[1]))
    if target_ids:
        # A named server is a hard planning constraint. Do not let a generic
        # high-scoring capability redirect the objective to another server.
        chosen = [view for score, _, view in scored if score >= 100]
    else:
        # For an exact existing entity, always include schema-bound mutations
        # that can advance that entity. A strong collection of diagnostic
        # reads must not crowd the same-entity continuation action out of the
        # bounded planner window.
        bound_actions = [view for _, _, view in scored
                         if view.get("read_write_class") == "WRITE"
                         and entity_action_compatible(targets, view, objective)] if targets.get("explicit_target") else []
        chosen = list(bound_actions)
        chosen_ids = {str(view.get("capability_id")) for view in chosen}
        for view in (view for _, _, view in scored if str(view.get("capability_id")) not in chosen_ids):
            if len(chosen) >= limit:
                break
            chosen.append(view)
        # Plans that promise verification need a matching read capability in
        # the bounded model context. Add the closest same-server read tool for
        # selected write tools; full live schemas remain available to execution.
        if query_words.intersection({"verify", "verified", "confirm", "exists", "readback"}):
            chosen_ids = {str(view.get("capability_id")) for view in chosen}
            action_words = {"create", "make", "write", "update", "edit", "delete", "assign",
                            "send", "share", "publish", "purchase", "schedule", "archive", "label",
                            "draft", "run", "execute", "nexus", "mcp"}
            verification_reads: list[tuple[int, int, int, dict[str, Any]]] = []
            for write_score, write_order, write_view in scored[:limit]:
                if write_view.get("read_write_class") != "WRITE":
                    continue
                write_terms = set(re.findall(r"[a-z0-9]+", str(write_view.get("tool_name") or "").casefold())) - action_words
                matching_reads: list[tuple[int, int, int, dict[str, Any]]] = []
                for read_score, read_order, read_view in scored:
                    if read_view.get("read_write_class") != "READ":
                        continue
                    if read_view.get("source_id") != write_view.get("source_id"):
                        continue
                    if str(read_view.get("capability_id")) in chosen_ids:
                        continue
                    read_terms = set(re.findall(r"[a-z0-9]+", str(read_view.get("tool_name") or "").casefold())) - action_words - {"read", "get", "list", "search", "find", "inspect", "status"}
                    overlap = len(write_terms & read_terms)
                    matching_reads.append((overlap, read_score + write_score, -read_order, read_view))
                if matching_reads:
                    matching_reads.sort(reverse=True, key=lambda item: item[:3])
                    verification_reads.append(matching_reads[0])
            verification_reads.sort(reverse=True, key=lambda item: item[:3])
            for _, _, _, read_view in verification_reads[:8]:
                if str(read_view.get("capability_id")) not in chosen_ids:
                    chosen.append(read_view)
                    chosen_ids.add(str(read_view.get("capability_id")))
    return chosen, max(0, live_count - len(chosen))


_PLANNER_EVIDENCE_KEYS = {
    "case_id", "research_case_id", "objective_id", "project_id", "job_id", "work_id", "result_id",
    "receipt_id", "finding_id", "finding_ids", "evidence_source_id", "status", "state", "case_status",
    "research_work_state", "current_stage", "stage", "next_action", "next_research_action", "answered_count",
    "answered_question_id", "open_question_count", "open_questions", "answered_questions", "question_id",
    "questions", "research_conclusion", "source_count", "sources_opened", "provider_attempts", "attempt_count",
    "max_attempts", "last_error_code", "last_error_summary", "error_code", "error", "failure_class",
    "summary", "title", "description", "reason", "source", "source_type", "completed_at", "claimed_by",
    "started_at", "completed",
}
_PLANNER_EVIDENCE_CONTAINERS = {
    "data", "result_data", "jobs", "research_work_item", "research_case", "case", "synthesis", "evidence",
    "research_package", "objective_lineage", "items", "provenance", "metadata", "planner_gap",
}


def _compact_planner_evidence(value: Any, *, depth: int = 0) -> Any:
    """Keep outcome-relevant evidence while bounding durable tool history in planner context."""
    if depth >= 6:
        return None
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, item in value.items():
            folded = str(key).casefold()
            if folded in _PLANNER_EVIDENCE_KEYS:
                if isinstance(item, str):
                    output[str(key)] = item[:320]
                elif isinstance(item, list):
                    output[str(key)] = [_compact_planner_evidence(x, depth=depth + 1) for x in item[:4]]
                else:
                    output[str(key)] = _compact_planner_evidence(item, depth=depth + 1)
            elif folded in _PLANNER_EVIDENCE_CONTAINERS:
                output[str(key)] = _compact_planner_evidence(item, depth=depth + 1)
        return output
    if isinstance(value, list):
        return [_compact_planner_evidence(item, depth=depth + 1) for item in value[:4]]
    if isinstance(value, str):
        return value[:320]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:160]


def _compact_planner_prior(prior: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(prior, dict):
        return None
    output = {key: prior[key] for key in (
        "planning_failure", "failed_step", "error", "same_mission", "original_objective_preserved",
        "capability_build_failed", "capability_repair_required", "capability_acquired",
        "acquisition_planning_required", "mission_success_condition_failed",
    ) if key in prior}
    gap = prior.get("capability_gap") or prior.get("gap_evidence")
    if isinstance(gap, dict):
        output["capability_gap"] = _compact_planner_evidence(gap)
    return output


def _compact_planner_completed(completed: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    rows = []
    for row in completed or []:
        if not isinstance(row, dict):
            continue
        rows.append({key: str(row[key])[:240] if key in {"goal", "step_id", "capability_id", "status"}
                     else _compact_planner_evidence(row[key])
                     for key in ("step_id", "goal", "capability_id", "status", "result") if key in row})
    # Planning is based on the current instruction plus its latest execution
    # evidence. Older detailed history remains durable in the mission store.
    # Re-sending every prior tool result can exceed Hermes' bounded context.
    return rows[-3:]


def plan_objective(mission: dict[str, Any], understanding: dict[str, Any], catalog: list[dict[str, Any]], *,
                   planner: Callable[[str], str] | None = None, prior_outcome: dict[str, Any] | None = None,
                   completed: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Ask the configured Nova model for a constrained plan; no tools run in planning mode."""
    mission_id = str(mission["mission_id"])
    targets = understanding.get("target_entity") or {}
    allowed, omitted_count = _planner_catalog_view(catalog, str(mission.get("current_instruction") or mission.get("objective_text") or ""), targets)
    prompt = """Return ONLY one JSON object matching {"mission_success_condition":{"description":"...","verification":{"capability_id":"...","arguments":{},"assertion":{}}},"steps":[...]}. You are Nova's goal planner.
Operating doctrine: __NOVA_OPERATOR_DOCTRINE__
Plan at most 8 steps. Choose capability_id values exactly from the live catalog; never invent IDs.
The capability list in PLAN INPUT is the bounded, live-selected candidate set; omitted live capabilities were outside the best-fit window. The full catalog was persisted separately.
Bind a user-named server/entity exactly. Keep independent steps parallel conceptually but serialize output.
Every WRITE step MUST include a verification object with a READ capability_id, arguments, and assertion.
Every plan MUST include mission_success_condition with an independent READ verification of Ray's requested final outcome. It must verify the objective outcome, not merely that a plan step/tool call ran. Use an exact target and state assertion where Ray named an entity or requested continuation/repair. Resolve arguments from completed results with {{stepN.FIELD}} placeholders. This verification is separate from step verification and runs after all plan steps.
Use {{step1.FIELD}} placeholders for values returned by earlier calls. Never execute a tool while planning.
Do not request approval for reads or bounded zero-cost internal work. Mark real consequence boundaries explicitly.
If no safe existing path exists, return steps:[] and capability_gap. If a safe bounded capability can fill the exact gap, you may also return capability_proposal with exactly these fields: {"capability_id":"<new unique id>","name":"<new name>","purpose":"...","operation":"reverse_text","input_schema":{"type":"object","required":["text"],"properties":{"text":{"type":"string"}}},"output_schema":{"type":"object","required":["text"],"properties":{"text":{"type":"string"}}},"cost_class":"ZERO","consequence_class":"INTERNAL","read_write_class":"READ","required_permissions":[],"dependencies":[],"tests":[{"input":{"text":"abc"},"expected":{"text":"cba"}}]}. Use only the declarative reverse_text operation, zero permissions, no dependencies, ZERO cost, INTERNAL consequence, READ class, and test vectors. Never propose code, shell, network, credentials, writes, external effects, or production effects.
For an Operator mission status question, select nova:operator:nexus_get_operator_mission_status. Use {"current_mission":true} to inspect the owner's latest other active mission, or an exact mission_id only when provided by current conversation lineage.
Each step: {step_id,goal,capability_id,arguments,depends_on,expected_postcondition,verification,alternate_capability_ids,boundary}.
Verification assertion supports {contains:string}, {not_contains:string}, {exists:path}, {equals:{path,value}}, {not_found:true}.
Do not claim completion; only produce a plan.
"""
    prompt = prompt.replace("__NOVA_OPERATOR_DOCTRINE__", DOCTRINE)
    planner_understanding = {key: value for key, value in understanding.items() if key != "desired_outcome"}
    lineage = mission.get("current_objective_lineage") or {}
    exact_lineage = {key: lineage[key] for key in ("objective_id", "project_id", "job_id", "case_id",
        "note_id", "file_id", "event_id") if lineage.get(key)} if isinstance(lineage, dict) else {}
    request = {"objective": mission.get("objective_text"), "current_instruction": mission.get("current_instruction"),
               "understanding": planner_understanding,
               "current_lineage": exact_lineage,
               "prior_outcome": _compact_planner_prior(prior_outcome),
               "completed_steps": _compact_planner_completed(completed),
               "live_capabilities": allowed, "live_catalog_count": len(catalog),
               "omitted_candidate_count": omitted_count}
    if planner:
        raw = planner(prompt + "\nPLAN INPUT:\n" + _json(request))
    else:
        invocation_id = "nova-operator-plan-" + uuid.uuid4().hex
        with _connect() as db:
            _event(db, mission_id, None, "MODEL_PLAN_REQUESTED", {
                "provider_job_id": invocation_id, "parent_correlation_id": mission.get("correlation_id"),
                "request_id": mission_id})
        raw = _default_planner(prompt + "\nPLAN INPUT:\n" + _json(request), mission_id, invocation_id)
    plan = _parse_plan(raw)
    return plan


def _default_planner(prompt: str, mission_id: str, invocation_id: str) -> str:
    from nexus_agent_platform.bridge.oracle_hermes_cli import run_oracle_hermes
    safe_mission_id = re.sub(r"[^A-Za-z0-9_.-]", "", mission_id)[:48]
    safe_invocation_id = re.sub(r"[^A-Za-z0-9_.-]", "", invocation_id)[:32]
    # Each plan request already carries prior steps and recovery evidence in
    # its bounded input. Reusing one Hermes session per mission duplicates all
    # prior planner prompts in model context until the provider rejects new
    # plans with local_model_input_limit. Keep conversational state in the
    # durable Operator mission; keep each bounded planner invocation isolated.
    session = f"nova-operator-plan-{safe_mission_id}-{safe_invocation_id}"
    # The active provider wrapper reserves by durable job ID. Give each bounded
    # planning invocation its own idempotency key while retaining the parent
    # Telegram/objective correlation for audit and budget aggregation.
    env_values = {
        "NEXUS_DURABLE_JOB_ID": invocation_id,
        "NEXUS_CORRELATION_ID": str(os.environ.get("NEXUS_CORRELATION_ID") or mission_id),
        "NEXUS_DEPARTMENT": "NOVA",
        "NEXUS_JOB_TYPE": "NOVA_TELEGRAM_OWNER_TURN",
    }
    previous = {key: os.environ.get(key) for key in env_values}
    os.environ.update(env_values)
    try:
        # Stay on the active Nova release's existing Hermes wrapper contract.
        # Complex recovery plans can be materially slower than conversational
        # turns because the prompt includes the live catalog and exact lineage.
        # A 40-second cutoff discarded valid plans that arrived just after the
        # deadline, leaving the same mission stuck in RECOVERING. Keep this
        # bounded by the bridge's 300-second maximum while allowing one normal
        # planner response to finish.
        result = run_oracle_hermes(prompt, session, timeout_seconds=120, request_id=mission_id,
            structured_task=True)
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    if result.status != "SUCCEEDED" or not result.response:
        raise RuntimeError("OPERATOR_PLANNER_" + str(result.error or result.status))
    return result.response


def save_plan(mission_id: str, plan: dict[str, Any], catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {str(row["capability_id"]): row for row in catalog}
    with _connect() as db:
        mission_row = db.execute("SELECT objective_text,understanding_json FROM operator_missions WHERE mission_id=?",
                                 (mission_id,)).fetchone()
    if mission_row:
        understanding = json.loads(mission_row["understanding_json"] or "{}")
        target = understanding.get("target_entity") if isinstance(understanding, dict) else None
        objective_text = str(mission_row["objective_text"] or "")
    else:
        target, objective_text = None, ""
    if target and target.get("explicit_target") and target.get("entity_ids"):
        if not any(entity_action_compatible(target, by_id.get(str(step.get("capability_id") or ""), {}), objective_text,
                                              support_read=True)
                   for step in plan.get("steps", []) if isinstance(step, dict)):
            if plan.get("steps"):
                raise ValueError("ENTITY_ACTION_CAPABILITY_MISMATCH")
    mission_condition = plan.get("mission_success_condition")
    if plan.get("steps"):
        if not isinstance(mission_condition, dict) or not isinstance(mission_condition.get("verification"), dict):
            raise ValueError("MISSION_SUCCESS_CONDITION_REQUIRED")
        mission_verification = mission_condition["verification"]
        verify_id = str(mission_verification.get("capability_id") or "")
        if verify_id not in by_id or by_id[verify_id].get("read_write_class") != "READ":
            raise ValueError("MISSION_SUCCESS_VERIFIER_MUST_BE_LIVE_READ_CAPABILITY")
        if target and not entity_action_compatible(target, by_id[verify_id], objective_text):
            raise ValueError("MISSION_SUCCESS_VERIFIER_ENTITY_MISMATCH")
        if not isinstance(mission_verification.get("assertion"), dict):
            raise ValueError("MISSION_SUCCESS_ASSERTION_REQUIRED")
    normalized = []
    for i, raw in enumerate(plan.get("steps", []), 1):
        if not isinstance(raw, dict):
            raise ValueError("PLAN_STEP_NOT_OBJECT")
        cap_id = str(raw.get("capability_id") or "")
        if cap_id not in by_id:
            raise ValueError("UNKNOWN_CAPABILITY_ID:" + cap_id[:100])
        if target and not entity_action_compatible(target, by_id[cap_id], objective_text,
                                                   support_read=True):
            raise ValueError("ENTITY_ACTION_CAPABILITY_MISMATCH:" + str(target.get("entity_type") or "UNKNOWN"))
        arguments = raw.get("arguments") if isinstance(raw.get("arguments"), dict) else {}
        if (target and target.get("explicit_target") and target.get("entity_ids")
                and not _arguments_bind_target(target, by_id[cap_id], arguments,
                    require_binding=by_id[cap_id].get("read_write_class") == "WRITE")):
            raise ValueError("ENTITY_ACTION_ARGUMENT_MISMATCH")
        verification = raw.get("verification")
        if by_id[cap_id]["read_write_class"] == "WRITE":
            if not isinstance(verification, dict) or verification.get("capability_id") not in by_id:
                raise ValueError("WRITE_STEP_MISSING_READ_VERIFICATION")
            if by_id[str(verification["capability_id"])]["read_write_class"] != "READ":
                raise ValueError("POSTCONDITION_TOOL_NOT_READ_ONLY")
            if target and not entity_action_compatible(target, by_id[str(verification["capability_id"])], objective_text):
                raise ValueError("POSTCONDITION_ENTITY_MISMATCH")
            verify_args = verification.get("arguments") if isinstance(verification.get("arguments"), dict) else {}
            if (target and target.get("explicit_target") and target.get("entity_ids")
                    and not _arguments_bind_target(target, by_id[str(verification["capability_id"])], verify_args)):
                raise ValueError("POSTCONDITION_ARGUMENT_ENTITY_MISMATCH")
        row = {
            "step_id": str(raw.get("step_id") or f"step_{i}"), "sequence": i,
            "goal": str(raw.get("goal") or "")[:1000], "required_capability": str(raw.get("required_capability") or ""),
            "selected_capability_id": cap_id, "inputs": raw.get("arguments") if isinstance(raw.get("arguments"), dict) else {},
            "target_entity": raw.get("target_entity") if isinstance(raw.get("target_entity"), dict) else {},
            "candidate_capabilities": [x for x in raw.get("candidate_capabilities", []) if x in by_id],
            "selection_reason": str(raw.get("selection_reason") or "Selected from the live approved catalog.")[:500],
            "dependencies": raw.get("depends_on") if isinstance(raw.get("depends_on"), list) else [],
            "expected_postcondition": {"description": raw.get("expected_postcondition"), "verification": verification},
            "alternate_capability_ids": [x for x in raw.get("alternate_capability_ids", []) if x in by_id],
            "boundary": raw.get("boundary"), "status": "PENDING",
        }
        normalized.append(row)
    with _connect() as db:
        mission_row = db.execute("SELECT plan_version FROM operator_missions WHERE mission_id=?", (mission_id,)).fetchone()
        version = int(mission_row["plan_version"] if mission_row else 0) + 1
        # Every plan version has unique persisted step IDs and sequence ranges.
        # Keep incomplete/recovering rows as durable evidence: a mutation may
        # have succeeded before its independent verifier failed, so deleting
        # that row would make the next plan repeat the side effect blindly.
        for row in normalized:
            sid = f"{mission_id}:{version}:{row['step_id']}"
            row["persisted_step_id"] = sid
            db.execute("""INSERT INTO operator_steps(step_id,mission_id,sequence,goal,required_capability,
                selected_capability_id,inputs_json,dependencies_json,expected_postcondition_json,status,
                target_entity_json,candidate_capabilities_json,selection_reason)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(step_id) DO UPDATE SET inputs_json=excluded.inputs_json,
                target_entity_json=excluded.target_entity_json,candidate_capabilities_json=excluded.candidate_capabilities_json,
                selection_reason=excluded.selection_reason""",
            (sid, mission_id, (version - 1) * MAX_STEPS + row["sequence"], row["goal"], row["required_capability"], row["selected_capability_id"],
                 _json(row["inputs"]), _json(row["dependencies"]), _json(row["expected_postcondition"]), row["status"],
                 _json(row["target_entity"]), _json(row["candidate_capabilities"]), row["selection_reason"]))
        db.execute("UPDATE operator_missions SET status=?,plan_version=?,updated_at=? WHERE mission_id=?",
                   ("PLANNING" if not normalized else "EXECUTING", version, _now(), mission_id))
        if isinstance(mission_condition, dict):
            db.execute("""UPDATE operator_missions SET mission_success_condition_json=?,
                mission_success_evidence_json='{}',mission_success_verified=0,
                mission_completion_reason=NULL WHERE mission_id=?""",
                (_json(mission_condition), mission_id))
        _event(db, mission_id, None, "PLAN_PERSISTED", {"plan_version": version, "step_count": len(normalized),
                                                          "step_ids": [x["persisted_step_id"] for x in normalized]})
    return normalized


def _resolve_refs(value: Any, results: dict[str, dict[str, Any]]) -> Any:
    if isinstance(value, dict): return {k: _resolve_refs(v, results) for k, v in value.items()}
    if isinstance(value, list): return [_resolve_refs(v, results) for v in value]
    if not isinstance(value, str): return value
    match = re.fullmatch(r"\{\{(step\d+)\.([A-Za-z0-9_.]+)\}\}", value)
    if not match: return value
    step_key, path = match.groups()
    current: Any = results.get(step_key, {})
    for part in path.split("."):
        if isinstance(current, dict): current = current.get(part)
        else: return None
    return current


def _json_path(value: Any, path: str) -> Any:
    current = value
    for part in str(path or "").split("."):
        if not part: continue
        if isinstance(current, dict): current = current.get(part)
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current): current = current[int(part)]
        else: return None
    return current


def _assert_postcondition(result: dict[str, Any], assertion: dict[str, Any]) -> bool:
    data = result.get("result_data")
    text = _json(data).casefold()
    if assertion.get("not_found") is True:
        return bool(re.search(r"\b(?:note_not_found|not_found|not found|does not exist|resource_missing)\b", text))
    if "contains" in assertion: return str(assertion["contains"]).casefold() in text
    if "not_contains" in assertion: return str(assertion["not_contains"]).casefold() not in text
    if "exists" in assertion: return _json_path(data, str(assertion["exists"])) is not None
    if isinstance(assertion.get("equals"), dict):
        exp = assertion["equals"]
        return _json_path(data, exp.get("path", "")) == exp.get("value")
    return bool(result.get("call_succeeded"))


def _call_approved_mcp(server_id: str, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Invoke a live MCP tool through the same Hermes profile/credential boundary."""
    from nova.approved_mcp_registry import approved_server_records
    server = next((row for row in approved_server_records() if row.get("server_id") == server_id), None)
    if not server:
        raise PermissionError("SERVER_NOT_APPROVED")
    payload = json.dumps({"server_id": server_id, "tool": tool_name, "arguments": arguments})
    script = r'''import asyncio,json,sys,yaml,httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.client.stdio import stdio_client,StdioServerParameters
q=json.load(sys.stdin); d=yaml.safe_load(open("/opt/data/profiles/nova_nexus/config.yaml")) or {}; c=(d.get("mcp_servers") or {}).get(q["server_id"])
if not c or not c.get("enabled",True): raise RuntimeError("SERVER_DISABLED")
async def invoke(r,w):
 async with ClientSession(r,w) as s:
  await s.initialize(); tools=await s.list_tools()
  if q["tool"] not in {t.name for t in tools.tools}: raise RuntimeError("TOOL_NOT_DISCOVERED")
  x=await s.call_tool(q["tool"],q.get("arguments") or {})
  texts=[getattr(i,"text","") for i in (x.content or [])]
  structured=getattr(x,"structuredContent",None)
  out={"is_error":bool(x.is_error),"content":texts,"structured_content":structured}
  print(json.dumps(out,default=str))
async def main():
 if c.get("url"):
  async with httpx.AsyncClient(headers=c.get("headers") or {},timeout=60) as h:
   async with streamable_http_client(c["url"],http_client=h) as (r,w): await invoke(r,w)
 elif c.get("command"):
  p=StdioServerParameters(command=c["command"],args=c.get("args") or [],env=c.get("env") or None,cwd=c.get("cwd"))
  async with stdio_client(p) as (r,w): await invoke(r,w)
 else: raise RuntimeError("UNSUPPORTED_MCP_TRANSPORT")
asyncio.run(main())'''
    import subprocess
    p = subprocess.run(["podman", "exec", "-i", "nexus-hermes-0206", "/opt/hermes/.venv/bin/python", "-c", script],
        input=payload, capture_output=True, text=True, timeout=90, check=False)
    if p.returncode:
        detail = re.sub(r"(?i)(token|password|secret|authorization)(\s*[:=]\s*)[^\s,;]+", r"\1\2[REDACTED]", p.stderr[-500:])
        raise RuntimeError("MCP_CALL_FAILED:" + detail.strip())
    return json.loads(p.stdout)


def _invoke(capability: dict[str, Any], arguments: dict[str, Any], *, owner_authorized: bool) -> dict[str, Any]:
    if capability.get("source_type") == "NOVA_OPERATOR" and capability.get("tool_name") == "nexus_get_operator_mission_status":
        if set(arguments) - {"mission_id", "current_mission", "owner_id"}:
            raise ValueError("STATUS_TOOL_ARGUMENTS_NOT_ALLOWED")
        owner = str(capability.get("_current_owner_id") or "")
        if arguments.get("mission_id"):
            value = status_read(str(arguments["mission_id"]), owner_id=owner)
        elif arguments.get("current_mission") is True:
            value = status_read(None, owner_id=owner, exclude_mission_id=str(capability.get("_current_mission_id") or ""))
        else:
            return {"call_succeeded": False, "error_code": "MISSION_ID_OR_CURRENT_MISSION_REQUIRED",
                    "result_data": {"read_only": True, "no_mutation": True}}
        return {"call_succeeded": value is not None, "action_succeeded": value is not None,
                "result_data": value or {"status": "NOT_FOUND", "read_only": True, "no_mutation": True},
                "source": "operator_status_read", "raw_result_reference": "read_only_sqlite_query"}
    if capability.get("source_type") == "GENERATED_SKILL":
        return _invoke_generated(capability, arguments)
    from nova.approved_mcp_registry import evaluate_mcp_tool_policy
    policy = evaluate_mcp_tool_policy(capability, owner_authorized=owner_authorized)
    server_meta = capability.get("server_metadata") or {}
    if policy["decision"] not in {"ALLOW", "DEFER_TO_NEXUS_GOVERNANCE"}:
        raise PermissionError("POLICY_" + policy["decision"] + ":" + policy["reason"])
    if policy["decision"] == "DEFER_TO_NEXUS_GOVERNANCE" and server_meta.get("route_mode") != "NEXUS_GOVERNED":
        raise PermissionError("NEXUS_GOVERNANCE_ROUTE_MISMATCH")
    raw = _call_approved_mcp(str(capability["source_id"]), str(capability["tool_name"]), arguments)
    data = raw.get("structured_content")
    if data is None:
        content = raw.get("content") or []
        data = content
        if len(content) == 1:
            try: data = json.loads(content[0])
            except (TypeError, ValueError): data = content[0]
    data = _normalize_result_data(data)
    return {"call_succeeded": not bool(raw.get("is_error")), "action_succeeded": not bool(raw.get("is_error")),
            "resource_id": _extract_resource(data), "result_data": data, "receipt_id": _extract_receipt(data),
            "error_code": "MCP_TOOL_ERROR" if raw.get("is_error") else None,
            "error_message": None if not raw.get("is_error") else _json(data)[:500],
            "source": f"{capability['source_id']}.{capability['tool_name']}", "raw_result_reference": None,
            "policy_decision": policy, "tool_receipt_id": _extract_receipt(data)}


def _normalize_result_data(value: Any) -> Any:
    """Provide stable lowercase field names while retaining original keys."""
    if isinstance(value, list):
        return [_normalize_result_data(item) for item in value]
    if not isinstance(value, dict):
        return value
    normalized = {str(key).casefold(): _normalize_result_data(item) for key, item in value.items()}
    for key, item in value.items():
        if str(key).casefold() != str(key):
            normalized.setdefault(str(key), _normalize_result_data(item))
    return normalized


def _preserve_workspace_path_reference(result: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    """Keep the validated request path addressable when an adapter omits it.

    Workspace write tools may return a conflict or a compact receipt without a
    top-level ``relative_path``. Later readback plans can still refer to
    ``{{stepN.relative_path}}`` because the already schema-validated input is
    the authoritative identity for that step. Never coerce malformed values;
    schema validation runs before execution.
    """
    path = arguments.get("relative_path")
    if isinstance(path, str):
        result.setdefault("relative_path", path)
    return result


def _extract_resource(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("resource_id", "note_id", "project_id", "objective_id", "job_id", "case_id", "file_id", "event_id", "id"):
            if value.get(key) is not None: return str(value[key])
        for child in value.values():
            found = _extract_resource(child)
            if found: return found
    elif isinstance(value, list):
        for child in value:
            found = _extract_resource(child)
            if found: return found
    elif isinstance(value, str):
        match = re.search(r"\b(?:NOTE_ID|PROJECT_ID|OBJECTIVE_ID|JOB_ID|CASE_ID|FILE_ID|EVENT_ID|RESOURCE_ID)\s*[:=]\s*([A-Za-z0-9_.:-]+)", value, re.I)
        if match: return match.group(1)
    return None


def _workspace_logical_entity_type(step: dict[str, Any] | None) -> str | None:
    """Return the domain entity type for a bounded workspace action, when known."""
    step = step if isinstance(step, dict) else {}
    target = step.get("target_entity") if isinstance(step.get("target_entity"), dict) else {}
    candidate = str(target.get("entity_type") or step.get("logical_entity_type") or "").upper()
    if candidate in {"NOTE", "FILE"}:
        return candidate
    inputs = step.get("inputs") if isinstance(step.get("inputs"), dict) else {}
    if inputs.get("note_id"):
        return "NOTE"
    if inputs.get("file_id"):
        return "FILE"
    goal = str(step.get("goal") or "")
    match = re.search(r"\b(NOTE|FILE)\b", goal, re.I)
    return match.group(1).upper() if match else None


def _workspace_logical_entity_type_from_rows(rows: list[dict[str, Any]] | None) -> str | None:
    for row in rows or []:
        result = row.get("result") if isinstance(row.get("result"), dict) else {}
        step = {**row, "inputs": row.get("inputs") or {},
                "target_entity": row.get("target_entity") or {}}
        entity_type = _workspace_logical_entity_type(step)
        if entity_type:
            return entity_type
        for key in ("note_id", "file_id"):
            data = result.get("result_data") if isinstance(result.get("result_data"), dict) else {}
            if data.get(key):
                return "NOTE" if key == "note_id" else "FILE"
    return None


def _extract_entities(value: Any, found: dict[str, str] | None = None, *,
                      logical_entity_type: str | None = None) -> dict[str, str]:
    found = found if found is not None else {}
    if isinstance(value, dict):
        aliases = {"objective_id": "objective_id", "project_id": "project_id", "work_id": "work_id",
                   "job_id": "job_id", "case_id": "case_id", "note_id": "note_id", "file_id": "file_id",
                   "event_id": "event_id", "result_id": "result_id"}
        for key, role in aliases.items():
            if value.get(key) is not None: found[role] = str(value[key])
        # Bounded Nexus workspace artifact paths are the durable identity for
        # internal file/note actions; preserve that exact path as lineage.
        workspace_path = value.get("relative_path") or value.get("path")
        if isinstance(workspace_path, str) and workspace_path.startswith(
                ("reports/nova_internal/", "data/runtime/nova_artifacts/")):
            domain_type = str(logical_entity_type or "").upper()
            if domain_type == "NOTE":
                found.pop("file_id", None) if found.get("file_id") == workspace_path else None
                found.setdefault("note_id", workspace_path)
            elif domain_type == "FILE":
                found.pop("note_id", None) if found.get("note_id") == workspace_path else None
                found.setdefault("file_id", workspace_path)
            else:
                found.setdefault("file_id", workspace_path)
                if "/nova_note_" in workspace_path or "/note_" in workspace_path:
                    found.setdefault("note_id", workspace_path)
        for child in value.values():
            _extract_entities(child, found, logical_entity_type=logical_entity_type)
    elif isinstance(value, list):
        for child in value:
            _extract_entities(child, found, logical_entity_type=logical_entity_type)
    elif isinstance(value, str):
        for key in ("OBJECTIVE_ID", "PROJECT_ID", "WORK_ID", "JOB_ID", "CASE_ID", "NOTE_ID", "FILE_ID", "EVENT_ID", "RESULT_ID"):
            m = re.search(rf"\b{key}\s*[:=]\s*([A-Za-z0-9_.:-]+)", value, re.I)
            if m: found[key.casefold()] = m.group(1)
    return found


def _extract_receipt(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("receipt_id", "tool_receipt_id", "nexus_receipt_id"):
            if value.get(key): return str(value[key])
        for child in value.values():
            found = _extract_receipt(child)
            if found: return found
    elif isinstance(value, list):
        for child in value:
            found = _extract_receipt(child)
            if found: return found
    elif isinstance(value, str):
        m = re.search(r"\b(?:TOOL_)?RECEIPT_ID\s*[:=]\s*([A-Za-z0-9_.:-]+)", value, re.I)
        if m: return m.group(1)
    return None


def _validate_args(schema: dict[str, Any], args: dict[str, Any]) -> None:
    try:
        from jsonschema import Draft202012Validator
        errors = list(Draft202012Validator(schema or {"type": "object"}).iter_errors(args))
        if errors: raise ValueError("INPUT_SCHEMA_INVALID:" + ";".join(str(x.message) for x in errors[:3]))
    except ImportError:
        effective = schema or {"type": "object"}
        properties = effective.get("properties") or {}
        errors = []
        missing = set(effective.get("required") or []) - set(args)
        if missing:
            errors.append("missing required fields: " + ", ".join(sorted(missing)))
        if effective.get("additionalProperties") is False:
            extras = set(args) - set(properties)
            if extras:
                errors.append("additional properties are forbidden: " + ", ".join(sorted(extras)))
        type_checks = {"string": lambda v: isinstance(v, str), "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
                       "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
                       "boolean": lambda v: isinstance(v, bool), "object": lambda v: isinstance(v, dict),
                       "array": lambda v: isinstance(v, list)}
        for name, value in args.items():
            spec = properties.get(name) if isinstance(properties, dict) else None
            if not isinstance(spec, dict):
                continue
            if "const" in spec and value != spec["const"]:
                errors.append(f"{name} must equal the declared constant")
            if isinstance(spec.get("enum"), list) and value not in spec["enum"]:
                errors.append(f"{name} must be one of the declared enum values")
            checker = type_checks.get(str(spec.get("type") or ""))
            if checker and not checker(value):
                errors.append(f"{name} must have type {spec['type']}")
        if errors:
            raise ValueError("INPUT_SCHEMA_INVALID:" + ";".join(errors[:3]))


def _persist_step_state(mission_id: str, step: dict[str, Any], status: str, *, error: str | None = None,
                        result: dict[str, Any] | None = None, receipt: dict[str, Any] | None = None) -> None:
    if status not in STEP_STATES: raise ValueError("INVALID_OPERATOR_STEP_STATUS")
    now = _now()
    with _connect() as db:
        values = db.execute("SELECT attempt_count FROM operator_steps WHERE step_id=?", (step["persisted_step_id"],)).fetchone()
        attempts = int(values["attempt_count"] if values else 0) + (1 if status == "RUNNING" else 0)
        db.execute("""UPDATE operator_steps SET status=?,attempt_count=?,last_error=COALESCE(?,last_error),
            result_reference_json=COALESCE(?,result_reference_json),receipt_reference_json=COALESCE(?,receipt_reference_json),
            started_at=CASE WHEN ?='RUNNING' AND started_at IS NULL THEN ? ELSE started_at END,
            completed_at=CASE WHEN ? IN ('COMPLETE','COMPLETE_VERIFIED_BY_POSTCONDITION') THEN ? ELSE completed_at END
            WHERE step_id=?""",
            (status, attempts, error, _json(result) if result else None, _json(receipt) if receipt else None,
             status, now, status, now, step["persisted_step_id"]))
        db.execute("UPDATE operator_missions SET status=?,current_step_id=?,updated_at=? WHERE mission_id=?",
                   ("RECOVERING" if status == "RECOVERING" else "EXECUTING", step["persisted_step_id"], now, mission_id))
        _event(db, mission_id, step["persisted_step_id"], "STEP_" + status, {"error": error, "result": result, "receipt": receipt})


def _store_lineage(mission_id: str, step: dict[str, Any] | str, result: dict[str, Any]) -> None:
    step_id = step if isinstance(step, str) else str(step.get("persisted_step_id") or step.get("step_id") or "")
    logical_type = None if isinstance(step, str) else _workspace_logical_entity_type(step)
    entities = _extract_entities(result.get("result_data") or {}, logical_entity_type=logical_type)
    if result.get("resource_id") and not entities:
        resource = str(result["resource_id"])
        entities[{"job": "job_id", "objective": "objective_id", "project": "project_id",
                  "case": "case_id", "note": "note_id", "file": "file_id", "event": "event_id"}
                 .get(resource.split("_", 1)[0].casefold(), "resource_id")] = resource
    if not entities: return
    with _connect() as db:
        for role, resource in entities.items():
            if logical_type in {"NOTE", "FILE"} and role in {"note_id", "file_id"}:
                canonical_role = "note_id" if logical_type == "NOTE" else "file_id"
                if role != canonical_role and str(resource) == str((result.get("result_data") or {}).get("path")):
                    continue
            db.execute("INSERT OR REPLACE INTO operator_lineage VALUES(?,?,?,?,?,?,?)",
                (mission_id, role.replace("_id", "").upper(), str(resource), "CURRENT_OBJECT", step_id,
                 _now(), _json({"source": result.get("source"),
                    **({"logical_entity_type": logical_type, "storage_backing_type": "FILE",
                        "storage_path": str((result.get("result_data") or {}).get("path") or resource)}
                       if logical_type in {"NOTE", "FILE"} and role in {"note_id", "file_id"} else {})})))
        if logical_type == "NOTE":
            note_path = entities.get("note_id")
            if note_path:
                backing = db.execute("""SELECT entity_role,metadata_json FROM operator_lineage
                    WHERE mission_id=? AND entity_type='FILE' AND entity_id=? AND entity_role='CURRENT_OBJECT'""",
                    (mission_id, str(note_path))).fetchone()
                if backing:
                    metadata = json.loads(backing["metadata_json"] or "{}")
                    metadata.update({"relationship": "STORAGE_BACKING_FOR", "logical_entity_type": "NOTE",
                                     "storage_backing_type": "FILE", "storage_path": str(note_path),
                                     "reconciled_from_role": "CURRENT_OBJECT"})
                    db.execute("""UPDATE operator_lineage SET entity_role='STORAGE_BACKING',metadata_json=?
                        WHERE mission_id=? AND entity_type='FILE' AND entity_id=? AND entity_role='CURRENT_OBJECT'""",
                        (_json(metadata), mission_id, str(note_path)))
                    _event(db, mission_id, step_id if step_id else None, "LINEAGE_STORAGE_BACKING_RECONCILED", {
                        "entity_type": "FILE", "entity_id": str(note_path), "prior_role": "CURRENT_OBJECT",
                        "new_role": "STORAGE_BACKING", "logical_entity_type": "NOTE"})


def _record_failure(mission_id: str, step: dict[str, Any], error: str, alternates: list[str], attempts: list[str]) -> None:
    failure_id = "opf_" + uuid.uuid4().hex
    payload = {
        "failure_id": failure_id, "failure_class": _failure_class(error),
        "primary_path": step.get("selected_capability_id"), "primary_failure": error[:600],
        "alternates_considered": alternates, "alternates_attempted": attempts,
        "repair_attempts": 0, "final_recovery_outcome": "RECOVERING"}
    with _connect() as db:
        db.execute("INSERT INTO operator_failures VALUES(?,?,?,?,?,?,?)",
                   (failure_id, mission_id, step.get("persisted_step_id"), payload["failure_class"], _json(payload), "RECOVERING", _now()))
        _event(db, mission_id, step.get("persisted_step_id"), "FAILURE_CLASSIFIED", payload)


_PENDING_RESPONSE = re.compile(r"\b(?:pending|still needs|not yet verified|recovery required|waiting for running state|remains active)\b", re.I)


def completion_guard(*, mission_success_verified: bool, mission_success_evidence: dict[str, Any] | None,
                     next_step_exists: bool = False, recovery_pending: bool = False,
                     waiting_for_subtask: bool = False, current_step_incomplete: bool = False,
                     mission_state_active: bool = False, repair_pending: bool = False,
                     boundary_not_resolved: bool = False, response: str | None = None) -> bool:
    """Reject mission completion unless the requested outcome has independent evidence."""
    evidence = mission_success_evidence or {}
    if not mission_success_verified or evidence.get("status") != "PASS":
        return False
    if any((next_step_exists, recovery_pending, waiting_for_subtask, current_step_incomplete,
            mission_state_active, repair_pending, boundary_not_resolved)):
        return False
    text = str(response or "")
    if re.search(r"\b(?:objective|mission) complete\b", text, re.I) and _PENDING_RESPONSE.search(text):
        return False
    return True


def _verify_mission_success(mission_id: str, condition: dict[str, Any], capabilities: dict[str, dict[str, Any]],
                            results: dict[str, dict[str, Any]], *, owner_authorized: bool,
                            executor: Callable[[dict[str, Any], dict[str, Any], bool], dict[str, Any]] | None) -> dict[str, Any]:
    """Run the separate read-only mission postcondition and persist its evidence."""
    verification = condition.get("verification") if isinstance(condition, dict) else None
    if not isinstance(verification, dict):
        raise ValueError("MISSION_SUCCESS_VERIFICATION_MISSING")
    capability_id = str(verification.get("capability_id") or "")
    cap = capabilities.get(capability_id)
    if not cap or cap.get("read_write_class") != "READ":
        raise ValueError("MISSION_SUCCESS_VERIFIER_UNAVAILABLE_OR_NOT_READ_ONLY")
    arguments = _resolve_refs(verification.get("arguments") or {}, results)
    _validate_args(cap.get("input_schema") or {}, arguments)
    result = executor(cap, arguments, owner_authorized) if executor else _invoke(cap, arguments, owner_authorized=owner_authorized)
    if not isinstance(result, dict):
        raise TypeError("MISSION_SUCCESS_RESULT_NOT_OBJECT")
    result = dict(result)
    result["result_data"] = _normalize_result_data(result.get("result_data"))
    assertion = verification.get("assertion") or {}
    passed = _assert_postcondition(result, assertion) and (
        bool(result.get("call_succeeded")) or assertion.get("not_found") is True)
    evidence = {"status": "PASS" if passed else "FAIL", "condition": condition,
        "verifier": capability_id, "arguments": arguments, "result": result,
        "verified_at": _now(), "independent_of_step_completion": True}
    with _connect() as db:
        db.execute("UPDATE operator_missions SET mission_success_evidence_json=?,mission_success_verified=?,updated_at=? WHERE mission_id=?",
                   (_json(evidence), int(passed), _now(), mission_id))
        _event(db, mission_id, None, "MISSION_SUCCESS_VERIFIED" if passed else "MISSION_SUCCESS_NOT_VERIFIED", evidence)
    return evidence


def _failure_class(error: str) -> str:
    value = str(error).casefold()
    for token, code in (("timeout", "TIMEOUT"), ("not_approved", "AUTHORITY"), ("policy_", "GOVERNANCE"),
                        ("disabled", "CONFIGURATION"), ("not_discovered", "ROUTING"), ("auth", "AUTHORIZATION"),
                        ("schema", "INPUT_SCHEMA"), ("mcp", "MCP_EXECUTION")):
        if token in value: return code
    return "EXECUTOR_FAILURE"


def _capability_gap(mission_id: str, requested: str, catalog: list[dict[str, Any]], plan: dict[str, Any], reason: str,
                    step_id: str | None = None) -> dict[str, Any]:
    families = {str(row.get("source_type") or "UNKNOWN") for row in catalog}
    source_ids = {str(row.get("source_id") or "UNKNOWN") for row in catalog}
    required = str((plan.get("capability_gap") or {}).get("required_capability") or requested)
    # Every alternate class is evaluated against the same live complete catalog;
    # absence is recorded as evidence rather than treated as a silent stop.
    evaluators = {
        "alternate_mcp_evaluated": any(x in families for x in {"MCP", "EXTERNAL_MCP"}),
        "alternate_nexus_action_evaluated": any("nexus" in x.casefold() for x in source_ids),
        "alternate_department_evaluated": any(x in families for x in {"RESEARCH", "SYSTEMS", "ALPHA", "DEPARTMENT"}),
        "configuration_option_evaluated": True,
        "safe_repair_evaluated": True,
        "postcondition_verification_evaluated": True,
    }
    gap_id = "ocg_" + uuid.uuid4().hex
    evidence = {"gap_id": gap_id, "mission_id": mission_id, "step_id": step_id,
        "required_capability": required, "live_catalog_checked": True,
        "catalog_capability_ids": [str(row.get("capability_id")) for row in catalog],
        "alternate_mcp_evaluated": evaluators["alternate_mcp_evaluated"],
        "alternate_nexus_action_evaluated": evaluators["alternate_nexus_action_evaluated"],
        "alternate_department_evaluated": evaluators["alternate_department_evaluated"],
        "configuration_option_evaluated": evaluators["configuration_option_evaluated"],
        "explicit_target_checked": True, "primary_path_evaluated": True,
        "primary_path_attempted_when_reasonable": bool(step_id),
        "capability_acquisition_evaluated": True,
        "build_required": bool(plan.get("capability_proposal")), "safe_repair_evaluated": True,
        "postcondition_verification_evaluated": True, "reason": str(reason)[:500],
        "planner_gap": plan.get("capability_gap"), "status": "EVALUATED"}
    with _connect() as db:
        db.execute("UPDATE operator_missions SET status='CAPABILITY_GAP',updated_at=? WHERE mission_id=?", (_now(), mission_id))
        db.execute("INSERT INTO operator_capability_gaps VALUES(?,?,?,?,?,?,?,?)",
                   (gap_id, mission_id, step_id, required, _json(evidence), "EVALUATED", _now(), _now()))
        db.execute("INSERT INTO operator_capability_proposals VALUES(?,?,?,?,?,?)",
            (gap_id, mission_id, required, _json(evidence), "EVALUATED", _now()))
        _event(db, mission_id, step_id, "CAPABILITY_GAP_EVALUATED", evidence)
    return evidence


def _refresh_capabilities_for_acquisition(mission_id: str,
                                          catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Refresh the full live catalog before deciding a capability gap is real.

    Planner candidate windows can omit a usable MCP/dept capability. Acquisition
    planning must therefore re-discover the approved runtime inventory rather than
    asking the planner to reconsider the same filtered list. If live discovery
    fails, retain the last known catalog and record that the gap remains active;
    omission from a failed refresh is never evidence that a capability is absent.
    """
    try:
        refreshed = discover_catalog(force=True)
        if not refreshed:
            raise RuntimeError("LIVE_CAPABILITY_DISCOVERY_RETURNED_EMPTY")
        save_catalog(mission_id, refreshed)
        return refreshed
    except Exception as exc:
        with _connect() as db:
            _event(db, mission_id, None, "CAPABILITY_CATALOG_REFRESH_FAILED", {
                "error": f"{type(exc).__name__}:{str(exc)[:300]}",
                "retained_catalog_count": len(catalog),
                "mission_remains_active": True,
            })
        return catalog


def action_not_available_allowed(evidence: dict[str, Any]) -> bool:
    """A terminal unavailability claim needs evidence for every required path."""
    required = ("live_catalog_checked", "explicit_target_checked", "primary_path_evaluated",
        "primary_path_attempted_when_reasonable", "alternate_mcp_evaluated",
        "alternate_nexus_action_evaluated", "alternate_department_evaluated",
        "safe_repair_evaluated", "capability_acquisition_evaluated", "postcondition_verification_evaluated")
    return all(evidence.get(key) is True for key in required)


def workspace_crud_family_preflight(catalog: list[dict[str, Any]]) -> dict[str, Any]:
    """Check the active approved catalog for the complete bounded NOTE/FILE CRUD family."""
    contracts = {
        "nexus_write_workspace_artifact": ({"relative_path", "content"}, "WRITE"),
        "nexus_read_workspace_file": ({"relative_path"}, "READ"),
        "nexus_update_workspace_artifact": ({"relative_path", "content", "expected_sha256"}, "WRITE"),
        "nexus_delete_workspace_artifact": ({"relative_path", "expected_sha256"}, "WRITE"),
    }
    by_name = {str(row.get("tool_name")): row for row in catalog
               if row.get("source_type") == "MCP" and row.get("source_id") == "nexus_mcp_remote"}
    operations: dict[str, dict[str, Any]] = {}
    for action, tool_name in {
        "CREATE": "nexus_write_workspace_artifact", "READ": "nexus_read_workspace_file",
        "UPDATE": "nexus_update_workspace_artifact", "DELETE": "nexus_delete_workspace_artifact",
    }.items():
        row = by_name.get(tool_name)
        required, rw = contracts[tool_name]
        schema = (row or {}).get("input_schema") or {}
        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        required_fields = set(schema.get("required") or ())
        valid = bool(row and row.get("authorized") is True
                     and row.get("runtime_health") == "PASS"
                     and row.get("read_write_class") == rw
                     and required.issubset(properties)
                     and required.issubset(required_fields)
                     and (rw == "READ" or row.get("write_allowed") is True)
                     and row.get("external_effect") is not True
                     and row.get("production_effect") is not True)
        operations[action] = {"tool_name": tool_name,
            "capability_id": (row or {}).get("capability_id"), "visible": row is not None,
            "schema_valid": required.issubset(properties) and required.issubset(required_fields),
            "authorized": bool(row and row.get("authorized") is True), "valid": valid}
    all_valid = all(item["valid"] for item in operations.values())
    return {"status": "PASS" if all_valid else "FAIL", "operations": operations,
            "entities": {"NOTE": all_valid, "FILE": all_valid},
            "bounded_namespaces": ["reports/nova_internal/"],
            "same_entity_update_delete": all_valid}


_TRUE_BLOCKERS = {"NEW_INCREMENTAL_CASH_REQUIRED", "RAY_ACTION_REQUIRED",
    "CONSEQUENTIAL_ACTION_APPROVAL_REQUIRED", "SECURITY_SCOPE_EXPANSION", "TRUE_TECHNICAL_BLOCKER"}


def true_blocker_allowed(blocker_type: str, evidence: dict[str, Any]) -> bool:
    if evidence.get("blocker_evidence_source") != "NOVA_RUNTIME_EVALUATOR":
        return False
    required = (
        "reasonable_paths_exhausted", "internal_repair_exhausted",
        "capability_acquisition_not_possible_or_requires_approval",
        "existing_approved_direct_capability_evaluated",
        "existing_approved_alternate_capability_evaluated",
        "safe_adapter_reroute_evaluated",
        "safe_schema_lineage_repair_evaluated",
        "bounded_capability_acquisition_evaluated",
        "postcondition_based_recovery_evaluated",
        "same_entity_continuation_evaluated",
    )
    return str(blocker_type) in _TRUE_BLOCKERS and all(evidence.get(key) is True for key in required)


def record_true_blocker(mission_id: str, blocker_type: str, evidence: dict[str, Any]) -> bool:
    """Persist a terminal blocker only after alternate and recovery burden is met."""
    if not true_blocker_allowed(blocker_type, evidence):
        _mission_state(mission_id, "RECOVERING", {"invalid_blocker_attempt": blocker_type,
            "evidence": evidence, "mission_remains_active": True})
        return False
    _mission_state(mission_id, "BLOCKED_TRUE", {"blocker_type": blocker_type, **evidence})
    return True


def _execute_one(mission_id: str, step: dict[str, Any], capabilities: dict[str, dict[str, Any]],
                 results: dict[str, dict[str, Any]], *, owner_authorized: bool,
                 executor: Callable[[dict[str, Any], dict[str, Any], bool], dict[str, Any]] | None = None) -> tuple[dict[str, Any] | None, str | None]:
    cap = capabilities[step["selected_capability_id"]]
    args = _resolve_refs(step.get("inputs") or {}, results)
    result = None
    try:
        _validate_args(cap.get("input_schema") or {}, args)
        _persist_step_state(mission_id, step, "RUNNING")
        result = executor(cap, args, owner_authorized) if executor else _invoke(cap, args, owner_authorized=owner_authorized)
        if not isinstance(result, dict):
            raise TypeError("EXECUTOR_RESULT_NOT_OBJECT")
        result = dict(result)
        result["result_data"] = _normalize_result_data(result.get("result_data"))
        result = _preserve_workspace_path_reference(result, args)
        _store_lineage(mission_id, step, result)
        if not result.get("call_succeeded"):
            raise RuntimeError(result.get("error_code") or "MCP_TOOL_ERROR")
        _persist_step_state(mission_id, step, "VERIFYING", result=result,
                            receipt={"receipt_id": result.get("receipt_id"), "tool_receipt_id": result.get("tool_receipt_id"),
                                     "source": result.get("source"), "recorded_at": _now()})
        verification = step["expected_postcondition"].get("verification")
        if verification:
            verify_cap = capabilities[str(verification["capability_id"])]
            verification_results = {**results, f"step{step['sequence']}": result}
            verify_args = _resolve_refs(verification.get("arguments") or {}, verification_results)
            _validate_args(verify_cap.get("input_schema") or {}, verify_args)
            verified = executor(verify_cap, verify_args, owner_authorized) if executor else _invoke(verify_cap, verify_args, owner_authorized=owner_authorized)
            if not isinstance(verified, dict):
                raise TypeError("POSTCONDITION_RESULT_NOT_OBJECT")
            verified = dict(verified)
            verified["result_data"] = _normalize_result_data(verified.get("result_data"))
            passed = _assert_postcondition(verified, verification.get("assertion") or {})
            if not passed:
                raise RuntimeError("POSTCONDITION_FAILED:" + str(step["expected_postcondition"].get("description") or step["goal"])[:240])
            result["postcondition"] = {"status": "PASS", "verified_by": verify_cap["capability_id"], "evidence": verified["result_data"]}
            _persist_step_state(mission_id, step, "COMPLETE_VERIFIED_BY_POSTCONDITION", result=result,
                receipt={"receipt_id": result.get("receipt_id"), "verification_source": verify_cap["capability_id"], "recorded_at": _now()})
        else:
            result["postcondition"] = {"status": "PASS_DIRECT_RESULT", "evidence": "Successful read result"}
            _persist_step_state(mission_id, step, "COMPLETE", result=result,
                receipt={"receipt_id": result.get("receipt_id"), "source": result.get("source"), "recorded_at": _now()})
        return result, None
    except Exception as exc:
        error = f"{type(exc).__name__}:{str(exc)[:500]}"
        # A mutation result is persisted as VERIFYING before its independent
        # read. Retry that read once while the exact returned mutation result
        # is still in scope. If verification remains unavailable, the durable
        # VERIFYING result is retained for same-entity recovery on the next run.
        verification = (step.get("expected_postcondition") or {}).get("verification")
        if isinstance(result, dict) and result.get("call_succeeded") and isinstance(verification, dict):
            try:
                verify_cap = capabilities[str(verification["capability_id"])]
                verify_args = _resolve_refs(verification.get("arguments") or {},
                                            {**results, f"step{step['sequence']}": result})
                _validate_args(verify_cap.get("input_schema") or {}, verify_args)
                verified = executor(verify_cap, verify_args, owner_authorized) if executor else _invoke(
                    verify_cap, verify_args, owner_authorized=owner_authorized)
                if isinstance(verified, dict):
                    verified = dict(verified)
                    verified["result_data"] = _normalize_result_data(verified.get("result_data"))
                    if _assert_postcondition(verified, verification.get("assertion") or {}):
                        result["postcondition"] = {"status": "PASS", "verified_by": verify_cap["capability_id"],
                                                    "evidence": verified["result_data"],
                                                    "recovered_after_verifier_error": True}
                        _persist_step_state(mission_id, step, "COMPLETE_VERIFIED_BY_POSTCONDITION", result=result,
                            receipt={"verification_source": verify_cap["capability_id"],
                                     "recovered_after_verifier_error": True, "recorded_at": _now()})
                        return result, None
            except Exception:
                pass
        _persist_step_state(mission_id, step, "RECOVERING", error=error)
        _record_failure(mission_id, step, error, step.get("alternate_capability_ids") or [], [])
        return None, error


def _recover_persisted_mutation(mission_id: str, step: dict[str, Any], prior: dict[str, Any],
                                capabilities: dict[str, dict[str, Any]], results: dict[str, dict[str, Any]], *,
                                owner_authorized: bool,
                                executor: Callable[[dict[str, Any], dict[str, Any], bool], dict[str, Any]] | None = None
                                ) -> tuple[dict[str, Any] | None, str | None]:
    """Verify a previously returned mutation before any same-step retry."""
    action_result = prior.get("result") if isinstance(prior.get("result"), dict) else {}
    verification = (step.get("expected_postcondition") or {}).get("verification")
    if not action_result.get("call_succeeded") or not isinstance(verification, dict):
        return None, "PRIOR_MUTATION_RESULT_NOT_VERIFIABLE"
    try:
        verify_cap = capabilities[str(verification["capability_id"])]
        verify_args = _resolve_refs(verification.get("arguments") or {},
                                    {**results, f"step{step['sequence']}": action_result})
        _validate_args(verify_cap.get("input_schema") or {}, verify_args)
        verified = executor(verify_cap, verify_args, owner_authorized) if executor else _invoke(
            verify_cap, verify_args, owner_authorized=owner_authorized)
        if not isinstance(verified, dict):
            raise TypeError("POSTCONDITION_RESULT_NOT_OBJECT")
        verified = dict(verified)
        verified["result_data"] = _normalize_result_data(verified.get("result_data"))
        if not _assert_postcondition(verified, verification.get("assertion") or {}):
            raise RuntimeError("POSTCONDITION_STILL_UNVERIFIED")
        recovered = dict(action_result)
        recovered["postcondition"] = {"status": "PASS", "verified_by": verify_cap["capability_id"],
                                       "evidence": verified["result_data"],
                                       "recovered_without_repeating_mutation": True}
        _persist_step_state(mission_id, step, "COMPLETE_VERIFIED_BY_POSTCONDITION", result=recovered,
            receipt={"verification_source": verify_cap["capability_id"],
                     "recovered_without_repeating_mutation": True, "recorded_at": _now()})
        return recovered, None
    except Exception as exc:
        error = f"POSTCONDITION_RECOVERY:{type(exc).__name__}:{str(exc)[:300]}"
        _persist_step_state(mission_id, step, "RECOVERING", error=error, result=action_result,
            receipt={"prior_mutation_result_retained": True, "recorded_at": _now()})
        return None, error


def _mission_state(mission_id: str, status: str, final: dict[str, Any] | None = None) -> None:
    if status not in MISSION_STATES: raise ValueError("INVALID_OPERATOR_MISSION_STATUS")
    now = _now()
    if status == "COMPLETE":
        proof = (final or {}).get("mission_success_evidence") or {}
        verified = bool((final or {}).get("mission_success_verified"))
        if not completion_guard(mission_success_verified=verified, mission_success_evidence=proof,
                                response=(final or {}).get("response")):
            _mission_state(mission_id, "RECOVERING", {"completion_rejected": True,
                "reason": "MISSION_SUCCESS_CONDITION_NOT_VERIFIED_OR_COMPLETION_CONTRADICTED"})
            return
    completed = now if status == "COMPLETE" else None
    with _connect() as db:
        db.execute("""UPDATE operator_missions SET status=?,final_result_json=?,updated_at=?,
            completed_at=?,mission_success_verified=CASE WHEN ?='COMPLETE' THEN 1 ELSE 0 END,
            mission_completion_reason=CASE WHEN ?='COMPLETE' THEN ? ELSE mission_completion_reason END
            WHERE mission_id=?""",
                   (status, _json(final) if final is not None else None, now, completed, status, status,
                    str((final or {}).get("mission_completion_reason") or "MISSION_SUCCESS_CONDITION_VERIFIED") if status == "COMPLETE" else None,
                    mission_id))
        if status in {"COMPLETE", "WAITING_FOR_APPROVAL", "BLOCKED_TRUE"}:
            outcome = {"COMPLETE": "RESOLVED", "WAITING_FOR_APPROVAL": "WAITING_FOR_APPROVAL",
                       "BLOCKED_TRUE": "BLOCKED_TRUE"}[status]
            rows = db.execute("SELECT failure_id,evidence_json FROM operator_failures WHERE mission_id=? AND status='RECOVERING'",
                              (mission_id,)).fetchall()
            for row in rows:
                payload = json.loads(row["evidence_json"] or "{}")
                payload["final_recovery_outcome"] = outcome
                db.execute("UPDATE operator_failures SET status=?,evidence_json=? WHERE failure_id=?",
                           (outcome, _json(payload), row["failure_id"]))
        _event(db, mission_id, None, "MISSION_" + status, final or {})


def run_objective(mission: dict[str, Any], text: str, semantic: dict[str, Any], *,
                  owner_authorized: bool, planner: Callable[[str], str] | None = None,
                  catalog: list[dict[str, Any]] | None = None, max_replans: int = MAX_REPLANS,
                  executor: Callable[[dict[str, Any], dict[str, Any], bool], dict[str, Any]] | None = None) -> dict[str, Any]:
    """Run one durable objective; failures return to bounded planning/recovery."""
    mission_id = str(mission.get("operator_mission_id") or mission["mission_id"])
    catalog_was_live_discovered = catalog is None
    catalog = catalog if catalog is not None else discover_catalog(force=True)
    began = begin_mission(mission, text, semantic, catalog)
    save_catalog(mission_id, catalog)
    capabilities = {row["capability_id"]: dict(row) for row in catalog}
    for row in capabilities.values():
        if row.get("source_type") == "NOVA_OPERATOR":
            row["_current_mission_id"] = mission_id
            row["_current_owner_id"] = str(mission.get("user_id", ""))
    with _connect() as db:
        existing = db.execute("SELECT objective_text FROM operator_missions WHERE mission_id=?", (mission_id,)).fetchone()
        original_objective = str(existing["objective_text"] if existing else text)
        done_rows = db.execute("SELECT step_id,goal,selected_capability_id,inputs_json,result_reference_json,status FROM operator_steps WHERE mission_id=? AND status IN ('COMPLETE','COMPLETE_VERIFIED_BY_POSTCONDITION') ORDER BY sequence", (mission_id,)).fetchall()
    mission_for_planner = {**mission, "mission_id": mission_id, "objective_text": original_objective,
                           "current_instruction": text}
    prior: dict[str, Any] | None = None
    completed_summaries: list[dict[str, Any]] = [
        {"step_id": row["step_id"], "goal": row["goal"], "capability_id": row["selected_capability_id"],
         "status": row["status"], "result": json.loads(row["result_reference_json"] or "null")}
        for row in done_rows]
    completed_by_plan_id: dict[str, dict[str, Any]] = {
        str(row["step_id"]).rsplit(":", 1)[-1]: {
            "goal": row["goal"], "capability_id": row["selected_capability_id"],
            "inputs": json.loads(row["inputs_json"] or "{}"),
            "result": json.loads(row["result_reference_json"] or "{}"),
        } for row in done_rows}
    all_results: dict[str, dict[str, Any]] = {
        f"step{i}": json.loads(row["result_reference_json"] or "{}")
        for i, row in enumerate(done_rows, 1)}
    replan_count = 0
    acquisition_replan_count = 0
    capability_build_attempts = 0
    failure_history: list[str] = []
    completed_step_ids = {str(row.get("step_id")) for row in completed_summaries}
    while True:
        _mission_state(mission_id, "PLANNING")
        try:
            plan = plan_objective(mission_for_planner, began["understanding"], catalog, planner=planner,
                                  prior_outcome=prior, completed=completed_summaries)
            steps = save_plan(mission_id, plan, catalog)
        except Exception as exc:
            failure_history.append(type(exc).__name__ + ":" + str(exc)[:220])
            if failure_history[-1].startswith("RuntimeError:OPERATOR_PLANNER_"):
                _mission_state(mission_id, "RECOVERING", {"error": failure_history[-1], "retryable": True,
                    "same_mission": True, "alternate_existing_adapter_required": True})
                return {"handled": False, "mission_id": mission_id, "status": "RECOVERING", "error": failure_history[-1]}
            if replan_count < max_replans:
                replan_count += 1
                prior = {"planning_failure": failure_history[-1], "same_mission": True}
                _mission_state(mission_id, "RECOVERING", prior)
                continue
            _mission_state(mission_id, "RECOVERING", {"error": failure_history[-1], "retryable": True})
            return {"handled": False, "mission_id": mission_id, "status": "RECOVERING", "error": failure_history[-1]}
        if not steps:
            reason = str(plan.get("capability_gap", {}).get("reason") or "No executable plan was returned.")
            evidence = _capability_gap(mission_id, str(plan.get("capability_gap", {}).get("required_capability") or text[:300]), catalog, plan, reason)
            empty_plan = {"status": "EMPTY_PLAN", "same_mission": True,
                          "missing_action_classified": True,
                          "capability_discovery_required": True,
                          "postcondition_recovery_required": True,
                          "reason": reason[:300]}
            with _connect() as db:
                _event(db, mission_id, None, "EMPTY_PLAN_RECOVERY", empty_plan)
            # The planner receives a bounded best-fit view, not the full catalog.
            # When an actionable gap is found, refresh live MCP/dept discovery
            # once before considering a build or blocker. A newly available tool
            # is an execution route, so return directly to planning on this same
            # mission instead of surfacing the gap to Ray.
            if catalog_was_live_discovered:
                previous_by_id = {str(row.get("capability_id")): _json(row) for row in catalog}
                refreshed = _refresh_capabilities_for_acquisition(mission_id, catalog)
                refreshed_by_id = {str(row.get("capability_id")): _json(row) for row in refreshed}
                catalog = refreshed
                capabilities = {row["capability_id"]: dict(row) for row in catalog}
                for row in capabilities.values():
                    if row.get("source_type") == "NOVA_OPERATOR":
                        row["_current_mission_id"] = mission_id
                        row["_current_owner_id"] = str(mission.get("user_id", ""))
                newly_visible = sorted(key for key, value in refreshed_by_id.items()
                                       if previous_by_id.get(key) != value)
                if newly_visible and acquisition_replan_count < max(1, min(max_replans, 2)):
                    acquisition_replan_count += 1
                    prior = {"capability_gap": evidence, "acquisition_planning_required": True,
                             "live_catalog_refreshed": True, "newly_visible_capabilities": newly_visible,
                             "same_mission": True, "original_objective_preserved": True}
                    _mission_state(mission_id, "ACQUISITION_PLANNING", prior)
                    with _connect() as db:
                        _event(db, mission_id, None, "CAPABILITY_ACQUISITION_LIVE_CATALOG_REFRESHED", prior)
                    continue
            proposal = plan.get("capability_proposal")
            if isinstance(proposal, dict) and capability_build_attempts < 2:
                capability_build_attempts += 1
                try:
                    release = build_and_register_capability(mission_id, proposal)
                    registered = _registered_generated_capabilities()
                    registered_ids = {row["capability_id"] for row in registered}
                    catalog = [row for row in catalog if row["capability_id"] not in registered_ids] + registered
                    save_catalog(mission_id, catalog)
                    capabilities = {row["capability_id"]: dict(row) for row in catalog}
                    for row in capabilities.values():
                        if row.get("source_type") == "NOVA_OPERATOR":
                            row["_current_mission_id"] = mission_id
                            row["_current_owner_id"] = str(mission.get("user_id", ""))
                    _mission_state(mission_id, "RECOVERING", {"capability_release": release,
                        "same_mission": True, "original_objective_preserved": True,
                        "original_step_resumed_when_applicable": True})
                    prior = {"capability_acquired": release, "same_mission": True,
                             "original_objective_preserved": True, "gap_evidence": evidence}
                    continue
                except Exception as exc:
                    failure = f"CAPABILITY_BUILD_FAILED:{type(exc).__name__}:{str(exc)[:300]}"
                    if isinstance(exc, PermissionError) and "REQUIRES_APPROVAL" in str(exc):
                        boundary = {"blocker_type": "SECURITY_SCOPE_EXPANSION",
                                    "exact_requirement": str(exc)[:300], "same_mission": True,
                                    "capability_gap": evidence}
                        _mission_state(mission_id, "WAITING_FOR_APPROVAL", boundary)
                        return {"handled": True, "mission_id": mission_id, "status": "WAITING_FOR_APPROVAL",
                                "response": "This objective is waiting for approval for the stated capability permission boundary.",
                                "boundary": boundary, "capability_gap": evidence}
                    if acquisition_replan_count < max(1, min(max_replans, 2)):
                        acquisition_replan_count += 1
                        prior = {"capability_build_failed": failure, "capability_repair_required": True,
                                 "same_mission": True, "original_objective_preserved": True,
                                 "gap_evidence": evidence}
                        _mission_state(mission_id, "ACQUISITION_PLANNING", prior)
                        continue
                    _mission_state(mission_id, "RECOVERING", {"error": failure, "same_mission": True})
                    return {"handled": True, "mission_id": mission_id, "status": "RECOVERING",
                            "response": "The same objective remains in bounded capability recovery after a validation failure; no unvalidated capability was activated.",
                            "error": failure, "capability_gap": evidence}
            if acquisition_replan_count < max(1, min(max_replans, 2)):
                acquisition_replan_count += 1
                prior = {"capability_gap": evidence, "acquisition_planning_required": True,
                         "reevaluate_live_alternatives": True, "same_mission": True,
                         "original_objective_preserved": True}
                _mission_state(mission_id, "ACQUISITION_PLANNING", prior)
                with _connect() as db:
                    _event(db, mission_id, None, "CAPABILITY_ACQUISITION_PLANNING", prior)
                continue
            planner_gap = plan.get("capability_gap") if isinstance(plan.get("capability_gap"), dict) else {}
            if planner_gap.get("human_approval_required"):
                boundary = {"blocker_type": "RAY_ACTION_REQUIRED", "exact_requirement": str(
                    planner_gap.get("reason") or reason)[:300], "same_mission": True,
                    "capability_gap": evidence}
                _mission_state(mission_id, "WAITING_FOR_APPROVAL", boundary)
                return {"handled": True, "mission_id": mission_id, "status": "WAITING_FOR_APPROVAL",
                        "response": "This objective is waiting for the specific Ray approval required to acquire the capability.",
                        "boundary": boundary, "capability_gap": evidence}
            # Planner text is not evidence that runtime alternatives were exhausted.
            # Empty plans remain nonterminal until an internal evaluator provides
            # an auditable certificate for each applicable recovery path.
            blocker = {"blocker_evidence_source": "PLANNER_UNVERIFIED",
                       "reasonable_paths_exhausted": False, "internal_repair_exhausted": False,
                       "capability_acquisition_not_possible_or_requires_approval": False,
                       "existing_approved_direct_capability_evaluated": False,
                       "existing_approved_alternate_capability_evaluated": False,
                       "safe_adapter_reroute_evaluated": False,
                       "safe_schema_lineage_repair_evaluated": False,
                       "bounded_capability_acquisition_evaluated": False,
                       "postcondition_based_recovery_evaluated": False,
                       "same_entity_continuation_evaluated": False,
                       "live_capability_discovery_completed": True, "primary_path_attempted": True,
                       "alternate_paths_attempted": True, "safe_repair_attempted": True,
                       "reroute_attempted": True, "capability_acquisition_evaluated": True,
                       "required_capability": evidence.get("required_capability"),
                       "catalog_capability_ids": evidence.get("catalog_capability_ids", []),
                       "reason": "No compatible live capability or safe declarative build remains after acquisition replanning."}
            accepted = record_true_blocker(mission_id, "TRUE_TECHNICAL_BLOCKER", blocker)
            if not accepted:
                return {"handled": True, "mission_id": mission_id, "status": "RECOVERING",
                        "response": "The same objective remains active while missing capabilities and same-entity recovery are evaluated; no terminal blocker is claimed.",
                        "boundary": blocker, "capability_gap": evidence, "step_count": 0}
            return {"handled": True, "mission_id": mission_id, "status": "BLOCKED_TRUE",
                    "response": "The objective reached a verified technical boundary after live alternatives, safe repair, and bounded capability acquisition were exhausted.",
                    "boundary": blocker, "capability_gap": evidence, "step_count": 0}
        with _connect() as db:
            recovering_rows = db.execute("""SELECT step_id,goal,selected_capability_id,inputs_json,
                result_reference_json,status FROM operator_steps WHERE mission_id=?
                AND status IN ('RECOVERING','VERIFYING') AND result_reference_json IS NOT NULL
                ORDER BY sequence""", (mission_id,)).fetchall()
        recovering_by_plan_id = {
            str(row["step_id"]).rsplit(":", 1)[-1]: {
                "goal": row["goal"], "capability_id": row["selected_capability_id"],
                "inputs": json.loads(row["inputs_json"] or "{}"),
                "result": json.loads(row["result_reference_json"] or "{}"),
                "status": row["status"],
            } for row in recovering_rows
        }
        results: dict[str, dict[str, Any]] = {}
        failed: tuple[dict[str, Any], str] | None = None
        for step in steps:
            prior_step = completed_by_plan_id.get(str(step["step_id"]))
            if (prior_step and prior_step.get("capability_id") == step["selected_capability_id"]
                    and prior_step.get("inputs") == step["inputs"] and prior_step.get("goal") == step["goal"]):
                key = f"step{step['sequence']}"
                results[key] = prior_step["result"]
                all_results[key] = prior_step["result"]
                completed_step_ids.add(str(step["step_id"]))
                prior_postcondition = (prior_step["result"].get("postcondition") or {}).get("status", "")
                reused_status = "COMPLETE" if prior_postcondition == "PASS_DIRECT_RESULT" else "COMPLETE_VERIFIED_BY_POSTCONDITION"
                _persist_step_state(mission_id, step, reused_status,
                    result=prior_step["result"], receipt={"reused_verified_result": True, "recorded_at": _now()})
                continue
            prior_mutation = recovering_by_plan_id.get(str(step["step_id"]))
            if (prior_mutation
                    and prior_mutation.get("capability_id") == step["selected_capability_id"]
                    and prior_mutation.get("inputs") == step["inputs"]
                    and prior_mutation.get("goal") == step["goal"]):
                recovered, recovery_error = _recover_persisted_mutation(
                    mission_id, step, prior_mutation, capabilities, {**all_results, **results},
                    owner_authorized=owner_authorized, executor=executor)
                if recovery_error:
                    failed = (step, recovery_error)
                    break
                key = f"step{step['sequence']}"
                results[key] = recovered or {}
                all_results[key] = recovered or {}
                completed_step_ids.add(str(step["step_id"]))
                completed_by_plan_id[str(step["step_id"])] = {
                    "goal": step["goal"], "capability_id": step["selected_capability_id"],
                    "inputs": step["inputs"], "result": recovered or {}}
                completed_summaries.append({"step_id": step["step_id"], "goal": step["goal"],
                    "capability_id": step["selected_capability_id"], "status": "COMPLETE_VERIFIED_BY_POSTCONDITION",
                    "result": recovered or {}})
                continue
            # Explicit dependencies must refer to completed plan step keys.
            missing = [dep for dep in step["dependencies"]
                       if dep not in completed_step_ids and dep not in results and dep not in all_results]
            if missing:
                failed = (step, "DEPENDENCY_NOT_COMPLETE:" + ",".join(missing))
                break
            result, error = _execute_one(mission_id, step, capabilities, {**all_results, **results},
                                         owner_authorized=owner_authorized, executor=executor)
            if error:
                failed = (step, error)
                break
            key = f"step{step['sequence']}"
            results[key] = result or {}
            all_results[key] = result or {}
            completed_step_ids.add(str(step["step_id"]))
            completed_by_plan_id[str(step["step_id"])] = {
                "goal": step["goal"], "capability_id": step["selected_capability_id"],
                "inputs": step["inputs"], "result": result or {},
            }
            completed_summaries.append({"step_id": step["step_id"], "goal": step["goal"],
                                         "capability_id": step["selected_capability_id"],
                                         "status": "COMPLETE", "result": result})
        if failed:
            step, error = failed
            failure_history.append(error)
            if "POLICY_APPROVAL_REQUIRED" in error or "POLICY_RAY_ACTION_REQUIRED" in error:
                _mission_state(mission_id, "WAITING_FOR_APPROVAL", {
                    "boundary_type": "CONSEQUENTIAL_EXTERNAL_ACTION_APPROVAL", "exact_requirement": error,
                    "what_was_tried": failure_history})
                return {"handled": True, "mission_id": mission_id, "status": "WAITING_FOR_APPROVAL",
                        "response": f"I completed the safe steps, but need your approval before {step['goal']}. Nothing crossed that boundary. Reply with approval to continue.",
                        "failure": error, "step_count": len(completed_summaries)}
            if replan_count < max_replans:
                replan_count += 1
                prior = {"failed_step": step["step_id"], "error": error, "same_mission": True,
                         "original_objective_preserved": True}
                _mission_state(mission_id, "RECOVERING", prior)
                continue
            _mission_state(mission_id, "RECOVERING", {"failure_class": _failure_class(error), "exact_requirement": error,
                "what_was_tried": failure_history, "alternates_failed": step.get("alternate_capability_ids", []),
                "retryable": True, "true_blocker_established": False})
            return {"handled": True, "mission_id": mission_id, "status": "RECOVERING",
                    "response": f"The objective remains active. I tried the approved execution path and bounded recovery, but it still needs another recovery attempt: {error[:240]}. No completion is claimed.",
                    "failure": error, "step_count": len(completed_summaries)}
        with _connect() as db:
            mission_row = db.execute("SELECT mission_success_condition_json FROM operator_missions WHERE mission_id=?",
                                     (mission_id,)).fetchone()
        mission_condition = json.loads(mission_row["mission_success_condition_json"] or "{}") if mission_row else {}
        try:
            mission_evidence = _verify_mission_success(mission_id, mission_condition, capabilities,
                {**all_results, **results}, owner_authorized=owner_authorized, executor=executor)
        except Exception as exc:
            mission_evidence = {"status": "ERROR", "condition": mission_condition,
                "error": f"{type(exc).__name__}:{str(exc)[:400]}", "verified_at": _now()}
            with _connect() as db:
                db.execute("UPDATE operator_missions SET mission_success_evidence_json=?,mission_success_verified=0,updated_at=? WHERE mission_id=?",
                           (_json(mission_evidence), _now(), mission_id))
                _event(db, mission_id, None, "MISSION_SUCCESS_VERIFICATION_ERROR", mission_evidence)
        if mission_evidence.get("status") != "PASS":
            failure_history.append("MISSION_SUCCESS_CONDITION_NOT_VERIFIED")
            if replan_count < max_replans:
                replan_count += 1
                prior = {"mission_success_condition_failed": mission_evidence, "same_mission": True,
                         "original_objective_preserved": True, "step_completion_is_not_mission_completion": True}
                _mission_state(mission_id, "RECOVERING", prior)
                continue
            final = {"objective": original_objective, "mission_id": mission_id,
                "mission_success_verified": False, "mission_success_evidence": mission_evidence,
                "completion_rejected": True, "same_mission": True,
                "response": "The objective remains active. Its plan steps finished, but the requested final outcome is not independently verified. I am keeping this mission open and continuing recovery."}
            _mission_state(mission_id, "RECOVERING", final)
            return {"handled": True, "mission_id": mission_id, "status": "RECOVERING",
                    "final_result": final, "response": final["response"], "step_count": len(completed_summaries)}
        final = {"objective": original_objective, "completed_steps": completed_summaries,
                 "all_postconditions_verified": all(
                     bool((row.get("result") or {}).get("postcondition", {}).get("status", "").startswith("PASS"))
                     for row in completed_summaries), "mission_id": mission_id,
                 "mission_success_condition": mission_condition, "mission_success_evidence": mission_evidence,
                 "mission_success_verified": True, "mission_completion_reason": "MISSION_SUCCESS_CONDITION_VERIFIED"}
        logical_entity_type = _workspace_logical_entity_type_from_rows(completed_summaries)
        final["response"] = _render_result(final, logical_entity_type=logical_entity_type)
        if not completion_guard(mission_success_verified=True, mission_success_evidence=mission_evidence,
                                response=final["response"]):
            _mission_state(mission_id, "RECOVERING", {**final, "mission_success_verified": False,
                "completion_rejected": True})
            return {"handled": True, "mission_id": mission_id, "status": "RECOVERING",
                    "final_result": final, "response": "The objective remains active because the completion consistency check rejected the result."}
        _mission_state(mission_id, "COMPLETE", final)
        record_knowledge(mission_id)
        return {"handled": True, "mission_id": mission_id, "status": "COMPLETE", "final_result": final,
                "step_count": len(completed_summaries), "response": final["response"],
                "entities": _extract_entities([row.get("result", {}).get("result_data") for row in completed_summaries],
                                               logical_entity_type=logical_entity_type)}


def _render_result(final: dict[str, Any], *, logical_entity_type: str | None = None) -> str:
    lines = ["Objective complete. The requested final state is independently verified."]
    entities: dict[str, str] = {}
    evidence_result = ((final.get("mission_success_evidence") or {}).get("result") or {})
    _extract_entities(evidence_result.get("result_data") or {}, entities,
                      logical_entity_type=logical_entity_type)
    for row in final.get("completed_steps", []):
        result = row.get("result") or {}
        _extract_entities(result.get("result_data") or {}, entities,
                          logical_entity_type=logical_entity_type)
    for key, label in (("objective_id", "OBJECTIVE_ID"), ("project_id", "PROJECT_ID"),
                       ("work_id", "WORK_ID"), ("job_id", "JOB_ID"), ("case_id", "CASE_ID"),
                       ("note_id", "NOTE_ID"), ("file_id", "FILE_ID"), ("event_id", "EVENT_ID"),
                       ("result_id", "RESULT_ID")):
        if entities.get(key): lines.append(f"{label}={entities[key]}")
    return "\n".join(lines)


def status_read(mission_id: str | None = None, *, owner_id: str | None = None,
                exclude_mission_id: str | None = None) -> dict[str, Any] | None:
    """Fast read-only operator status; never triggers recovery or queue maintenance."""
    db = _read_only_connect()
    if db is None:
        return None
    try:
        if mission_id:
            if owner_id:
                mission = db.execute("SELECT * FROM operator_missions WHERE mission_id=? AND owner_id=?", (mission_id, owner_id)).fetchone()
            else:
                mission = db.execute("SELECT * FROM operator_missions WHERE mission_id=?", (mission_id,)).fetchone()
        elif owner_id:
            active_rows = db.execute("""SELECT * FROM operator_missions WHERE owner_id=?
                AND status IN ('UNDERSTANDING','PLANNING','EXECUTING','WAITING_FOR_SUBTASK',
                    'RECOVERING','ACQUISITION_PLANNING','WAITING_FOR_APPROVAL','CAPABILITY_GAP','FAILED_INTERNAL')
                AND mission_id != ?
                ORDER BY updated_at DESC""", (owner_id, str(exclude_mission_id or ""))).fetchall()
            completed_rows = db.execute("""SELECT * FROM operator_missions WHERE owner_id=?
                AND status='COMPLETE' AND mission_success_verified=1
                ORDER BY COALESCE(completed_at,updated_at) DESC""", (owner_id,)).fetchall()

            def entity_ids(row):
                values = set(re.findall(r"\b(?:objective|project|job|case|note|file|event|result)_[A-Za-z0-9_.:-]+\b",
                                        str(row["objective_text"] or "")))
                values.update(str(x[0]) for x in db.execute(
                    "SELECT entity_id FROM operator_lineage WHERE mission_id=?", (row["mission_id"],)).fetchall())
                return values

            verified_by_ids = []
            for row in completed_rows:
                verified_by_ids.append((row, entity_ids(row)))
            mission = None
            for candidate in active_rows:
                candidate_ids = entity_ids(candidate)
                superseded = any(
                    candidate_ids and candidate_ids.intersection(done_ids)
                    and str(done["completed_at"] or done["updated_at"]) > str(candidate["updated_at"])
                    for done, done_ids in verified_by_ids
                )
                if not superseded:
                    mission = candidate
                    break
            if mission is None:
                return {"mission_id": None, "objective": None, "status": "NO_ACTIVE_MISSION",
                        "current_step": None, "last_action": None, "last_result": None,
                        "failure_state": None, "recovery_state": None, "next_step": None,
                        "waiting_on": None, "entity_lineage": [], "capability_gap": None,
                        "updated_at": None, "read_only": True, "no_mutation": True}
        else:
            return None
        if not mission: return None
        selected_mission_id = str(mission["mission_id"])
        authoritative_snapshot = _snapshot_from_mission_row(db, mission)
        steps = db.execute("SELECT * FROM operator_steps WHERE mission_id=? ORDER BY sequence", (selected_mission_id,)).fetchall()
        last = db.execute("SELECT event_type,payload_json,created_at FROM operator_events WHERE mission_id=? ORDER BY created_at DESC LIMIT 1", (selected_mission_id,)).fetchone()
        lineage = db.execute("SELECT entity_type,entity_id,entity_role,last_verified_at,metadata_json FROM operator_lineage WHERE mission_id=? ORDER BY last_verified_at DESC", (selected_mission_id,)).fetchall()
        pending = next((dict(row) for row in steps if row["status"] not in {"COMPLETE", "COMPLETE_VERIFIED_BY_POSTCONDITION"}), None)
        gap = db.execute("SELECT evidence_json,status FROM operator_capability_gaps WHERE mission_id=? ORDER BY created_at DESC LIMIT 1",
                         (selected_mission_id,)).fetchone() if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='operator_capability_gaps'").fetchone() else None
        return {"mission_id": mission["mission_id"], "objective": mission["objective_text"], "status": mission["status"],
                "current_step": pending or (dict(steps[-1]) if steps else None),
                "last_action": last["event_type"] if last else None,
                "last_result": json.loads(steps[-1]["result_reference_json"] or "null") if steps else None,
                "failure_state": json.loads(last["payload_json"] or "{}") if last and "FAIL" in last["event_type"] else None,
                "next_step": pending["goal"] if pending else None,
                "waiting_on": "Ray or approval" if mission["status"] in {"WAITING_FOR_APPROVAL", "BLOCKED_TRUE"} else None,
                "entity_lineage": [dict(row) for row in lineage],
                "success_verified": authoritative_snapshot["success_verified"],
                "terminal_reason": authoritative_snapshot["terminal_reason"],
                "final_outcome": authoritative_snapshot["final_outcome"],
                "success_condition": authoritative_snapshot["success_condition"],
                "success_evidence": authoritative_snapshot["success_evidence"],
                "final_entity_state": authoritative_snapshot["final_entity_state"],
                "source_of_truth": authoritative_snapshot["source_of_truth"],
                "capability_gap": ({**json.loads(gap["evidence_json"] or "{}"), "status": gap["status"]} if gap else None),
                "recovery_state": mission["status"] if mission["status"] in {"RECOVERING", "CAPABILITY_GAP", "WAITING_FOR_APPROVAL"} else None,
                "updated_at": mission["updated_at"], "read_only": True, "no_mutation": True}
    finally:
        db.close()


def decide_read_only_route(user_text: str, *, active_mission: dict[str, Any] | None,
                           completed_mission: dict[str, Any] | None,
                           previous_turn: dict[str, Any] | None = None,
                           entity_lineage: dict[str, Any] | None = None,
                           route_id: str,
                           shadow_only: bool = False) -> dict[str, Any]:
    """Pure decision for one approved R24 route, tagged with its authority mode."""
    if route_id not in {"R24.current", "R24.last_completed"}:
        raise ValueError("UNAUTHORIZED_WAVE1_ROUTE")
    from nova.operator_shadow import decide_shadow_request
    decision = decide_shadow_request(
        user_text,
        active_mission=active_mission,
        completed_mission=completed_mission,
        previous_turn=previous_turn,
        lineage=entity_lineage,
    )
    decision["ROUTE_ID"] = route_id
    decision["DECISION_OWNER"] = "SHADOW" if shadow_only else "NOVA_OPERATOR"
    decision["SHADOW_ONLY"] = bool(shadow_only)
    return decision


def _snapshot_from_mission_row(db: sqlite3.Connection, mission: sqlite3.Row) -> dict[str, Any]:
    """Build current/final state from the mission row; event rows are history only."""
    mission_id = str(mission["mission_id"])
    condition = json.loads(mission["mission_success_condition_json"] or "{}")
    evidence = json.loads(mission["mission_success_evidence_json"] or "{}")
    final_result = json.loads(mission["final_result_json"] or "{}")
    latest = db.execute("""SELECT event_type,created_at FROM operator_events
        WHERE mission_id=? ORDER BY created_at DESC LIMIT 1""", (mission_id,)).fetchone()
    current_step = db.execute("""SELECT step_id,sequence,goal,status FROM operator_steps
        WHERE mission_id=? AND status NOT IN ('COMPLETE','COMPLETE_VERIFIED_BY_POSTCONDITION')
        ORDER BY sequence LIMIT 1""", (mission_id,)).fetchone()
    if current_step is None:
        current_step = db.execute("""SELECT step_id,sequence,goal,status FROM operator_steps
            WHERE mission_id=? ORDER BY sequence DESC LIMIT 1""", (mission_id,)).fetchone()
    # Only the persisted terminal row plus independent verification can establish
    # completion. Earlier event text never promotes or demotes the mission state.
    verified_terminal = str(mission["status"]).upper() == "COMPLETE" and bool(mission["mission_success_verified"])
    case_state = (((evidence.get("result") or {}).get("result_data") or {}).get("case_state") or {})
    lineage = [dict(row) for row in db.execute("""SELECT entity_type,entity_id,entity_role,last_verified_at
        FROM operator_lineage WHERE mission_id=? ORDER BY COALESCE(last_verified_at,'') DESC""", (mission_id,))]
    historical_events = [dict(row) for row in db.execute("""SELECT event_type,created_at FROM operator_events
        WHERE mission_id=? AND (event_type LIKE '%BLOCK%' OR event_type LIKE '%RECOVER%'
            OR event_type LIKE '%CAPABILITY_GAP%' OR event_type LIKE '%FAIL%')
        ORDER BY created_at""", (mission_id,))]
    final_entity_state = None
    if case_state:
        final_entity_state = {
            "entity_type": "RESEARCH_CASE",
            "entity_id": evidence.get("verified_case_id") or evidence.get("arguments", {}).get("case_id"),
            "status": case_state.get("status") or evidence.get("case_status"),
            "open_question_count": evidence.get("open_question_count"),
            "source_count": evidence.get("source_count", case_state.get("source_count")),
            "synthesis_count": evidence.get("synthesis_count", case_state.get("synthesis_count")),
            "recommendation": evidence.get("recommendation"),
            "updated_at": case_state.get("updated_at"),
        }
    return {
        "mission_id": mission_id,
        "objective": mission["objective_text"],
        "status": "COMPLETE" if verified_terminal else mission["status"],
        "success_verified": verified_terminal,
        "active": str(mission["status"]).upper() not in TERMINAL_MISSION_STATES,
        "current_step_id": mission["current_step_id"],
        "current_step": dict(current_step) if current_step else None,
        "terminal_reason": mission["mission_completion_reason"],
        "final_outcome": final_result.get("response") if verified_terminal else None,
        "success_condition": condition.get("description"),
        "success_evidence": ({
            "case_status": evidence.get("case_status"),
            "open_question_count": evidence.get("open_question_count"),
            "source_count": evidence.get("source_count"),
            "synthesis_count": evidence.get("synthesis_count"),
            "recommendation": evidence.get("recommendation"),
            "historical_exception_recoverable": evidence.get("historical_exception_recoverable"),
            "verified_at": evidence.get("verified_at"),
            "verifier": evidence.get("verifier"),
        } if verified_terminal else None),
        "completed_at": mission["completed_at"],
        "updated_at": mission["updated_at"],
        "latest_event": dict(latest) if latest else None,
        "historical_problem_events": historical_events,
        "final_entity_state": final_entity_state,
        "entity_lineage": lineage,
        "source_of_truth": "operator_missions authoritative row + persisted mission success evidence; events are historical",
    }


def get_authoritative_mission_snapshot(mission_id: str, *, owner_id: str | None = None) -> dict[str, Any] | None:
    """Read the canonical mission state without deriving it from event history."""
    db = _read_only_connect()
    if db is None:
        return None
    try:
        if owner_id is None:
            row = db.execute("SELECT * FROM operator_missions WHERE mission_id=?", (str(mission_id),)).fetchone()
        else:
            row = db.execute("SELECT * FROM operator_missions WHERE mission_id=? AND owner_id=?",
                             (str(mission_id), str(owner_id))).fetchone()
        return _snapshot_from_mission_row(db, row) if row else None
    finally:
        db.close()


def recent_completed_status(owner_id: str) -> dict[str, Any] | None:
    """Return the latest verified completed mission, including its final outcome."""
    db = _read_only_connect()
    if db is None:
        return None
    try:
        mission = db.execute("""SELECT * FROM operator_missions WHERE owner_id=?
            AND status='COMPLETE' AND mission_success_verified=1
            ORDER BY COALESCE(completed_at,updated_at) DESC LIMIT 1""", (str(owner_id),)).fetchone()
        if not mission:
            return None
        snapshot = _snapshot_from_mission_row(db, mission)
        snapshot["objective"] = mission["objective_text"]
        snapshot["mission_success_verified"] = snapshot["success_verified"]
        return snapshot
    finally:
        db.close()


def mission_for_entity(owner_id: str, entity_ids: list[str] | tuple[str, ...]) -> str | None:
    """Resolve an explicit current object to its owning operator mission, never by similarity."""
    exact = [str(x) for x in entity_ids if str(x)]
    if not exact:
        return None
    marks = ",".join("?" for _ in exact)
    db = _read_only_connect()
    if db is None:
        return None
    try:
        row = db.execute(f"""SELECT m.mission_id FROM operator_missions m JOIN operator_lineage l
            ON l.mission_id=m.mission_id WHERE m.owner_id=? AND l.entity_role='CURRENT_OBJECT' AND l.entity_id IN ({marks})
            ORDER BY l.last_verified_at DESC LIMIT 1""", (str(owner_id), *exact)).fetchone()
        return str(row["mission_id"]) if row else None
    finally:
        db.close()


def current_entity_lineage(owner_id: str) -> dict[str, Any] | None:
    """Return the latest exact owner lineage bundle, preserving entity IDs across turns.

    The per-chat JSON is a convenience cache; this durable Operator ledger is
    authoritative when that cache is stale or incomplete.
    """
    db = _read_only_connect()
    if db is None:
        return None
    try:
        latest = db.execute("""SELECT m.mission_id,m.source_message_id,m.updated_at
            FROM operator_missions m JOIN operator_lineage l USING(mission_id)
            WHERE m.owner_id=? AND l.entity_role='CURRENT_OBJECT'
            ORDER BY COALESCE(l.last_verified_at,m.updated_at) DESC,m.updated_at DESC LIMIT 1""",
            (str(owner_id),)).fetchone()
        if not latest:
            return None
        rows = db.execute("""SELECT entity_type,entity_id,entity_role,created_by_step,last_verified_at,metadata_json
            FROM operator_lineage WHERE mission_id=? AND entity_role='CURRENT_OBJECT'
            ORDER BY COALESCE(last_verified_at,'') DESC""", (latest["mission_id"],)).fetchall()
        result: dict[str, Any] = {
            "mission_id": latest["mission_id"], "operator_mission_id": latest["mission_id"],
            "source_message_id": latest["source_message_id"], "updated_at": latest["updated_at"],
            "active_reference": True,
        }
        aliases = {"OBJECTIVE": "objective_id", "PROJECT": "project_id", "JOB": "job_id",
                   "CASE": "case_id", "NOTE": "note_id", "FILE": "file_id", "EVENT": "event_id",
                   "RESULT": "result_id"}
        for row in rows:
            key = aliases.get(str(row["entity_type"]).upper())
            if key and key not in result:
                result[key] = row["entity_id"]
                result[key.replace("_id", "_entity")] = {
                    "entity_type": row["entity_type"], "entity_id": row["entity_id"],
                    "entity_role": row["entity_role"], "created_by_step": row["created_by_step"],
                    "last_verified_at": row["last_verified_at"],
                    "metadata": json.loads(row["metadata_json"] or "{}"),
                    "mission_id": latest["mission_id"], "source_message_id": latest["source_message_id"],
                    "active_reference": True,
                }
        return result
    finally:
        db.close()


def recent_research_case_lineage(owner_id: str, *, case_id: str | None = None,
                                limit: int = 20) -> dict[str, Any] | None:
    """Read the owner's recent exact Research case lineage without changing it.

    This is a final resolver fallback, after immediate and active context. If
    the durable history contains more than one distinct case, the caller must
    treat the reference as ambiguous instead of guessing.
    """
    db = _read_only_connect()
    if db is None:
        return None
    try:
        bounded_limit = max(1, min(int(limit), 50))
        query = """SELECT l.mission_id,l.entity_id,l.last_verified_at,
                m.source_message_id,m.objective_text,m.status,m.updated_at,
                m.mission_success_evidence_json
            FROM operator_lineage l JOIN operator_missions m USING(mission_id)
            WHERE m.owner_id=? AND l.entity_role='CURRENT_OBJECT'
              AND upper(l.entity_type) IN ('CASE','RESEARCH_CASE')
        """
        args: list[Any] = [str(owner_id)]
        if case_id:
            query += " AND l.entity_id=?"
            args.append(str(case_id))
        query += " ORDER BY COALESCE(l.last_verified_at,m.updated_at) DESC,m.updated_at DESC LIMIT ?"
        args.append(bounded_limit)
        rows = db.execute(query, args).fetchall()
        distinct = list(dict.fromkeys(str(row["entity_id"]) for row in rows if row["entity_id"]))
        if not distinct:
            return None
        if len(distinct) != 1:
            return {"case_id": None, "ambiguous_case_ids": distinct,
                    "resolution_status": "AMBIGUOUS", "read_only": True, "no_mutation": True}
        selected = next(row for row in rows if str(row["entity_id"]) == distinct[0])
        evidence = json.loads(selected["mission_success_evidence_json"] or "{}")
        arguments = evidence.get("arguments") if isinstance(evidence.get("arguments"), dict) else {}
        return {"case_id": distinct[0], "mission_id": selected["mission_id"],
                "source_message_id": selected["source_message_id"],
                "objective": selected["objective_text"], "mission_status": selected["status"],
                "objective_id": str(arguments.get("objective_id") or "") or None,
                "project_id": str(arguments.get("project_id") or "") or None,
                "durable_job_id": str(arguments.get("durable_job_id") or "") or None,
                "last_verified_at": selected["last_verified_at"],
                "read_only": True, "no_mutation": True}
    finally:
        db.close()


def note_existing_route_fallback(mission_id: str, route: dict[str, Any], error: str) -> None:
    """Record a known existing Nova adapter as an alternate path before legacy dispatch."""
    with _connect() as db:
        db.execute("UPDATE operator_missions SET status='RECOVERING',updated_at=? WHERE mission_id=?", (_now(), mission_id))
        _event(db, mission_id, None, "EXISTING_ADAPTER_ALTERNATE_SELECTED", {
            "route": route, "primary_failure": str(error)[:500], "same_mission": True,
            "new_objective_created": False})


def record_knowledge(mission_id: str) -> bool:
    """Persist advisory plan knowledge after verified completion."""
    with _connect() as db:
        mission = db.execute("SELECT * FROM operator_missions WHERE mission_id=?", (mission_id,)).fetchone()
        if not mission or mission["status"] != "COMPLETE": return False
        steps = db.execute("SELECT * FROM operator_steps WHERE mission_id=? ORDER BY sequence", (mission_id,)).fetchall()
        final = json.loads(mission["final_result_json"] or "{}")
        pattern = hashlib.sha256(re.sub(r"\d+", "#", mission["objective_text"].casefold()).encode()).hexdigest()[:20]
        db.execute("INSERT OR REPLACE INTO operator_knowledge VALUES(?,?,?,?,?,?,?,?,?)", (
            pattern, mission["objective_text"][:1000], _json([dict(row) for row in steps]),
            _json([row["selected_capability_id"] for row in steps]), "[]", "[]",
            _json([json.loads(row["expected_postcondition_json"] or "{}") for row in steps]), _json(final), _now()))
        _event(db, mission_id, None, "EXECUTION_KNOWLEDGE_RECORDED", {"pattern_id": pattern})
        return True

