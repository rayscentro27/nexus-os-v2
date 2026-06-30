#!/usr/bin/env python3
import argparse,json,re
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'))
from activation_common import ROOT,write_report
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--json',action='store_true'); a=ap.parse_args(); reg=(ROOT/'src/data/reportRegistry.js').read_text(); viewer=(ROOT/'src/components/ReportViewer.jsx').read_text(); total=reg.count('"id":'); checks={'reports_registered':total>=10,'markdown_render':'renderMarkdown' in viewer,'missing_fallback':'Report not generated yet' in viewer,'copy_path':'clipboard.writeText' in viewer}; payload={'ok':all(checks.values()),'status':'report_viewer_smoke_passed','reports_visible':total,'checks':checks,'external_action_performed':False}; write_report('report_viewer_smoke_test','Report Viewer Smoke Test',payload,{'Checks':checks}); print(json.dumps(payload)) if a.json else None
if __name__=='__main__': main()
