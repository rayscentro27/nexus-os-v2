from nexus_foundation.multi_market_lab import (
    adapters,
    bounded_specs,
    options_position,
    replay_record,
    run_tournament,
)


def _bars(count=240):
    return [{"time": f"2026-01-{(i // 24) + 1:02d}T{(i % 24):02d}:00:00Z", "mid": {"c": 1.10 + i * 0.0001}} for i in range(count)]


def test_market_contracts_are_paper_only_and_options_are_multi_leg():
    current = adapters()
    assert set(current) == {"FOREX", "CRYPTO", "OPTIONS"}
    assert all(x.live_authority == "NONE" and x.paper_capability for x in current.values())
    position = options_position("SPY", [{"action": "BUY", "call_put": "CALL", "strike": 500, "expiration": "2027-01-15", "quantity": 1, "premium": 4.2}, {"action": "SELL", "call_put": "CALL", "strike": 510, "expiration": "2027-01-15", "quantity": 1, "premium": 1.8}])
    assert len(position["legs"]) == 2 and position["paper_only"] is True


def test_bounded_tournament_is_deterministic_and_replay_safe():
    first = run_tournament(_bars())
    second = run_tournament(_bars())
    assert [x["experiment_id"] for x in first] == [x["experiment_id"] for x in second]
    assert len(first) == 3 and len({x["experiment_id"] for x in first}) == 3
    assert all(x["spec"]["market_type"] == "FOREX" for x in first)
    replay = replay_record(first[0])
    assert replay["lookahead_protected"] is True
    assert replay["execution_authority"] == "NONE"
    assert all("oos" in x for x in first)


def test_experiment_generator_separates_family_and_market():
    specs = bounded_specs()
    assert len({x.experiment_id for x in specs}) == len(specs)
    assert {x.strategy_family for x in specs} == {"TREND_FOLLOWING", "BREAKOUT", "MEAN_REVERSION"}
