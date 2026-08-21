# Nexus Options Trading Capability Audit

## Finding

Options are a real capability gap. A framework that can represent an option
contract is not automatically capable of accurately backtesting or managing an
options strategy. Nexus needs point-in-time chain data and lifecycle semantics
before any strategy claim is credible.

## Required capabilities

| Requirement | Nexus today | Candidate evidence |
|---|---|---|
| Calls/puts, strikes, expirations | MISSING canonical model | Nautilus instrument model is promising |
| Historical chains with bid/ask | MISSING | Requires licensed point-in-time source |
| IV and Greeks | MISSING portfolio service | Nautilus supports venue/tutorial Greeks; pricing library may supplement |
| Assignment/exercise/expiration | MISSING | Must be explicit simulator behavior, not inferred |
| Multi-leg/vertical/debit/credit spreads | MISSING | Nautilus documents option spread creation/loading/trading |
| Covered calls/CSPs | MISSING strategy templates | Build only after lifecycle model |
| Commissions/slippage/liquidity | PARTIAL policy concepts | Must be contract-level and dataset-backed |
| Portfolio Greeks/risk graph | MISSING | Requires portfolio risk service |
| Paper options trading | MISSING | Broker/data adapter and reconciliation required |

## Best framework candidate

**NautilusTrader** is the best broad open-source candidate to evaluate because
it combines multi-asset instruments, deterministic event-driven simulation,
venue adapters, option chains/Greeks, and option-spread support. It is not a
license to trade, and it does not remove the need for a reliable historical
data contract.

## Supplemental tooling

An options-specific portfolio backtester such as
[LambdaClass/options_portfolio_backtester](https://github.com/lambdaclass/options_portfolio_backtester)
is a useful research comparison because it advertises historical chains,
Greeks-aware risk, contract inventory, and pinned data provenance. It remains a
pilot candidate until license, dataset rights, lifecycle accuracy, and
maintenance are verified.

## Historical data requirement

For each timestamp Nexus needs the underlying, contract identity, strike,
expiration, call/put, bid/ask or executable quote, volume, open interest, IV or
inputs to recompute IV, Greeks convention, corporate actions, multiplier,
trading calendar, and survivorship/chain membership. A current chain endpoint
is not historical truth.

## Paper architecture

The paper engine must simulate fills, spreads, commissions, slippage, liquidity,
assignment, exercise, expiration, buying power, margin, and portfolio Greeks.
It returns a risk report and receipt. Broker adapters are read-only until an
independent approval and safety certification explicitly changes policy.
