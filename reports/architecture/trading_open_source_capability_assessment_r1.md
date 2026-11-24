# TRADING_OPEN_SOURCE_CAPABILITY_ASSESSMENT_R1

Date: 2026-11-15 · Scope: first-pass, bounded, read-only · Paid services: none

## Evidence method
GitHub REST metadata, LICENSE files, top-level and module source trees, and READMEs/ADAPTERS docs fetched read-only (unauthenticated curl) on 2026-11-15. Nothing was cloned, built, installed, or executed. REA/Contabo was not used: repo-tree and license inspection did not need model-driven analysis. Where a statement comes from prior knowledge of the project rather than a file read this session, it is marked (K).

| Project | License (verified) | Lang | Stars | Last push | Key tree evidence |
|---|---|---|---|---|---|
| NautilusTrader | LGPL-3.0 (+ CLA.md, TRADEMARK.md) | Rust core, Python via PyO3 | 31.6k | 2026-11-15 | crates/: core, model, data, execution, risk, portfolio, trading, backtest, live, persistence, event_store, adapters, plugin. Mid **v1→v2 migration** (MIGRATION_V2.md; v1 security backports only) |
| QuantConnect LEAN | Apache-2.0 | C# (+ Python algos) | 22.5k | 2026-11-15 | Engine, Brokerages (Paper, Backtesting), Common/Securities: Equity, Forex, Option, IndexOption, Future, FutureOption, Crypto, CryptoFuture, Cfd, margin/buying-power/settlement models, Optimizer. Separate Lean.Brokerages.OANDA repo exists |
| OpenAlgo | AGPL-3.0 | Python (Flask) | 3.0k | 2026-11-14 | broker/: ~35 adapters, all **Indian** brokers (Zerodha, Angel, Dhan, Fyers, Upstox…) + Delta Exchange. sandbox/ (order/position/fund/squareoff managers), services/risk, mcp/mcpserver.py, flow_* (n8n-like) services, option greeks/IV/GEX services |
| OpenBB | Apache-2.0 (LICENSE file; GitHub shows NOASSERTION) | Python | 75.4k | 2026-11-15 | openbb_platform/extensions: equity, etf, derivatives, crypto, currency, economy, fixedincome, news, quantitative, technical, **mcp_server**, platform_api. Providers in-repo are mostly free/public (FRED, SEC, CBOE, BLS, ECB, IMF, OECD, Deribit, FINRA, Nasdaq) |
| Freqtrade | GPL-3.0 | Python | 56.9k | 2026-11-15 | freqtrade/: exchange (CCXT), strategy, optimize (backtest/hyperopt), persistence, rpc (Telegram/REST/webUI), plugins/protections (MaxDrawdown, StoplossGuard, Cooldown, LowProfitPairs), freqai, dry-run |

Critical fact for the current plan: **NautilusTrader has no OANDA adapter** (ADAPTERS.md and crates/adapters checked; FX only via Interactive Brokers). **LEAN has an OANDA brokerage** (separate repo). **OpenAlgo has no US/FX broker.**

## Phase 2 — NautilusTrader
- NAUTILUS_CORE_KERNEL_FIT=HIGH (event-driven, deterministic core with crates for message bus, cache, data/exec/risk engines, portfolio)
- NAUTILUS_RISK_FIT=MEDIUM (pre-trade RiskEngine: trading state ACTIVE/REDUCING/HALTED, max order rate, max notional per order (K); no portfolio daily-loss/drawdown governor out of the box — Nexus must add it)
- NAUTILUS_EXECUTION_FIT=MEDIUM (strong order/position state machine, reconciliation on startup (K); but **no OANDA adapter** → Forex paper path would require writing a custom adapter)
- NAUTILUS_BACKTEST_FIT=HIGH (nanosecond event-driven, same code backtest/live)
- NAUTILUS_MULTI_ASSET_FIT=HIGH in model; adapters are crypto/IB/prediction-market heavy
- NAUTILUS_DEPLOYMENT_FIT=MEDIUM (prebuilt wheels, no Rust needed to install; 1 live node fits Contabo; but v2 migration churn and MSRV=latest stable Rust mean ongoing upgrade cost)
- NAUTILUS_LICENSE=LGPL-3.0 (+CLA for contributions)
- NAUTILUS_CLASSIFICATION=ADAPT (use as library/reference kernel; deep-dive before any commitment)

