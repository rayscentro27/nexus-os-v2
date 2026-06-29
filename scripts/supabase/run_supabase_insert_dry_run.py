#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os
from supabase_activation_common import *

LEGACY_UUID_TABLES={"client_profiles","business_opportunities","partner_offers"}


def normalize(data):
 if isinstance(data,list):return data
 if isinstance(data,dict):
  for key in ("records","items","data","profiles","tasks","cards","opportunities"):
   if isinstance(data.get(key),list):return data[key]
  return [data]
 return []


def project(row,table,index):
 if not isinstance(row,dict): return row,[]
 out=dict(row);changes=[]
 if not out.get("tenant_id"):
  out["tenant_id"]="tenant_demo_goclear";changes.append("tenant_id_defaulted_for_internal_export")
 source_id=out.get("id") or out.get("offer_id") or out.get("key") or out.get("slug") or out.get("title") or out.get("name")
 if not source_id:
  source_id=f"{table}-{index}-{hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()[:12]}";changes.append("deterministic_id_derived")
 if table in LEGACY_UUID_TABLES:
  out["external_id"]=str(source_id);changes.append("id_mapped_to_external_id")
 else:
  out["id"]=str(source_id)
 return out,changes


def build(execute=False)->tuple[dict,int]:
 validations=[];total=0;invalid=0
 for file,table in FILE_TABLE_MAP.items():
  path=SUPABASE_READY/file
  if not path.exists():continue
  rows=normalize(read_json(path,[]));missing=[];transformations=[]
  for i,row in enumerate(rows):
   projected,changes=project(row,table,i);transformations.extend(changes)
   required=("external_id","tenant_id") if table in LEGACY_UUID_TABLES else ("id","tenant_id")
   absent=[k for k in required if not isinstance(projected,dict) or not projected.get(k)]
   if absent:missing.append({"row":i,"missing":absent});invalid+=1
  total+=len(rows);validations.append({"file":file,"table":table,"records":len(rows),"valid":not missing,"missing_fields":missing[:10],"projection_transformations":sorted(set(transformations))})
 gate=execute and os.getenv("NEXUS_SUPABASE_INSERT_APPROVED")=="true"
 if execute:
  report={"ok":False,"generated_at":now(),"status":"execution_blocked","reason":"Live insertion is intentionally not implemented in this activation runner; use the reviewed server-side implementation after RLS approval.","approval_env_present":gate,"live_insertion_performed":False,"external_action_performed":False,"validations":validations}
  code=2
 else:
  report={"ok":invalid==0,"generated_at":now(),"status":"dry_run_passed" if invalid==0 else "dry_run_needs_mapping_fixes","files_validated":len(validations),"records_validated":total,"invalid_records":invalid,
   "validations":validations,"projection_only":True,"default_tenant":"tenant_demo_goclear","live_insertion_performed":False,"service_role_used":False,"next_required_action":"Review projected legacy UUID mappings and tenant defaults before a separately approved execution runner.","external_action_performed":False};code=0 if invalid==0 else 1
 write_report("supabase_insert_dry_run","Supabase Insert Dry Run",report,{"Validations":validations});return report,code


def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");p.add_argument("--execute",action="store_true");a=p.parse_args();r,c=build(a.execute);print(json.dumps(r,indent=2) if a.json else r);return c
if __name__=="__main__":raise SystemExit(main())
