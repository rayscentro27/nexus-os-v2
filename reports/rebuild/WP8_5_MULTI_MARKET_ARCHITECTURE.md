# Multi-Market Architecture

`multi_market_lab.py` implements generic adapters for FOREX, CRYPTO, and OPTIONS, with paper capability and `live_authority=NONE`. Forex maps OANDA Practice, pip/spread/next-completed-bar semantics. Crypto is a 24/7 paper/simulation foundation without live credentials. Options support underlying/contract fields and validated multi-leg positions with premium-at-risk/defined-risk semantics.

Strategy family, market, instrument, timeframe, regime, parameters, and risk model are separate experiment dimensions. No unsupported market is claimed integrated.
