#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from monetization_common import SUPABASE_READY,now,offers,write_json,write_report
def build():
 rows=offers();write_json(SUPABASE_READY/"offer_registry_latest.json",rows);report={"ok":len(rows)>=9,"generated_at":now(),"status":"offer_registry_active","offers_count":len(rows),"primary_offer":"$97 Credit & Funding Readiness Review","offers_live":0,"approval_gated":len(rows),"external_action_performed":False};write_report("offer_registry","Offer Registry",report,{"Offers":rows});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
