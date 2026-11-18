"""Local searchable portfolio memory; standard library only, no network/secrets."""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone

def save(record: dict, path: str | Path) -> None:
    required={"project_id","version","score","outputs","weaknesses","missing_components","improvement_targets","research_triggers","next_stage"}
    if required-set(record): raise ValueError("PORTFOLIO_RECORD_FIELDS_MISSING")
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    row={**record,"updated_at":datetime.now(timezone.utc).isoformat()}
    existing=[]
    if p.exists(): existing=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    existing=[x for x in existing if not (x.get("project_id")==row["project_id"] and x.get("version")==row["version"])]
    existing.append(row); tmp=p.with_suffix(p.suffix+".tmp"); tmp.write_text("".join(json.dumps(x,sort_keys=True)+chr(10) for x in existing)); tmp.replace(p)

def search(query: str, path: str | Path) -> list[dict]:
    terms=[x.casefold() for x in query.split() if x]
    if not terms: return []
    rows=[json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    def score(row):
        text=json.dumps(row,sort_keys=True).casefold(); return sum(t in text for t in terms)
    return sorted((r for r in rows if score(r)),key=score,reverse=True)

def match_research_and_reopen(new_finding: str, path: str | Path) -> list[dict]:
    """Return completed projects whose saved research triggers match a new finding.

    This creates explicit improvement candidates; it does not promote projects,
    alter approvals, or schedule work without a workflow assignment.
    """
    tokens={x.casefold() for x in new_finding.split() if len(x)>2}
    candidates=[]
    for row in search(new_finding,path):
        triggers=" ".join(row.get("research_triggers",[])).casefold()
        matched=sorted(t for t in tokens if t in triggers)
        if matched: candidates.append({"project_id":row["project_id"],"version":row["version"],
            "matched_triggers":matched,"status":"REOPEN_CANDIDATE","authority_change":False})
    return candidates
