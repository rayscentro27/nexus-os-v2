#!/usr/bin/env python3
"""Build source-backed feeder and Ray/Nova intake morning status."""
from __future__ import annotations
import json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from nexus_agent_platform.feeder_runtime import health_report

def main():
    cache_path=ROOT/'reports/runtime/feeder_opportunity_intake_status_latest.json'
    status=None
    try:
        cached=json.loads(cache_path.read_text(encoding='utf-8'))
        cached_at=datetime.fromisoformat(str(cached['generated_at']).replace('Z','+00:00'))
        cache_age=(datetime.now(timezone.utc)-cached_at).total_seconds()
        if cache_age<=3600:status={**cached,'report_source':'LAST_SUCCESSFUL_SUPABASE_WORKER_READBACK','monitor_snapshot_age_seconds':int(cache_age)}
    except (OSError,ValueError,KeyError,TypeError):
        cache_age=None
    # The scheduler writes its own cycle receipt. If the most recent wake
    # failed after this snapshot, surface the failure while retaining the last
    # verified counts; never replace a current failure with an old PASS.
    try:
        run_path=ROOT/'data/runtime/systems_workflow_runs.jsonl'
        last=next((json.loads(line) for line in reversed(run_path.read_text(encoding='utf-8').splitlines()) if '"feeder_runtime"' in line),{})
        feeder=last.get('feeder_runtime') or {}
        if status and feeder.get('status') in {'DEGRADED','CHECK_ERROR'}:
            status.update({'status':'DEGRADED','systems_next_workflow':feeder.get('next_workflow') or 'FEEDER_QUEUE_RECOVERY','failure':feeder.get('diagnostic_tail') or feeder.get('error_class') or 'latest feeder wake failed','ray_action_required':False})
    except (OSError,ValueError,IndexError,TypeError):
        pass
    if status is None:
        try:status=health_report()
        except Exception as exc:
            status={'status':'CHECK_ERROR','generated_at':datetime.now(timezone.utc).isoformat(),'source_counts':{},'research_gaps':{},'handoffs':{},'nova':{},'systems_next_workflow':'SUPABASE_RUNTIME_RECOVERY','failure':f'{type(exc).__name__}: {str(exc)[:300]}'}
    hand=status.get('handoffs',{});gaps=status.get('research_gaps',{});nova=status.get('nova',{})
    report={'schema_version':'nexus.feeder-morning-report.v1','generated_at':status['generated_at'],'title':'FEEDER + OPPORTUNITY INTAKE STATUS','status':status['status'],'sources_added':sum(x.get('sources',0) for x in status['source_counts'].values()),'sources_processed':sum(x.get('handed_off',0)+x.get('research_required',0) for x in status['source_counts'].values()),'research_gaps_created':gaps.get('open',0)+gaps.get('completed',0),'research_gaps_completed':gaps.get('completed',0),'handoffs_completed':hand.get('completed',0),'blocked':sum(x.get('blocked',0) for x in status['source_counts'].values()),'failed':sum(x.get('failed',0) for x in status['source_counts'].values()),'ray_nova_ideas':{'new':nova.get('RAY_INTAKE_REVIEW',0),'discussed':nova.get('DISCUSSING',0),'sent_to_research':nova.get('SENT_TO_RESEARCH',0),'saved':nova.get('SAVED_BY_RAY',0),'promoted_to_atlas':nova.get('IN_ATLAS_WORKFLOW',0)},'recovery_workflow':status['systems_next_workflow'],'ray_action_required':status['status'] in {'BLOCKED_BY_AUTH','HANDOFF_STALLED','DOWNSTREAM_STALLED'},'failure':status.get('failure'),'reason':'See queue, handoff, and gap counts; normal successes do not notify Ray.'}
    out=ROOT/'reports/runtime/feeder_opportunity_morning_report_latest.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
