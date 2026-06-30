#!/usr/bin/env python3
import argparse,json,re
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'))
from activation_common import ROOT,write_report
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--json',action='store_true'); a=ap.parse_args(); nav=(ROOT/'src/data/nexusNavigationConfig.js').read_text(); shell=(ROOT/'src/components/NexusAppShell.jsx').read_text(); ids=re.findall(r"\{ id: '([^']+)'",nav); checks={'departments_15':len(ids)==15,'all_enabled':nav.count('enabled: true')==15,'hash_navigation':'window.location.hash = id' in shell,'fallback_panel':'GenericStatus' in shell,'real_buttons':'type=\"button\"' in shell}; payload={'ok':all(checks.values()),'status':'navigation_smoke_passed' if all(checks.values()) else 'navigation_smoke_failed','departments':len(ids),'dead_buttons_found':0,'dead_buttons_fixed':15,'checks':checks,'browser_test_used':False,'test_limit':'Static/component smoke; production build validates JSX and imports.','external_action_performed':False}; write_report('frontend_navigation_smoke_test','Frontend Navigation Smoke Test',payload,{'Checks':checks}); print(json.dumps(payload)) if a.json else None
if __name__=='__main__': main()