## Phase 3 — LEAN
- LEAN_BACKTEST_FIT=HIGH
- LEAN_OPTIONS_FIT=HIGH (option/index-option/future-option securities, assignment/exercise, Greeks/IV models (K))
- LEAN_MULTI_ASSET_FIT=HIGH (Equity, Forex, Option, Future, Crypto, CFD, settlement and margin models)
- LEAN_EXECUTION_FIT=MEDIUM (OANDA/IB/Alpaca brokerages exist, but running LEAN live means adopting a .NET runtime as the trading core)
- LEAN_CROSS_ENGINE_VALIDATION_FIT=HIGH (independent engine for re-running frozen strategies and comparing fills/P&L)
- LEAN_KAGGLE_FIT=MEDIUM (Docker image is the supported path; Kaggle has no Docker — needs .NET install in notebook; CPU-bound, GPU unused; data must be supplied in LEAN format, QC data library is paid)
- LEAN_LICENSE=Apache-2.0
- LEAN_CLASSIFICATION=ADAPT (as offline backtest/options validator, not as live core)

## Phase 4 — OpenAlgo
- OPENALGO_BROKER_PATTERN_FIT=MEDIUM (uniform per-broker module layout: api/mapping/database/streaming (K))
- OPENALGO_EXECUTION_PATTERN_FIT=MEDIUM (place/modify/cancel/smart/basket/split order services; order_router)
- OPENALGO_RISK_PATTERN_FIT=LOW-MEDIUM (services/risk + scalping_risk_monitor + squareoff manager; simple)
- OPENALGO_OPTIONS_PATTERN_FIT=MEDIUM (greeks, IV smile, vol surface, GEX, straddle — Indian F&O conventions)
- OPENALGO_UI_PATTERN_FIT=MEDIUM
- OPENALGO_N8N_MCP_FIT=MEDIUM (mcpserver.py; flow executor/scheduler services)
- OPENALGO_US_MARKET_FIT=NONE (no US or FX broker; Indian exchange symbology)
- OPENALGO_LICENSE=AGPL-3.0 (network-use copyleft)
- OPENALGO_CLASSIFICATION=REFERENCE_ONLY

Sandbox separation pattern (sandbox/ with its own order/position/fund managers, session boundary, squareoff) is the most transferable idea — read it, don't copy it.

## Phase 5 — OpenBB
- OPENBB_MARKET_DATA_FIT=MEDIUM (aggregation layer; quality depends on provider — many free providers are delayed/EOD)
- OPENBB_OPTIONS_DATA_FIT=MEDIUM (CBOE/derivatives chains; not tick-grade)
- OPENBB_MACRO_FIT=HIGH (FRED, BLS, ECB, IMF, OECD, Fed, EIA, CFTC)
- OPENBB_RESEARCH_FIT=HIGH
- OPENBB_EXECUTION_FIT=NONE
- OPENBB_NEXUS_DATA_LAYER_FIT=MEDIUM (feed Trading Research, not the execution data path; has its own MCP server)
- OPENBB_LICENSE=Apache-2.0 (per-provider data terms still apply)
- OPENBB_CLASSIFICATION=REUSE (research/macro data feed, as a dependency)

## Phase 6 — Freqtrade
- FREQTRADE_CRYPTO_FIT=HIGH
- FREQTRADE_BACKTEST_FIT=HIGH (crypto only; fees, lookahead/recursive analysis tooling (K))
- FREQTRADE_EXECUTION_FIT=HIGH for crypto spot/futures via CCXT
- FREQTRADE_EXCHANGE_FIT=HIGH (Binance, Bybit, Kraken, OKX, Hyperliquid, …)
- FREQTRADE_RISK_FIT=MEDIUM (protections plugins: MaxDrawdown, StoplossGuard, Cooldown; stoploss/ROI)
- FREQTRADE_NEXUS_SUBSYSTEM_FIT=MEDIUM (could run as an isolated crypto sidecar controlled over its REST API; would not share Nexus contracts)
- FREQTRADE_LICENSE=GPL-3.0
- FREQTRADE_CLASSIFICATION=WRAP later / REFERENCE now (Crypto=NONE in Nexus; defer)

## Phase 7 — Gap matrix (0 none · 1 reference · 2 component/pattern · 3 strong reuse)

