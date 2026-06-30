#!/usr/bin/env python3
import argparse, json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'activation'))
from activation_common import RUNTIME, MANUAL, now, write_json

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--interactive',action='store_true'); ap.add_argument('--card-id'); ap.add_argument('--decision',choices=['approved','rejected','held']); ap.add_argument('--feedback',default=''); ap.add_argument('--json',action='store_true'); a=ap.parse_args()
    card=a.card_id; decision=a.decision
    if a.interactive:
        card=card or input('Card ID: ').strip(); decision=decision or input('Decision (approved/rejected/held): ').strip()
    if not card or decision not in {'approved','rejected','held'}: raise SystemExit('card-id and a valid decision are required')
    receipt={'ok':True,'receipt_id':f"ray-{now().replace(':','').replace('.','')}",'card_id':card,'decision':decision,'feedback':a.feedback,'execution_status':'queued_for_execution','underlying_action_executed':False,'created_at':now()}
    write_json(RUNTIME/'ray_approval_receipts_latest.json',receipt)
    MANUAL.mkdir(parents=True,exist_ok=True); (MANUAL/'ray_approval_receipts_latest.md').write_text(f"# Ray Approval Receipt\n\n- card_id: {card}\n- decision: {decision}\n- execution_status: queued_for_execution\n- underlying_action_executed: false\n")
    if a.json: print(json.dumps(receipt))
if __name__=='__main__': main()
