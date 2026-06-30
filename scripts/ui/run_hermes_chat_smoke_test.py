#!/usr/bin/env python3
import argparse,json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'activation'))
from activation_common import ROOT,write_report
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--json',action='store_true'); a=ap.parse_args(); chat=(ROOT/'src/components/HermesChatPanel.jsx').read_text(); data=(ROOT/'src/data/hermesWorkroomData.js').read_text(); checks={'input': 'Message Hermes' in chat,'send_button':'>Send<' in chat,'enter_key':"event.key === 'Enter'" in chat,'fallback':'buildHermesResponse' in chat,'large_prompt':'delegation' in data,'no_spinner': 'spinner' not in chat.lower()}; payload={'ok':all(checks.values()),'status':'hermes_chat_smoke_passed','checks':checks,'external_action_performed':False}; write_report('hermes_chat_smoke_test','Hermes Chat Smoke Test',payload,{'Checks':checks}); print(json.dumps(payload)) if a.json else None
if __name__=='__main__': main()
