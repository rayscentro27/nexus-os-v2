#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'));from activation_common import SUPABASE_READY,write_json,write_report
def main():
 a=argparse.ArgumentParser();a.add_argument('--json',action='store_true');x=a.parse_args();cards=[{'id':'approve-hermes-delegated-external-actions','title':'Review external actions from Hermes delegation plan','status':'pending','underlying_action_executed':False}];write_json(SUPABASE_READY/'hermes_ray_review_cards_latest.json',cards);p={'ok':True,'status':'hermes_review_cards_ready','cards':len(cards),'external_action_performed':False};write_report('hermes_ray_review_cards','Hermes Ray Review Cards',p,{'Cards':cards});print(json.dumps(p)) if x.json else None
if __name__=='__main__':main()
