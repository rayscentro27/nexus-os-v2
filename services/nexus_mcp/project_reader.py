"""Read-only Nexus project context for Nova/Hermes (generic, any business-loop project).

Authoritative source: the business-loop project store under
``$NEXUS_REPO_ROOT/data/governed/business_loop`` (append-only JSONL; latest
revision wins). Approval-card status is read from the hash-bound request files
the distribution publisher itself uses. Nothing here writes, resumes, approves,
or publishes.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ID_RE = re.compile(r"^proj_[0-9a-z]{6,40}$")


def _repo() -> Path:
    return Path(os.environ.get("NEXUS_REPO_ROOT") or Path(__file__).resolve().parents[2])


def _store() -> Path:
    return Path(os.environ.get("NEXUS_BUSINESS_LOOP_DATA_DIR") or _repo() / "data/governed/business_loop")


def _rows(name: str) -> list[dict]:
    p = _store() / f"{name}.jsonl"
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def _latest(name: str, key: str) -> dict[str, dict]:
    cur: dict[str, dict] = {}
    for r in _rows(name):
        if r.get(key):
            cur[r[key]] = r
    return cur


def _card_status(approval_request_id: str) -> dict:
    for path in sorted((_repo() / "dist/creative").glob("*_approval_request.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if data.get("approval_request_id") == approval_request_id:
            return {"card_status": data.get("status"), "superseded_by": data.get("superseded_by"), "platform": data.get("platform"),
                    "target_url": data.get("target_url"), "approved": bool(data.get("approval_id"))}
    return {"card_status": "CARD_NOT_FOUND"}


def _envelope(tool: str, status: str, data: dict, items: list | None = None, error: str | None = None) -> dict:
    return {"tool_name": tool, "status": status, "data": data, "items": items or [],
            "metadata": {"read_only": True, "canonical": True, "source": "business_loop_project_store", "freshness": "live",
                         "currentness": "CURRENT" if status in {"OK", "EMPTY"} else "UNKNOWN", "item_count": len(items or []),
                         "read_at": datetime.now(timezone.utc).isoformat()},
            "error": error}


def list_projects(query: str = "") -> dict:
    projects = list(_latest("projects", "project_id").values())
    q = (query or "").strip().casefold()
    items = [{"project_id": p["project_id"], "opportunity_name": p.get("opportunity_name"), "venture_id": p.get("venture_id"),
              "status": p.get("status"), "current_department": p.get("current_department"), "updated_at": p.get("updated_at")}
             for p in projects
             if not q or all(w in json.dumps([p.get("opportunity_name"), p.get("venture_id"), p.get("opportunity_id"), p["project_id"]]).casefold()
                             for w in q.split())]
    return _envelope("nexus_get_projects", "OK" if items else "EMPTY", {"projects": items, "query": query}, items)


def get_project(project_id: str) -> dict:
    pid = (project_id or "").strip()
    if not PROJECT_ID_RE.match(pid):
        return _envelope("nexus_get_project", "INVALID_ARGUMENT", {}, error="project_id must look like proj_<id>")
    p = _latest("projects", "project_id").get(pid)
    if not p:
        known = sorted(_latest("projects", "project_id"))
        return _envelope("nexus_get_project", "NOT_FOUND", {"project_id": pid, "known_project_ids": known[:20]}, error="project_not_found")
    items = [w for w in _latest("work_items", "work_item_id").values() if w.get("project_id") == pid]
    handoffs = [h for h in _rows("handoffs") if h.get("project_id") == pid]
    creative = sorted((w for w in items if w.get("department") == "CREATIVE" and w.get("status") == "DONE"), key=lambda w: w.get("updated_at") or "")
    creative_assets = []
    for w in creative:
        out = w.get("outputs") or {}
        creative_assets += [{"path": a.get("path"), "size": a.get("size"), "hook_id": a.get("hook_id")} for a in out.get("ASSETS", [])]
        if out.get("asset"):
            creative_assets.append({"path": out.get("asset")})
    approvals = []
    for a in p.get("approvals_required") or []:
        row = {k: a.get(k) for k in ("approval_request_id", "approval_id", "approval_kind", "platform", "stage", "status", "owner_command", "then", "file")}
        if a.get("approval_request_id"):
            row.update(_card_status(a["approval_request_id"]))
        approvals.append({k: v for k, v in row.items() if v is not None})
    offer = p.get("commerce_offer") or {}
    analysis = p.get("last_conversion_analysis") or p.get("last_analysis") or {}
    waiting = [a for a in approvals if a.get("card_status") != "SUPERSEDED"]
    data = {
        "project_id": pid, "venture_id": p.get("venture_id"), "opportunity_id": p.get("opportunity_id"), "opportunity_name": p.get("opportunity_name"),
        "status": p.get("status"), "cycle": p.get("cycle"), "current_department": p.get("current_department"), "current_stage": p.get("current_stage"),
        "next_action": p.get("next_action"), "blockers": p.get("blockers") or [], "approvals_waiting": waiting, "approvals_all": approvals,
        "commerce_offer": {k: offer.get(k) for k in ("PRODUCT_NAME", "PRICE", "BASE_COST", "SHIPPING_ESTIMATE", "GROSS_MARGIN_ESTIMATE", "CHECKOUT_STATUS",
                                                     "PUBLICATION_STATUS", "SALES_STATUS", "PRINTIFY_PRODUCT_ID", "STOREFRONT_URL") if k in offer},
        "metrics": p.get("metrics") or {}, "next_best_action": analysis.get("NEXT_BEST_ACTION"),
        "creative_assets": creative_assets[-8:], "cost_ledger": p.get("cost_ledger"),
        "work_items": {"total": len(items), "by_status": {s: sum(1 for w in items if w.get("status") == s) for s in sorted({str(w.get("status")) for w in items})}},
        "recent_handoffs": [{"transition": h.get("transition"), "summary": (h.get("SUMMARY") or "")[:160], "at": h.get("TIMESTAMP")} for h in handoffs[-6:]],
        "updated_at": p.get("updated_at"),
    }
    return _envelope("nexus_get_project", "OK", data, waiting)


def _ledger_decisions(request_id: str) -> list[dict]:
    path = _repo() / "data/governed/approvals.jsonl"
    if not path.exists() or not request_id:
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if request_id in line:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            out.append({"approval_id": r.get("id"), "status": r.get("status"), "resolved_by": r.get("resolved_by"), "resolved_at": r.get("resolved_at")})
    return out


def _file_status(rel: str) -> dict:
    try:
        p = (_repo() / rel).resolve()
        if not str(p).startswith(str(_repo().resolve())):
            return {"artifact_status": "OUTSIDE_REPO_REFUSED"}
        d = json.loads(p.read_text(encoding="utf-8"))
        return {"artifact_status": d.get("status"), "live_financial_activation_performed": d.get("live_financial_activation_performed")}
    except (OSError, ValueError):
        return {"artifact_status": "ARTIFACT_NOT_FOUND"}


def get_project_approvals(project_id: str) -> dict:
    """Approvals linked to ONE project, each with its live artifact status and any recorded decision."""
    pid = (project_id or "").strip()
    if not PROJECT_ID_RE.match(pid):
        return _envelope("nexus_get_project_approvals", "INVALID_ARGUMENT", {}, error="project_id must look like proj_<id>")
    p = _latest("projects", "project_id").get(pid)
    if not p:
        return _envelope("nexus_get_project_approvals", "NOT_FOUND", {"project_id": pid}, error="project_not_found")
    rows = []
    for a in p.get("approvals_required") or []:
        row = {k: a.get(k) for k in ("approval_request_id", "approval_id", "approval_kind", "platform", "stage", "owner_command", "then", "file", "supersedes")}
        if a.get("approval_request_id"):
            row.update(_card_status(a["approval_request_id"]))
            decisions = _ledger_decisions(a["approval_request_id"])
            row["decisions"] = decisions
            status = row.get("card_status")
        else:
            row.update(_file_status(a["file"]) if a.get("file") else {"artifact_status": a.get("status")})
            decisions = _ledger_decisions(a.get("approval_id") or "")
            row["decisions"] = decisions
            status = row.get("artifact_status")
        latest = decisions[-1]["status"] if decisions else None
        if status == "SUPERSEDED":
            state = "SUPERSEDED"
        elif latest in ("approved", "consumed"):
            state = latest.upper()
        elif status in ("WAITING_FOR_RAY_APPROVAL", "pending"):
            state = "WAITING_FOR_RAY"
        else:
            state = str(status or "UNKNOWN")
        row["state"] = state
        rows.append({k: v for k, v in row.items() if v not in (None, [], "")})
    waiting = [r for r in rows if r["state"] == "WAITING_FOR_RAY"]
    data = {"project_id": pid, "opportunity_name": p.get("opportunity_name"), "waiting_count": len(waiting), "waiting": waiting,
            "all_project_approvals": rows, "source": "project.approvals_required + approval artifacts + governed approvals ledger",
            "note": "Read-only. Approving or publishing requires the owner command shown; Nova cannot approve."}
    return _envelope("nexus_get_project_approvals", "OK" if rows else "EMPTY", data, waiting)
