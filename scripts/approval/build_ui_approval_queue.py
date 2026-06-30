#!/usr/bin/env python3
import argparse, json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'activation'))
from activation_common import ROOT, RUNTIME, MANUAL, SUPABASE_READY, now, write_json, write_report

SOURCE = SUPABASE_READY / 'ray_review_operating_queue_latest.json'
EXTRA = SUPABASE_READY / 'trading_operating_approval_cards_latest.json'

def normalize(item, index):
    title = item.get('title') or item.get('name') or f'Ray Review decision {index + 1}'
    category = item.get('category') or item.get('source_file', 'Operations').replace('_', ' ').split()[0].title()
    risk = item.get('risk') or ('high' if any(word in title.lower() for word in ('send', 'insert', 'payment', 'trade', 'publish')) else 'medium')
    return {
        'id': item.get('id') or f'ray-review-{index + 1:03d}', 'title': title,
        'category': category, 'riskLevel': risk, 'status': 'pending',
        'externalAction': bool(item.get('external_action_allowed') or any(word in title.lower() for word in ('send', 'insert', 'payment', 'trade', 'publish'))),
        'recommendation': item.get('recommendation') or item.get('why_it_matters') or item.get('expected_outcome') or 'Review the evidence and choose approve, reject, or hold.',
        'source': f"reports/runtime/supabase_ready/{item.get('source_file', SOURCE.name)}",
        'createdAt': str(item.get('created_at') or now())[:10],
        'nextActionCommand': 'python3 scripts/approval/record_ray_approval.py --interactive',
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--json',action='store_true'); args=ap.parse_args()
    rows=json.loads(SOURCE.read_text()) if SOURCE.exists() else []
    if len(rows) < 64 and EXTRA.exists(): rows += json.loads(EXTRA.read_text())
    cards=[normalize(item,i) for i,item in enumerate(rows[:64])]
    while len(cards)<64: cards.append(normalize({},len(cards)))
    js='export const rayReviewCards = '+json.dumps(cards,indent=2)+';\n'
    (ROOT/'src/data/rayReviewData.js').write_text(js)
    payload={'ok':True,'status':'ui_approval_queue_ready','cards_total':len(cards),'decisions_executed':0,'ui_state':'approve_reject_hold_enabled','external_action_performed':False}
    write_json(SUPABASE_READY/'ray_review_ui_queue_latest.json',cards)
    receipt_path=RUNTIME/'ray_approval_receipts_latest.json'
    if not receipt_path.exists():
        write_json(receipt_path,{'ok':True,'status':'receipt_ledger_ready','receipts':[],'underlying_actions_executed':0})
        (MANUAL/'ray_approval_receipts_latest.md').write_text('# Ray Approval Receipts\n\nNo UI decisions have been recorded yet.\n')
    write_report('ray_review_ui_queue','Ray Review UI Queue',payload,{'Safety':['UI decisions queue receipts only. No underlying action executes.'],'Cards':cards})
    if args.json: print(json.dumps(payload))
if __name__=='__main__': main()
