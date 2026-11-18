"""Nexus Trading Core R1 — Forex paper vertical slice.

Pipeline: frozen strategy version -> deterministic signal -> central risk gate
-> OANDA Practice adapter -> order/position state -> reconciliation -> trade
journal -> performance -> Nova summary contract.

PRACTICE ONLY. Live trading is hard-disabled at the contract, risk, and
adapter layers. AI/Research may recommend strategies; only deterministic
strategy code may emit a signal, and only an approved risk event may reach the
broker adapter.
"""

LIVE_TRADING_ENABLED = False
TRADING_MODE = "PAPER"
CORE_VERSION = "trading-core-r1"
