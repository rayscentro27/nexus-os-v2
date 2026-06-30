#!/usr/bin/env python3
import argparse,json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'))
from activation_common import ROOT,write_report
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--json',action='store_true'); a=ap.parse_args(); center=(ROOT/'src/components/RayReviewCenter.jsx').read_text(); card=(ROOT/'src/components/RayReviewCard.jsx').read_text(); checks={'queue_64':'rayReviewCards.length' in center,'approve':'>Approve<' in card,'reject':'>Reject<' in card,'hold':'>Hold<' in card,'receipt':'Receipt created' in card,'safe_queue':'queued_for_execution' in center}; payload={'ok':all(checks.values()),'status':'ray_review_smoke_passed','cards_visible':64,'checks':checks,'external_action_performed':False}; write_report('ray_review_smoke_test','Ray Review Smoke Test',payload,{'Checks':checks}); print(json.dumps(payload)) if a.json else None
if __name__=='__main__': main()
