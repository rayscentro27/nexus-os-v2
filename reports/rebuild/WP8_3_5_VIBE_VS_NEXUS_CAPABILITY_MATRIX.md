# Vibe-Compatible Components vs Nexus

| Capability | Legacy/Vibe-compatible evidence | Canonical Nexus | Decision |
|---|---|---|---|
| Research/decomposition | strategy agent and Hermes review | Alpha + governed work orders | ADAPT concepts |
| Backtest | replay engine and simulator | deterministic Nexus/Python backtest | KEEP_NEXUS |
| Risk | position sizing, spread/limits | Nexus authority and paper-only safety | KEEP_NEXUS |
| Strategy memory | Supabase strategy tables/journal | Nexus strategy versions, metrics, receipts | ADAPT schema ideas |
| Multi-agent critique | researcher/reviewer separation | Alpha → Trading Engine → Nova | CONCEPT_ONLY |
| Execution | broker/API, auto executor, webhooks | OANDA Practice guarded lane | REJECT live paths |
| Recovery/receipts | legacy logs/journal | Nexus durable work/loop/receipts | KEEP_NEXUS |

Nexus remains the sole authority/state/control plane.

