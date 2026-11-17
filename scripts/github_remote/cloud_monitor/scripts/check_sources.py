#!/usr/bin/env python3
"""Small GitHub Actions monitor: API-only commit checks, no external checkout."""
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = ROOT / "sources.yaml"
STATE_FILE = ROOT / "state/source_state.json"
OUTPUT_FILE = ROOT / "output/changes.json"
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def parse_sources(text):
    sources = []
    current = None
    for line in text.splitlines():
        match = re.match(r"^\s*-\s*repository:\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\s*$", line)
        if match:
            current = {"repository": match.group(1), "owner_engine": "RESEARCH",
                       "routing_target": "RESEARCH_ONLY", "tracked_paths": []}
            sources.append(current)
            continue
        if current is not None:
            match = re.match(r"^\s+(owner_engine|routing_target):\s*([A-Z_]+)\s*$", line)
            if match:
                current[match.group(1)] = match.group(2)
                continue
            match = re.match(r"^\s+tracked_paths:\s*\[(.*)\]\s*$", line)
            if match:
                current["tracked_paths"] = [part.strip().strip("\"'") for part in match.group(1).split(",") if part.strip()]
    return sources


def api(path):
    request = urllib.request.Request("https://api.github.com" + path, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "Nexus-GitHub-Remote-Monitor/1.0",
        "X-GitHub-Api-Version": "2022-11-28", "Authorization": "Bearer " + os.environ["GITHUB_TOKEN"]})
    with urllib.request.urlopen(request, timeout=12) as response:
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise RuntimeError("bounded_api_response_exceeded")
        return json.loads(raw)


def main():
    # Deliberately supports the small generated YAML subset; no YAML dependency.
    sources = parse_sources(SOURCE_FILE.read_text())
    if len(sources) > 200:
        raise RuntimeError("source_count_limit_exceeded")
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    new_events, new_state = [], dict(state)
    now = datetime.now(timezone.utc).isoformat()
    for source in sources:
        repo = source["repository"]
        if not REPO_RE.fullmatch(repo):
            raise RuntimeError("invalid_repository_name")
        meta = api("/repos/" + urllib.parse.quote(repo, safe="/"))
        branch = meta["default_branch"]
        head = api(f"/repos/{repo}/commits/{urllib.parse.quote(branch, safe='')}")
        commit = head["sha"]
        old = new_state.get(repo, {}).get("commit")
        changed = []
        if old and old != commit:
            compare = api(f"/repos/{repo}/compare/{old}...{commit}")
            tracked = source.get("tracked_paths", [])
            changed = [file["filename"] for file in compare.get("files", [])[:100]
                       if not tracked or any(file["filename"] == path or file["filename"].startswith(path.rstrip("/") + "/") for path in tracked)]
            if changed:
                new_events.append({"source_id": repo, "repository": repo, "previous_commit": old, "current_commit": commit,
                "changed_paths": changed, "summary": (head.get("commit", {}).get("message", "Repository changed").splitlines() or [""])[0][:300],
                "owner_engine": source["owner_engine"], "routing_target": source["routing_target"],
                "verification_required": True, "observed_at": now})
        if old != commit:
            new_state[repo] = {"commit": commit, "checked_at": now}
    if new_state != state:
        STATE_FILE.write_text(json.dumps(new_state, indent=2, sort_keys=True) + "\n")
    output = json.loads(OUTPUT_FILE.read_text()) if OUTPUT_FILE.exists() else {"events": []}
    events = (output.get("events", []) + new_events)[-100:]
    payload = {"events": events}
    if events:
        payload["observed_at"] = now if new_events else output.get("observed_at", now)
    OUTPUT_FILE.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"sources_checked": len(sources), "new_change_events": len(new_events), "event_history_count": len(events)}))


if __name__ == "__main__":
    main()
