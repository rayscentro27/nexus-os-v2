#!/usr/bin/env python3
"""Build a bounded, secret-safe local knowledge index for Hermes."""
from __future__ import annotations
import json, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
NOW = datetime.now(timezone.utc)
MAX_BYTES = 300_000
MAX_ITEMS = 400
SKIP_PARTS = {"node_modules", "dist", ".git", ".netlify", "coverage"}
SECRET_NAME = re.compile(r"(?i)(^|/|\\)\.env($|\.)|secret|credential|private[_-]?key")
SECRET_VALUE = re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.|(sk|pk|sb)_(live|test|secret)_[A-Za-z0-9_-]{12,}|bearer\s+[A-Za-z0-9._-]{12,}", re.I)

def source_type(path: Path) -> str:
    name = path.name.lower(); text = str(path).lower()
    if "operations" in name or "process_inventory" in name or "scheduler_inventory" in name: return "operations"
    if "cli" in name: return "cli_registry"
    if "audit" in name or "reality" in name: return "audit"
    if "seed" in name: return "seed_report"
    if "research" in text or "youtube" in text: return "research"
    if "memory" in name or "event" in name or "activity" in name: return "memory"
    if "task" in name or "review" in name or "approval" in name: return "task"
    if path.suffix.lower() in {".md", ".json"} and "reports" in path.parts: return "report"
    return "repo_doc"

def summarize(path: Path, raw: str) -> tuple[str, str]:
    if SECRET_VALUE.search(raw): return "", "secret_pattern"
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                for key in ["hermes_readable_summary", "summary", "status", "result", "principle"]:
                    value = data.get(key)
                    if isinstance(value, (str, int, float, bool)): return str(value)[:420], "ok"
                return f"Structured report with keys: {', '.join(list(data)[:10])}.", "ok"
            return f"Structured list with {len(data)} items.", "ok"
        except Exception: return "Invalid or nonstandard JSON report.", "ok"
    lines = [re.sub(r"^[#>*\-\s]+", "", x).strip() for x in raw.splitlines() if x.strip()]
    safe = [x for x in lines if not SECRET_VALUE.search(x) and not re.search(r"(?i)(api key|service role).{0,10}[:=]", x)]
    return " ".join(safe[:3])[:420] or "Readable report with no concise summary.", "ok"

def candidates():
    paths = []
    for pattern in ["reports/**/*.md", "reports/**/*.json", "README.md", "docs/**/*.md", "package.json"]:
        paths.extend(ROOT.glob(pattern))
    unique=set(paths)
    def rank(path):
        text=str(path).lower()
        priority=0 if any(x in text for x in ["nexus_operations", "hermes_operations", "live_seed", "reality", "ray_review", "youtube", "cli_command"]) else 1
        return (priority, -path.stat().st_mtime if path.exists() else 0, str(path))
    return sorted(unique,key=rank)

def main():
    items=[]; skipped=[]
    for path in candidates():
        if len(items) >= MAX_ITEMS:
            skipped.append({"path":"remaining_candidates","reason":f"bounded_to_{MAX_ITEMS}_items"}); break
        rel=path.relative_to(ROOT)
        if any(part in SKIP_PARTS for part in rel.parts) or SECRET_NAME.search(str(rel)) or path.name.startswith("hermes_second_brain_index_latest"): continue
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            skipped.append({"path":str(rel),"reason":"missing_or_too_large"}); continue
        raw=path.read_text(errors="ignore")
        summary, reason=summarize(path,raw)
        if reason != "ok": skipped.append({"path":str(rel),"reason":reason}); continue
        updated=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc)
        freshness="fresh" if NOW-updated < timedelta(days=7) else "stale"
        st=source_type(path)
        tags=sorted(set(re.findall(r"(?i)\b(supabase|hermes|youtube|research|approval|scheduler|trading|revenue|client|operations|cli)\b", str(rel)+" "+summary.lower())))
        items.append({"source_id":re.sub(r"[^a-z0-9]+","-",str(rel).lower()).strip("-"),"source_type":st,
          "title":path.stem.replace("_"," ").replace("-"," ").title(),"summary":summary,"path":str(rel),
          "created_at":updated.isoformat(),"updated_at":updated.isoformat(),"freshness":freshness,
          "confidence":"high" if st in {"operations","audit","cli_registry","seed_report"} else "medium","tags":tags,
          "related_module":st,"safe_next_action":"Open the source and verify its timestamp before relying on it.",
          "approval_required_action":"Any write, execution, send, deploy, seed, publish, charge, dispute, or trade.","hermes_readable":True})
    payload={"generated_at":NOW.isoformat(),"item_count":len(items),"max_source_bytes":MAX_BYTES,"max_items":MAX_ITEMS,"items":items,"skipped":skipped,
      "limitations":["Local build-time index","Files with secret-like values or oversized content are skipped","No semantic embedding or live model used"]}
    (REPORTS/"hermes_second_brain_index_latest.json").write_text(json.dumps(payload,indent=2)+"\n")
    by_type={}
    for x in items: by_type[x["source_type"]]=by_type.get(x["source_type"],0)+1
    md="# Hermes Second Brain Index\n\nGenerated: %s\n\n- Indexed: %s bounded safe sources\n- Skipped: %s\n- No secrets, `.env`, `node_modules`, or `dist` indexed\n\n## Source types\n\n%s\n\n## Fresh operations sources\n\n%s\n"%(NOW.isoformat(),len(items),len(skipped),"\n".join(f"- {k}: {v}" for k,v in sorted(by_type.items())),"\n".join(f"- [{x['title']}]({x['path']}): {x['summary'][:180]}" for x in items if x["source_type"]=="operations") or "- None")
    (REPORTS/"hermes_second_brain_index_latest.md").write_text(md)
    print(json.dumps({"ok":True,"indexed":len(items),"skipped":len(skipped),"secrets_indexed":False}))

if __name__=="__main__": main()
