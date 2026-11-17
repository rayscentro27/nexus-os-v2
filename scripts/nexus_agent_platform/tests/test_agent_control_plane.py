import json
from pathlib import Path

import pytest
from nexus_agent_platform import agent_control_plane as cp
from nexus_agent_platform.creative import execution_router


def test_registries_have_unique_ids_and_contract_bounds():
    data = cp._identities()
    assert 'NOVA' in data['agents'] and 'ASSET_PERSISTENCE' in data['agents']
    assert len(data['agents']) == len(set(data['agents']))
    for row in data['agents'].values():
        if 'bot_id' in row:
            cp.validate_bot_contract(row)


def test_unapproved_skill_connector_and_environment_denied():
    with pytest.raises(cp.AuthorizationDenied, match='SKILL_NOT_ALLOWED'):
        cp.authorize(agent_id='NOVA', skill_id='research.deep_analysis')
    with pytest.raises(cp.AuthorizationDenied, match='CONNECTOR_NOT_ALLOWED'):
        cp.authorize(agent_id='NOVA', connector_id='CLOUDFLARE_R2')
    with pytest.raises(cp.AuthorizationDenied, match='ENVIRONMENT_NOT_ALLOWED'):
        cp.authorize(agent_id='MERCURY', environment_id='MODAL_GPU')


def test_bot_cannot_hardcode_provider_and_no_model_cannot_call_model():
    bot = {'bot_id':'X','model_required':True,'model_profile':'RESEARCH_FAST','provider':'openai','max_model_calls':1,'max_input_tokens':10,'max_output_tokens':10,'max_cost_usd':.1,'max_runtime_seconds':10,'max_retries':0}
    with pytest.raises(cp.AuthorizationDenied, match='BOT_MUST_REQUEST_MODEL_PROFILE_ONLY'):
        cp.validate_bot_contract(bot)
    with pytest.raises(cp.AuthorizationDenied, match='NO_MODEL_BOT_CANNOT_CALL_MODEL'):
        cp.authorize(agent_id='CREATIVE_LEAD', bot_id='ASSET_PERSISTENCE', model_profile='CREATIVE_PROMPT')
    assert cp.authorize(agent_id='CREATIVE_LEAD', bot_id='ASSET_PERSISTENCE', model_profile='NO_MODEL')['status']=='AUTHORIZED'


def test_nova_mercury_alpha_forbidden_authority():
    nova=cp._identities()['agents']['NOVA']; mercury=cp._identities()['agents']['MERCURY']; alpha=cp._identities()['agents']['ALPHA']
    assert 'CLOUDFLARE_R2_RAW' in nova['forbidden_connectors']
    assert 'LIVE_TRADING' in mercury['forbidden_connectors']
    assert 'PUBLISHING' in alpha['forbidden_connectors']


def test_unavailable_environment_is_not_routed_and_fallback_must_be_allowed():
    rows=[{'environment_id':'bad','status':'UNAVAILABLE','health':'UNKNOWN'}, {'environment_id':'ok','status':'LIVE_CERTIFIED','health':'LIVE_CERTIFIED'}]
    assert cp.select_environment(allowed=['bad'],preferred=['bad'],fallbacks=[],registry=rows,runtime_health={'bad':'UNKNOWN'})['status']=='UNAVAILABLE'
    out=cp.select_environment(allowed=['bad','ok'],preferred=['bad'],fallbacks=['ok'],registry=rows,runtime_health={'bad':'UNKNOWN','ok':'LIVE_CERTIFIED'})
    assert out=={'status':'SELECTED','environment_id':'ok','selection_class':'ALLOWED_FALLBACK'}
    assert cp.select_environment(allowed=['ok'],preferred=['ok'],fallbacks=[],registry=rows)['status']=='UNAVAILABLE'


def test_registry_snapshot_never_exposes_credential_values(monkeypatch):
    monkeypatch.setattr(cp,'_identities',lambda:{'agents':{'a':{'agent_id':'a','credential_value':'secret'}},'skills':{},'connectors':{},'environments':{},'models':{}})
    assert 'credential_value' not in cp.public_registry_snapshot()['agents'][0]