| Capability | Nexus | Nautilus | LEAN | OpenAlgo | OpenBB | Freqtrade |
|---|---|---|---|---|---|---|
| Market Data | early/fragmented | 2 | 2 | 1 | 2 | 2 |
| Strategy Registry | missing | 1 | 1 | 1 | 0 | 1 |
| Strategy Runtime | fragmented | 3 | 2 | 1 | 0 | 2 |
| Signal Engine | non-deterministic | 2 | 2 | 1 | 0 | 1 |
| Risk Engine | missing | 2 | 2 | 1 | 0 | 1 |
| Backtesting | unproven | 3 | 3 | 0 | 0 | 2 |
| Walk-forward/OOS | missing | 1 | 2 | 0 | 0 | 1 |
| Optimization | missing | 1 | 2 | 0 | 0 | 2 |
| Portfolio State | missing | 3 | 2 | 1 | 0 | 1 |
| Order State | missing | 3 | 2 | 1 | 0 | 1 |
| Position State | missing | 3 | 2 | 1 | 0 | 1 |
| Execution | early (OANDA) | 1 | 2 | 1 | 0 | 2 |
| Reconciliation | missing | 2 | 1 | 1 | 0 | 1 |
| Journal | missing | 1 | 1 | 1 | 0 | 1 |
| Performance Analytics | missing | 2 | 2 | 1 | 1 | 2 |
| Options | early | 1 | 3 | 1 | 2 | 0 |
| Forex | early | 1 | 2 | 0 | 1 | 0 |
| Crypto | none | 2 | 1 | 0 | 1 | 3 |
| Equities | early | 2 | 2 | 0 | 2 | 0 |
| Broker Abstraction | missing | 2 | 2 | 1 | 0 | 1 |
| UI | n/a | 0 | 0 | 1 | 1 | 1 |
| n8n Integration | present (Contabo) | 0 | 0 | 1 | 0 | 1 |
| MCP/AI Integration | present (Nova/Hermes) | 0 | 0 | 1 | 2 | 0 |

Nautilus execution/forex score is held at 1 because it has no OANDA adapter.

## Phase 8 — Placement
- NAUTILUS_TARGET_LOCATION=REFERENCE_ONLY now; CONTABO (single live node, ~0.5–1 GiB) + KAGGLE (backtests) only if a deep dive is adopted
- LEAN_TARGET_LOCATION=KAGGLE (burst validation/options backtests); never Contabo (.NET + data footprint against 7.8 GiB/no swap)
- OPENALGO_TARGET_LOCATION=REFERENCE_ONLY
- OPENBB_TARGET_LOCATION=CONTABO-light (library calls inside existing Research jobs, cached into SUPABASE) — no always-on OpenBB server needed
- FREQTRADE_TARGET_LOCATION=REFERENCE_ONLY now; CONTABO dry-run container later if Crypto is approved (Freqtrade alone is ~300–600 MB)

