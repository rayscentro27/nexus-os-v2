#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent.parent;sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import RUNTIME,SUPABASE_READY,now,read_json,write_json,write_report  # noqa:E402


def rows(data):
 if isinstance(data,list):return data
 if isinstance(data,dict):
  for key in ("approval_cards","cards","items","records","queue"):
   if isinstance(data.get(key),list):return data[key]
 return []


def build()->dict:
 files=sorted(set(RUNTIME.rglob("*approval*latest.json"))|set(RUNTIME.rglob("ray_review*latest.json")));dedup={}
 for path in files:
  if "prioritized" in path.name:continue
  for card in rows(read_json(path,[])):
   if not isinstance(card,dict):continue
   title=str(card.get("title") or card.get("name") or card.get("summary") or "").strip()
   if not title:continue
   key=" ".join(title.lower().split());dedup.setdefault(key,{**card,"title":title,"source_file":str(path.relative_to(ROOT))})
 seeds=[
  ("Approve Supabase core migration and RLS test plan","approve today","backend/data",100,"Review DRAFT SQL and approve local migration/RLS tests.","python3 scripts/supabase/run_supabase_insert_dry_run.py --json"),
  ("Approve $97 payment method and test-mode checkout design","approve today","revenue",98,"Select Stripe test mode or an approved manual fallback.","python3 scripts/monetization/prepare_payment_crm_path.py --json"),
  ("Approve first real YouTube metadata or transcript source","approve today","automation",95,"Authorize bounded metadata API intake or one approved transcript file.","python3 scripts/activation/run_youtube_metadata_intake.py --json"),
  ("Approve tenant-safe client creation workflow","review before Supabase","client onboarding",94,"Confirm tenant/client roles and minimum intake fields.","Review supabase/migrations/DRAFT_client_portal_core_tables.sql"),
  ("Approve Meta read-only connector validation","review before live external action","automation",85,"Authorize identity-only token/page validation; no posting.","Review reports/manual_publish/meta_connector_validation_plan_latest.md"),
  ("Approve dispute sandbox design","review before live external action","safety",84,"Approve synthetic sandbox only; real sends remain blocked.","Review reports/manual_publish/dispute_sandbox_upgrade_plan_latest.md")]
 for title,group,impact,score,decision,command in seeds:
  dedup.setdefault(title.lower(),{"id":"priority-"+str(score),"title":title,"category":impact,"approval_required":True,"source_file":"same_day_activation"})
  dedup[title.lower()].update({"group":group,"score":score,"exact_decision":decision,"next_command_or_action":command})
 cards=[]
 for key,card in dedup.items():
  title=card["title"];text=(title+" "+str(card.get("category",""))).lower()
  score=card.get("score") if isinstance(card.get("score"),int) else 50
  if any(x in text for x in ("$97","payment","supabase","tenant","youtube")):score=max(score,90)
  elif any(x in text for x in ("dispute","funding","credit","social","meta")):score=max(score,75)
  group=card.get("group") or ("approve today" if score>=90 else "review before live external action" if any(x in text for x in ("publish","send","connector","dispute")) else "review before Supabase" if any(x in text for x in ("client","guidance","document")) else "later")
  cards.append({"id":card.get("id",f"ray-review-{len(cards)+1}"),"tenant_id":card.get("tenant_id","tenant_demo_goclear"),"client_id":card.get("client_id","not_applicable"),"title":title,"category":card.get("category","operations"),"group":group,"priority_score":score,"status":"ready_for_Ray_review","approval_required":True,"exact_decision":card.get("exact_decision",f"Approve, reject, or defer: {title}"),"next_command_or_action":card.get("next_command_or_action","Record Ray's approve/reject/defer decision in Ray Review."),"source_file":card["source_file"],"external_action_performed":False,"created_at":now()})
 cards.sort(key=lambda x:(-x["priority_score"],x["title"]));write_json(SUPABASE_READY/"ray_review_prioritized_today_latest.json",cards)
 today=[x for x in cards if x["group"]=="approve today"]
 report={"ok":True,"generated_at":now(),"status":"ready_for_Ray_review","source_files_scanned":len(files),"deduped_card_count":len(cards),"approve_today_count":len(today),"groups":{g:sum(x["group"]==g for x in cards) for g in ("approve today","review before Supabase","review before live external action","later")},"top_cards":cards[:15],"external_action_performed":False,"summary":f"Deduped {len(cards)} cards; {len(today)} require a same-day Ray decision."}
 write_report("ray_review_prioritized_today","Ray Review Prioritized Today",report,{"Approve today":today,"Next queue":cards[len(today):len(today)+15]});return report


def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);return 0
if __name__=="__main__":raise SystemExit(main())