def test_asset_persistence_is_r2_only_and_temp_output_is_not_completion():
    source=Path('scripts/nexus_agent_platform/creative/asset_persistence.py').read_text()
    assert 'CloudflareR2StorageAdapter' in source and 'NON_CANONICAL_STORAGE_PROVIDER_BLOCKED' in source
    assert 'canonical_storage_verified' in source and 'generation_receipt' in source
    bot=cp._identities()['agents']['ASSET_PERSISTENCE']
    assert bot['model_profile']=='NO_MODEL' and bot['model_required'] is False


def test_model_profile_delegates_to_manager_without_exposing_route(monkeypatch):
    monkeypatch.setattr('scripts.model_router.select_reasoning_model', lambda **kwargs: {'decision':'selected','provider':'private-provider','model':'private-model','route':{'route_key':'safe'}})
    out=cp.resolve_model_profile(profile_id='RESEARCH_FAST',agent_id='ALPHA')
    assert out=={'status':'AVAILABLE','profile_id':'RESEARCH_FAST','resolved_by':'NEXUS_MODEL_MANAGER'}
    assert cp.resolve_model_profile(profile_id='NO_MODEL',agent_id='CREATIVE_LEAD',bot_id='ASSET_PERSISTENCE')=={'status':'NO_MODEL','profile_id':'NO_MODEL'}

def test_resource_budget_exceeded_is_explicit():
    with pytest.raises(cp.AuthorizationDenied, match='RESOURCE_BUDGET_EXCEEDED'):
        cp.enforce_resource_budget(actual_cost_usd=.3,max_cost_usd=.25,elapsed_seconds=2,max_runtime_seconds=10)


def test_authorized_creative_route_requires_runtime_health_and_never_completes_temp_output():
    work={'work_order_id':'w1','campaign_id':'c1','asset_type':'COPY','format':'JSON','quality_profile':'STANDARD','model_profile':'DETERMINISTIC_NO_MODEL','budget_class':'ZERO_SPEND_INTERNAL','approval_state':'APPROVED'}
    envs=[{'environment_id':'LOCAL_DETERMINISTIC_MEDIA_WORKER','active':True,'canonical_storage':False,'supported_media_types':['COPY'],'supported_formats':['JSON'],'quality_profiles':['STANDARD'],'requires_brand':False,'approval_required':False,'cost_rank':0,'latency_rank':0}]
    denied=execution_router.route_authorized(work,agent_id='CREATIVE_LEAD',bot_id='CREATIVE_EXECUTION_ROUTER',runtime_health={},environments=envs)
    assert denied['status']=='UNAVAILABLE'
    allowed=execution_router.route_authorized(work,agent_id='CREATIVE_LEAD',bot_id='CREATIVE_EXECUTION_ROUTER',runtime_health={'LOCAL_DETERMINISTIC_MEDIA_WORKER':'HEALTHY'},environments=envs)
    assert allowed['status']=='ROUTED'
    assert allowed.get('work_order_status') != 'COMPLETE'


def test_per_bot_model_call_and_resource_limits_are_enforced():
    bot=cp._identities()['agents']['ASSET_PERSISTENCE']
    with pytest.raises(cp.AuthorizationDenied, match='NO_MODEL_BOT_CANNOT_CALL_MODEL'):
        cp.enforce_bot_budget(bot=bot,model_calls=1,input_tokens=0,output_tokens=0,cost_usd=0,elapsed_seconds=1)
    reasoning=cp._identities()['agents']['ALPHA_DEEP_RESEARCH']
    with pytest.raises(cp.AuthorizationDenied, match='RESOURCE_BUDGET_EXCEEDED'):
        cp.enforce_bot_budget(bot=reasoning,model_calls=4,input_tokens=1,output_tokens=1,cost_usd=.01,elapsed_seconds=1)
