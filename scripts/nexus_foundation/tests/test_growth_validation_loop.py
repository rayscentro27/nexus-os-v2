import os
from nexus_agent_platform.governed import persistence
from nexus_foundation.growth_validation_loop import aggregate, record_event, validation_plan
def test_no_spend_plan_and_observed_metrics(tmp_path,monkeypatch):
 monkeypatch.setenv('NEXUS_GOVERNED_DATA_DIR',str(tmp_path)); opp={'opportunity_id':'opp_test','status':'ACCEPT_FOR_VALIDATION'}; plan=validation_plan(opp); assert plan['mode']=='NO_SPEND_ORGANIC_MEASUREMENT'; assert plan['prohibited_actions']
 record_event(plan['plan_id'],'VISIT',count=10); record_event(plan['plan_id'],'LEAD',count=2); result=aggregate(plan['plan_id']); assert result['lead_rate']==.2 and result['cac']=='UNKNOWN'
def test_event_idempotency(tmp_path,monkeypatch):
 monkeypatch.setenv('NEXUS_GOVERNED_DATA_DIR',str(tmp_path)); a=record_event('plan','VISIT',source='fixture',metadata={'x':1}); b=record_event('plan','VISIT',source='fixture',metadata={'x':1}); assert a['event_id']==b['event_id']; assert len(persistence.read_records('metrics'))==1
