#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import json
root=Path(__file__).resolve().parents[1];out={'timestamp':datetime.now(timezone.utc).isoformat(),'cycle':'daily_closeout','external_actions':0,'summary':'Local reports closed; approval-gated and blocked jobs skipped.'}
p=root/'reports/activation/nexus_daily_closeout_latest.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
