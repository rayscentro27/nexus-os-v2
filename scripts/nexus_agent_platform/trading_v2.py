"""V2 Trading contracts: research, deterministic paper simulation, and risk."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def strategy_contract(*, strategy_id: str, name: str, version: str, asset_class: str,
                      symbol_universe: list[str], timeframe: str, thesis: str,
                      entry_rules: list[str], exit_rules: list[str], position_sizing_rule: str,
                      risk_rules: list[str], data_requirements: list[str],
                      transaction_cost_assumption: str, slippage_assumption: str,
                      status: str = "IDEA", owner: str = "TRADING") -> dict[str, Any]:
    return {"schema_version": "nexus.trading-strategy.v2", "strategy_id": strategy_id,
            "name": name, "version": version, "asset_class": asset_class,
            "symbol_universe": symbol_universe, "timeframe": timeframe, "thesis": thesis,
            "entry_rules": entry_rules, "exit_rules": exit_rules,
            "position_sizing_rule": position_sizing_rule, "risk_rules": risk_rules,
            "data_requirements": data_requirements,
            "transaction_cost_assumption": transaction_cost_assumption,
            "slippage_assumption": slippage_assumption, "status": status, "owner": owner,
            "created_at": now(), "updated_at": now()}


def experiment_contract(*, experiment_id: str, strategy_id: str, hypothesis: str,
                        dataset: str, date_range: dict[str, str], in_sample_range: dict[str, str],
                        out_of_sample_range: dict[str, str], parameters: dict[str, Any],
                        cost_assumptions: dict[str, Any], slippage: Any,
                        success_criteria: list[str], failure_criteria: list[str],
                        code_version: str, data_version: str) -> dict[str, Any]:
    return {"schema_version": "nexus.trading-experiment.v2", "experiment_id": experiment_id,
            "strategy_id": strategy_id, "hypothesis": hypothesis, "dataset": dataset,
            "date_range": date_range, "in_sample_range": in_sample_range,
            "out_of_sample_range": out_of_sample_range, "parameters": parameters,
            "cost_assumptions": cost_assumptions, "slippage": slippage,
            "success_criteria": success_criteria, "failure_criteria": failure_criteria,
            "random_seed_if_relevant": None, "code_version": code_version,
            "data_version": data_version, "created_at": now()}


def risk_decision(*, signal_id: str, proposed_units: int, price: float,
                  max_position_units: int = 1000, current_exposure: float = 0,
                  max_exposure: float = 100_000) -> dict[str, Any]:
    proposed_notional = abs(proposed_units * price)
    allowed = abs(proposed_units) <= max_position_units and current_exposure + proposed_notional <= max_exposure
    return {"schema_version": "nexus.trading-risk-decision.v2", "signal_id": signal_id,
            "proposed_units": proposed_units, "price": price,
            "proposed_notional": proposed_notional, "max_position_units": max_position_units,
            "max_exposure": max_exposure, "decision": "PASS" if allowed else "REJECT",
            "reason": "within_limits" if allowed else "position_or_exposure_limit",
            "live_execution_allowed": False, "created_at": now()}


def paper_order(*, order_id: str, signal_id: str, instrument: str, side: str,
                units: int, price: float, fee_rate: float, slippage_rate: float) -> dict[str, Any]:
    fill_price = price * (1 + slippage_rate if side == "BUY" else 1 - slippage_rate)
    fee = abs(units * fill_price) * fee_rate
    return {"schema_version": "nexus.paper-order.v2", "order_id": order_id,
            "signal_id": signal_id, "instrument": instrument, "side": side,
            "units": units, "requested_price": price, "fill_price": fill_price,
            "fee": fee, "slippage_rate": slippage_rate, "status": "PAPER_FILLED",
            "live_execution": False, "created_at": now()}
