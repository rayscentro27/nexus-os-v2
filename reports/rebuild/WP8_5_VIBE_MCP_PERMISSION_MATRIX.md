# Vibe MCP Permission Matrix

| Capability | Alpha trading research | Nexus authority |
|---|---:|---:|
| Research/read, market data, quant analytics, regime/options/crypto analytics | allow when a real endpoint is provisioned | Nexus records evidence |
| Strategy evidence, journal/shadow analysis | allow read-only | Nexus owns strategy/experiment state |
| Order placement, broker write, live execution | deny | none |
| Shell, credential mutation, system mutation, unknown writes | deny | none |

The matrix is defined in `multi_market_lab.py`; no external framework receives the control plane.
