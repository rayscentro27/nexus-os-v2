#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import RUNTIME,SUPABASE_READY,now,read_json,write_json,write_report  # noqa:E402
def build():
 listing=read_json(RUNTIME/"notebooklm_notebook_list_latest.json",{});cards=[]
 if not listing.get("notebooks_listed"):cards.append({"id":"approve-notebooklm-watched-export","title":"Approve selected NotebookLM export into the watched folder","status":"pending_Ray_review","approval_required":True,"external_action_performed":False,"created_at":now()})
 else:cards.append({"id":"select-notebooklm-notebooks","title":"Select NotebookLM notebooks and assign research lanes","status":"pending_Ray_review","approval_required":True,"external_action_performed":False,"created_at":now()})
 cards.append({"id":"block-unofficial-notebooklm-browser","title":"Keep unofficial NotebookLM browser/cookie automation blocked","status":"policy_active","approval_required":True,"external_action_performed":False,"created_at":now()});write_json(SUPABASE_READY/"notebooklm_approval_cards_latest.json",cards);report={"ok":True,"generated_at":now(),"status":"notebooklm_review_cards_ready","cards_created":len(cards),"external_action_performed":False};write_report("notebooklm_ray_review_cards","NotebookLM Ray Review Cards",report,{"Cards":cards});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
