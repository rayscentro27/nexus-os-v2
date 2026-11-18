#!/usr/bin/env python3
"""Deterministic expiration payoff scenarios; not historical market performance."""
import json

def payoff(spot, center, wing, credit, multiplier=100):
    short_call=center+2; long_call=short_call+wing; short_put=center-2; long_put=short_put-wing
    # Compact symmetric iron-condor payoff from one call spread plus one put spread.
    call_loss=max(0.0, spot-short_call)-max(0.0, spot-long_call)
    put_loss=max(0.0, short_put-spot)-max(0.0, long_put-spot)
    return round((credit-call_loss-put_loss)*multiplier, 2)

def main():
    cfg={"underlying":"SPY","dte_entry":[30,45],"short_delta_target":0.15,"wing_width_usd":5.0,
         "entry_filter":"IV percentile >= 30; skip scheduled CPI/FOMC release day","profit_take_fraction":0.50,
         "time_exit_dte":21,"loss_exit_multiple_of_credit":2.0,"max_account_risk_fraction":0.01,
         "assumed_credit_usd_per_share":1.20,"scenario_center":500.0}
    # Illustrative settlement grid only: the assumed credit is a test input, not a quote.
    points=[490,495,498.8,500,501.2,505,510]
    rows=[{"settlement_spot":p,"pnl_usd_per_contract":payoff(p,500,5,1.20)} for p in points]
    max_loss=(5-1.20)*100
    result={"method":"THEORETICAL_EXPIRATION_SCENARIO_TEST","historical_option_data_used":False,
            "market_quotes_used":False,"live_or_paper_orders":False,"assumed_credit_not_market_quote":True,
            "specification":cfg,"max_loss_usd_per_contract":max_loss,
            "one_contract_risk_at_50000_account_fraction":max_loss/50000,
            "scenarios":rows,"assertions":{"worst_case_loss_bounded":max(r["pnl_usd_per_contract"] for r in rows)>=-max_loss,
            "center_spot_profit_equals_credit":payoff(500,500,5,1.2)==120,
            "tail_loss_does_not_exceed_defined_max":min(r["pnl_usd_per_contract"] for r in rows)>=-max_loss}}
    assert all(result["assertions"].values())
    print(json.dumps(result,indent=2))
if __name__=="__main__": main()
