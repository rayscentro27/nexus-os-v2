from nova.research_room_dispatch import render_nova_research_response


def _trading_result():
    return {"case": {
        "status": "COMPLETE",
        "source_report": {"text": (
            "█ CONCEPTS Seasonal harvest model. █ THE RULES Sell short at the selling level. "
            "Delay these sells to ensure two sells are not in the same rally. "
            "Avoid selling immediately after harvest. Exit positions (cover shorts) at harvest. "
            "▌Properties Position Sizing : This strategy sells in one-contract increments up to three times per year. "
            "█ INPUTS MA length : Moving Average length (Simple Moving Average). A 20 to 60 day range is recommended; with 40 as a starting point. "
            "ATR factor : 2.5 to 3.5 is generally recommended. Open-source script"
        )},
        "final_synthesis": {"execution_strategy": {
            "execution_mode": "TRADING_STRATEGY_MODE",
            "strategy": "Ag Selling Model",
            "market": "Corn futures",
            "timeframe": "Seasonal long-hold; chart interval unverified",
            "strategy_rules": {},
            "unverified_rules": ["Stop and target are not confirmed"],
            "data_required": ["Timestamped OHLCV and roll handling", "Fees and slippage"],
            "backtest_plan": {"steps": ["Chronological train/validation/test", "Include fees/slippage"]},
            "variants_to_test": ["Source parameters", "Nearby sensitivity without holdout tuning"],
            "paper_trading_plan": {"mode": "PAPER ONLY", "risk": "0.25% per trade; Nexus proposed, pending approval"},
            "trading_engine_build_requirements": ["Versioned parameters", "Paper-only guard"],
            "library_additions": [{"name": "Ag Selling test record", "summary": "Preserve source rules and test protocol"}],
            "next_action": "Trading creates the versioned source-rule spec.",
        }},
    }}


def test_trading_renderer_preserves_strategy_name_and_rules():
    rendered = render_nova_research_response(_trading_result())
    assert "Ag Selling Model" in rendered
    assert "RULES — SOURCE-DERIVED" in rendered
    assert "sell short at the source-defined selling level" in rendered
    assert "cover short positions at harvest" in rendered


def test_trading_renderer_preserves_unverified_data_and_backtest():
    rendered = render_nova_research_response(_trading_result())
    assert "UNVERIFIED_RULES" in rendered
    assert "Stop and target are not confirmed" in rendered
    assert "DATA_REQUIRED" in rendered and "Timestamped OHLCV" in rendered
    assert "BACKTEST_PLAN" in rendered and "Chronological train/validation/test" in rendered


def test_trading_renderer_preserves_variants_paper_plan_and_library():
    rendered = render_nova_research_response(_trading_result())
    assert "VARIANTS_TO_TEST" in rendered and "Source parameters" in rendered
    assert "PAPER_TRADING_PLAN" in rendered and "PAPER ONLY" in rendered
    assert "NEXUS-PROPOSED CONTROLS, NOT SOURCE RULES" in rendered
    assert "0.25% per trade" in rendered
    assert "LIBRARY_ADDITIONS" in rendered and "Ag Selling test record" in rendered
    assert "TRADING_ENGINE_BUILD_REQUIREMENTS" in rendered


def test_trading_renderer_requires_next_action_and_handoff():
    rendered = render_nova_research_response(_trading_result())
    assert "PROPOSED_HANDOFF=TRADING" in rendered
    assert "NEXT_ACTION" in rendered
    assert "Trading creates the versioned source-rule spec." in rendered


def test_business_renderer_regression_pass():
    result = {"case": {"final_synthesis": {"execution_strategy": {
        "execution_mode": "BUSINESS_OPPORTUNITY_MODE",
        "winner": "Lead-response automation",
        "top_businesses": [{"business": "Lead-response automation", "customer": "Local service firms",
                             "offer": "Install and configure follow-up workflows", "price": "$1,000 pilot"}],
        "why_winner": "Fits existing capabilities and can be validated quickly.",
        "how_nova_runs_it": {"finds_customers": "Builds an approved target list", "qualifies_customers": "Checks fit"},
        "what_nexus_needs_to_build": "A repeatable onboarding checklist",
        "first_10_customer_plan": "Warm referrals and owner interviews",
        "next_action": "Interview five local operators.",
    }}}}
    rendered = render_nova_research_response(result)
    assert "Lead-response automation" in rendered
    assert "Who pays" in rendered and "Local service firms" in rendered
    assert "What Nexus sells" in rendered
    assert "How Nova runs it" in rendered
    assert "Next action" in rendered and "Interview five local operators." in rendered


def test_each_supported_mode_uses_a_mode_specific_renderer():
    cases = {
        "NEXUS_ENHANCEMENT_MODE": {"technology": "Tool X", "what_nexus_should_adopt": ["Least privilege"],
                                   "implementation_plan": ["Run isolated test"], "next_action": "Systems reviews."},
        "CLAIM_VERIFICATION_MODE": {"what_we_know": ["Claim is unverified"],
                                    "what_we_do_not_know": ["Independent evidence"], "next_action": "Verify source."},
        "DEEP_RESEARCH_MODE": {"what_we_know": ["Known fact"], "what_we_do_not_know": ["Open question"],
                               "what_nexus_should_do": ["Run bounded test"], "next_action": "Assign owner."},
    }
    for mode, strategy in cases.items():
        strategy["execution_mode"] = mode
        rendered = render_nova_research_response({"case": {"final_synthesis": {"execution_strategy": strategy}}})
        assert "Next action" in rendered
        assert strategy["next_action"] in rendered
        assert "I completed the" not in rendered
