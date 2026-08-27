"""Run bounded Oracle Gemma and zero-cost guard evidence without cloud mutation."""
from __future__ import annotations
import json, subprocess, time
from pathlib import Path
from nexus_agent_platform.oracle_gemma_provider import health, review
from nexus_agent_platform.oracle_cost_guard import evaluate
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'reports/certification/nexus_oracle_gemma_latest.json'; MD=ROOT/'reports/certification/nexus_oracle_gemma_latest.md'
def main():
    h=health(); r=review({'deterministic_status':'NO_VALID_SETUP','evaluated_setups':9,'orders':0,'live_trading':False,'paper_only':True},expected_status='NO_VALID_SETUP') if h['status']=='ORACLE_AI_READY' else {'status':'FALLBACK_REQUIRED'}
    connectivity=False
    try:
        p=subprocess.run(['curl','-sf','--max-time','5','http://127.0.0.1:11435/api/generate','-H','Content-Type: application/json','-d','{"model":"gemma3:4b","prompt":"Reply with exactly: NEXUS_ORACLE_AI_OK","stream":false}'],capture_output=True,text=True,timeout=8)
        connectivity='NEXUS_ORACLE_AI_OK' in p.stdout
    except Exception: pass
    payload={'provider':h,'connectivity_expected':'NEXUS_ORACLE_AI_OK','connectivity':connectivity,'bounded_review':r,'cost_guard':evaluate(0.0),'oracle_cost_native_alerts':'REPORTED_BY_OPERATOR_CONFIGURATION_NOT_QUERIED','oracle_cost_api':'NOT_CONFIGURED','autonomous_provisioning':False,'public_ollama_exposure':False,'forex_ai_dependency':False,'live_trading':False,'paper_only':True,'reboot_certified':False}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2)+'\n')
    MD.write_text('# Oracle Gemma Remote AI Certification\n\n- provider: oracle_ollama_gemma\n- model: gemma3:4b\n- tunnel/API health: '+h['status']+'\n- connectivity: '+str(connectivity)+'\n- bounded review: '+r.get('status','UNKNOWN')+'\n- deterministic forex dependency: false\n- live trading: false\n- cost target: $0.00\n- OCI cost API: NOT_CONFIGURED\n- native budget/anomaly alerts: preserved; not mutated\n- reboot certification: not performed\n')
if __name__=='__main__': main()
