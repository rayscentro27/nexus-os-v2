from nexus_agent_platform.feeder_runtime import PROMPTS, ROUTES, _gaps, _nova_analysis
from scheduled_research_router import resolve_feeder_gap_source


def test_six_routes_are_deterministic_and_templates_are_full():
    assert len(PROMPTS) == 6
    assert ROUTES['BUSINESS_OPPORTUNITY_FEEDER'] == ('BUSINESS_OPPORTUNITIES', 'ATLAS')
    assert ROUTES['BUSINESS_FUNDING_FEEDER'] == ('BUSINESS_FUNDING', 'CLYDE')
    assert ROUTES['BUSINESS_CREATION_BANKABILITY_FEEDER'][0] == 'BUSINESS_CREATION'
    assert ROUTES['FOREX_INDICATOR_STRATEGY_FEEDER'][1] == 'MERCURY_FOREX_INDICATOR_LAB'
    assert ROUTES['OPTIONS_STRATEGY_FEEDER'][1] == 'MERCURY_OPTIONS_LAB'
    assert len(PROMPTS['OPTIONS_STRATEGY_FEEDER']) > 1300
    assert 'RECOMMENDED_NAICS' in PROMPTS['BUSINESS_CREATION_BANKABILITY_FEEDER']


def test_missing_fields_become_exact_gap_questions():
    questions = _gaps('BUSINESS_OPPORTUNITY_FEEDER', {'BUSINESS_MODEL': 'service'})
    assert any('target customer' in question for question in questions)
    assert any('demand evidence' in question for question in questions)


def test_goclear_nova_first_pass_is_a_ray_gate_not_a_decision():
    fields, response = _nova_analysis('GoClear could offer funding readiness help to business owners.')
    assert fields['SOURCE'] == 'RAY_NOVA'
    assert fields['FUNDING_REQUIRED_LIKELY'] == 'NO for initial validation; later amount unknown'
    assert fields['REVENUE_MODEL'].startswith('Possible fee / commission')
    assert response['RECOMMENDATION'] in {'DISCUSS_FURTHER', 'SEND_TO_RESEARCH', 'SAVE_FOR_LATER'}
    assert 'APPROVE_BUSINESS' not in response.values()


def test_source_less_feeder_gap_uses_public_search_and_keeps_exact_question():
    item={'request_type':'FEEDER_GAP_CLOSURE','work_id':'gap-1','research_question':'What are current public requirements?','source_url':None,'search_context':'Business Funding'}
    resolved,discovery=resolve_feeder_gap_source(item,lambda query,limit:{'provider':'fixture','results':[{'url':'https://example.org/requirements','title':'Requirements'}]})
    assert resolved['source_url']=='https://example.org/requirements'
    assert resolved['source_type']=='PUBLIC_SEARCH_RESULT'
    assert discovery['exact_question']==item['research_question']
    assert 'funding' in discovery['query']
    assert discovery['selected_url']==resolved['source_url']


def test_source_less_feeder_gap_surfaces_search_blocker():
    item={'request_type':'FEEDER_GAP_CLOSURE','work_id':'gap-2','research_question':'Find current evidence'}
    try:
        resolve_feeder_gap_source(item,lambda query,limit:{'provider':'none','results':[],'notes':['provider unavailable']})
    except RuntimeError as exc:
        assert str(exc)=='FEEDER_GAP_SEARCH_UNAVAILABLE:provider unavailable'
    else:
        raise AssertionError('search blocker must remain explicit')
