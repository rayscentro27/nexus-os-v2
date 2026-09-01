# Experiment Generator

`TradingExperimentGenerator` is represented by deterministic `ExperimentSpec` plus `bounded_specs()` and stable SHA-256 IDs. Dimensions include family, market, instrument, timeframe, regime, indicator parameters, transaction cost, risk, and money management. The initial tournament is bounded to three candidates; each includes parameter perturbations and four money-management comparisons.
