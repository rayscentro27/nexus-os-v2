#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from marketing_common import SUPABASE_READY,item,now,write_json,write_report
def build():
 rows=[{**item(i,title,"landing_page_experiment"),"variant":name,"hypothesis":hyp} for i,(name,title,hyp) in enumerate([("A","Know Before You Apply","Readiness-first language reduces premature applications."),("B","Your Funding Readiness Roadmap","Roadmap framing improves $97 review conversion."),("C","Stop Guessing About Credit and Funding","Pain-focused copy improves qualified intake.")])];write_json(SUPABASE_READY/"landing_page_experiments_latest.json",rows);report={"ok":True,"generated_at":now(),"status":"landing_page_experiments_ready","experiments":len(rows),"deployed":0,"external_action_performed":False};write_report("landing_page_experiments","Landing Page Experiments",report,{"Experiments":rows});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
