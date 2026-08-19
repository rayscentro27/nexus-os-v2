# Hermes Morning Brief Conversation Contract

Status: `MANUAL_REQUIRED`.

Hermes should answer `What happened overnight?` from the canonical Phase 16A brief, then retain the brief's opportunity references for `Tell me more about the most important opportunity` and `Why should I focus on that?`. The first action must respect the payment prerequisite: reconcile Stripe runtime keys to TEST before a downstream checkout.

Required evidence sources: `reports/phase16a/morning_brief_latest.json` plus the referenced loop ledger and blocker/revenue reports. No raw ledger dump is required unless Ray asks.
