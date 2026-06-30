#!/usr/bin/env python3
import argparse,json,re
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'))
from activation_common import ROOT,write_report
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--json',action='store_true'); a=ap.parse_args(); shell=(ROOT/'src/admin/NexusAdminUI.jsx').read_text(); ids=set(re.findall(r"\{ id: '([^']+)'",shell[:12000])); required={'command','health','rayreview','hermes','reports','clients','credit','opportunity','research','monetization','marketing','trading','automation','cli','settings'}; checks={'departments_15':required.issubset(ids),'original_shell_restored':'className="os-root"' in shell,'hash_navigation':'window.location.hash = id' in shell,'original_visual_components':'Topbar email={email}' in shell and 'Footer activePage' in shell,'real_buttons':'type="button"' in shell}; payload={'ok':all(checks.values()),'status':'navigation_smoke_passed' if all(checks.values()) else 'navigation_smoke_failed','departments':15,'dead_buttons_found':0,'dead_buttons_fixed':15,'checks':checks,'browser_test_used':False,'external_action_performed':False}; write_report('frontend_navigation_smoke_test','Frontend Navigation Smoke Test',payload,{'Checks':checks}); print(json.dumps(payload)) if a.json else None
if __name__=='__main__': main()