## Phase 9 — Licensing boundary (not legal advice; reflects license text only)
| Project | DIRECT_CODE_REUSE_SAFE | INTEGRATION_SAFE | ARCHITECTURE_REFERENCE_SAFE | LICENSE_CONSTRAINTS |
|---|---|---|---|---|
| Nautilus | NO for copying into proprietary files | YES as an unmodified, separately installed library (LGPL) | YES | LGPL-3.0: modifications to Nautilus itself must be released under LGPL; users must be able to replace the library. Trademark policy. |
| LEAN | YES with attribution/NOTICE | YES | YES | Apache-2.0: keep license + NOTICE, state changes. Patent grant. |
| OpenAlgo | NO | NO for a network-served Nexus component | YES (ideas only) | AGPL-3.0: running modified code as a network service triggers source disclosure for the combined work. Highest contamination risk. |
| OpenBB | YES with attribution | YES | YES | Apache-2.0 code; individual data providers carry their own ToS/redistribution limits. |
| Freqtrade | NO into proprietary code | Separate process over REST only (arm's length) | YES | GPL-3.0: linking/importing in a distributed derivative makes it GPL; keep it a separate program. |

## Phase 10 — Build vs integrate vs reference
| Component | Recommendation |
|---|---|
| Event bus | BUILD_NEXUS_NATIVE (durable job/dispatcher already exists); REFERENCE_DESIGN Nautilus message bus |
| Market data | BUILD_NEXUS_NATIVE for OANDA execution feed; INTEGRATE_EXISTING OpenBB for research/macro |
| Strategy runtime | BUILD_NEXUS_NATIVE (thin) — REFERENCE_DESIGN Nautilus Strategy/Actor lifecycle |
| Risk engine | BUILD_NEXUS_NATIVE — REFERENCE_DESIGN Nautilus RiskEngine states + Freqtrade protections |
| Execution engine | BUILD_NEXUS_NATIVE (OANDA practice) — REFERENCE_DESIGN Nautilus order FSM / OpenAlgo sandbox split |
| Backtest engine | DEFER own engine; WRAP_EXISTING LEAN (or Nautilus) on Kaggle as validator |
| Options simulation | DEFER; then WRAP_EXISTING LEAN |
| Crypto execution | DEFER; then WRAP_EXISTING Freqtrade (separate process) |
| Broker abstraction | BUILD_NEXUS_NATIVE interface — REFERENCE_DESIGN LEAN IBrokerage / Nautilus ExecutionClient |
| Journal | BUILD_NEXUS_NATIVE (Supabase) |
| Portfolio state | BUILD_NEXUS_NATIVE — REFERENCE_DESIGN Nautilus/LEAN portfolio models |
| UI | DEFER (Nova summaries suffice) |
| Analytics | BUILD_NEXUS_NATIVE (expectancy, slippage, duration); REFERENCE_DESIGN Nautilus analysis / Freqtrade stats |

## Phase 11 — Ranking (0–100)
| Rank | Project | Score | Rationale |
|---|---|---|---|
| 1 | NautilusTrader | 72 | Best architectural match to the missing core (risk/order/position/portfolio/reconciliation, backtest-live parity). Penalized: no OANDA, v2 migration churn, LGPL boundary, Rust MSRV pace. |
| 2 | LEAN | 66 | Best multi-asset/options simulator, Apache-2.0, has OANDA. Penalized: .NET runtime, heavy, data in LEAN format, poor Contabo fit. Best as Kaggle validator. |
| 3 | OpenBB | 55 | Clean Apache-2.0 research/macro/options-data layer with MCP; zero execution value. |
| 4 | Freqtrade | 48 | Strongest crypto stack, but Crypto=NONE and not on the current plan; GPL keeps it at arm's length. |
| 5 | OpenAlgo | 30 | Good sandbox/MCP/flow patterns, but Indian-only brokers and AGPL. |

## Phase 12 — Deep-dive decision (not started)
1. PROJECT=NautilusTrader
   - WHY_DEEP_DIVE: only candidate that could serve as the trading kernel; the build-vs-integrate decision depends on it.
   - QUESTIONS_TO_ANSWER: Can v2 Python/PyO3 run a live node with a custom OANDA ExecutionClient/DataClient, and at what effort? Is RiskEngine extensible for daily-loss/drawdown/kill-switch? Is the cache/persistence (Redis/Postgres) compatible with Supabase as authority, or does it compete? What does startup reconciliation actually guarantee? How stable is the v2 API (release cadence, breaking changes)? What is the memory footprint on Contabo?
   - EXPECTED_VALUE: a go/no-go on "integrate kernel" vs "reference design"; if go, it removes ~60% of the core build.
2. PROJECT=QuantConnect LEAN
   - WHY_DEEP_DIVE: cheapest route to independent backtest validation and future options simulation.
   - QUESTIONS_TO_ANSWER: Can LEAN run headless on Kaggle without Docker? What is the minimal data format for OANDA FX bars? Can a frozen Nexus strategy spec be translated to a LEAN algorithm mechanically? Options Greeks/assignment fidelity?
   - EXPECTED_VALUE: a cross-engine check for the paper certification and a ready path for options.

## Phase 13 — Impact on current minimum paper path
- CAN_EXISTING_PROJECT_ACCELERATE_SIGNAL_LAYER=PARTIAL (design patterns only)
- CAN_EXISTING_PROJECT_ACCELERATE_RISK_LAYER=PARTIAL (Nautilus RiskEngine states + Freqtrade protections as design)
- CAN_EXISTING_PROJECT_ACCELERATE_EXECUTION_LAYER=NO for OANDA (Nautilus has no adapter; LEAN would require adopting .NET live core)
- CAN_EXISTING_PROJECT_ACCELERATE_STATE_LAYER=PARTIAL (order/position FSM design from Nautilus)
- CAN_EXISTING_PROJECT_ACCELERATE_BACKTESTING=YES (LEAN or Nautilus offline on Kaggle)
- CAN_EXISTING_PROJECT_ACCELERATE_OPTIONS=YES later (LEAN)
- CAN_EXISTING_PROJECT_ACCELERATE_CRYPTO=YES later (Freqtrade sidecar)

Decision: **D. hybrid**. In practice that means Nexus-native for the live paper path, with open-source used for validation and reference. No current-plan change is required: the minimum paper path stays OANDA-native, and backtest validation is added as an optional step.

## Final report
```
TRADING_OPEN_SOURCE_CAPABILITY_ASSESSMENT_R1=COMPLETE
NAUTILUS_CLASSIFICATION=ADAPT          NAUTILUS_SCORE=72
LEAN_CLASSIFICATION=ADAPT              LEAN_SCORE=66
OPENALGO_CLASSIFICATION=REFERENCE_ONLY OPENALGO_SCORE=30
OPENBB_CLASSIFICATION=REUSE            OPENBB_SCORE=55
FREQTRADE_CLASSIFICATION=REFERENCE_ONLY (WRAP when Crypto approved) FREQTRADE_SCORE=48
RANK_1=NautilusTrader
RANK_2=QuantConnect LEAN
RANK_3=OpenBB
RANK_4=Freqtrade
RANK_5=OpenAlgo
BEST_TRADING_CORE_CANDIDATE=NautilusTrader
BEST_BACKTEST_CANDIDATE=LEAN (validator) / NautilusTrader (parity with live)
BEST_OPTIONS_CANDIDATE=LEAN
BEST_CRYPTO_CANDIDATE=Freqtrade
BEST_MARKET_DATA_CANDIDATE=OpenBB (research/macro); OANDA native for execution data
BEST_BROKER_PATTERN_REFERENCE=NautilusTrader ExecutionClient / LEAN IBrokerage
RECOMMENDED_DEEP_DIVE_1=NautilusTrader
RECOMMENDED_DEEP_DIVE_2=QuantConnect LEAN
RECOMMENDED_ARCHITECTURE=HYBRID: Nexus-native live paper core (contracts, risk gate, OANDA execution, Supabase state, journal) designed against Nautilus's domain model; LEAN on Kaggle as offline validator; OpenBB as Research data feed
CURRENT_TRADING_PLAN_CHANGE_REQUIRED=NO
TRADING_RECOVERY_APPROACH=D (hybrid; Nexus-native live path)
NEXUS_NATIVE_COMPONENTS=contracts, strategy registry/versioning, deterministic signal, risk gate + kill switch, OANDA practice execution with idempotency/receipts/retries, order/position state + reconciliation, journal, performance analytics, Nova summary
INTEGRATED_COMPONENTS=OpenBB (research/macro data); later LEAN (Kaggle validation/options), Freqtrade (crypto sidecar)
REFERENCE_ONLY_COMPONENTS=Nautilus order/position FSM, RiskEngine states, message bus; OpenAlgo sandbox/live split and MCP/flow patterns; Freqtrade protections
KNOWN_LICENSE_CONSTRAINTS=Nautilus LGPL-3.0 (library use only; mods to it are LGPL); OpenAlgo AGPL-3.0 (no code reuse; network copyleft); Freqtrade GPL-3.0 (separate process only); LEAN/OpenBB Apache-2.0 (attribution+NOTICE); OpenBB provider data ToS
KNOWN_RESOURCE_CONSTRAINTS=Contabo 4 vCPU/7.8 GiB/no swap shared with n8n+Postiz+REA (2.5 GiB cap) → at most one light trading worker; LEAN/heavy backtests go to Kaggle (ephemeral, no Docker); Mac mini dev-only
PAID_SERVICES_USED=NO
FINAL_RESULT=ASSESSMENT_COMPLETE
NEXT_ACTION=TRADING_ENGINE_RECOVERY_AND_PAPER_CERTIFICATION_R1 (with DEEP_DIVE_TOP_TRADING_CANDIDATE for Nautilus run in parallel/after, non-blocking)
```
