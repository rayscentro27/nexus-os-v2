# Research-to-Clyde Repository Audit

- Starting commit: `098dd1e9e1e23489ab6c8ac8440d37e08802267c`; branch: `main`.
- Existing credit path: live parser → verified JSONB → funding-impact review → bounded queue → admin/client adapters.
- Existing research path: general `research_sources`, Hermes Alpha inboxes, research exports, and a small outcome summarizer; no reusable credit-strategy approvals or claim separation.
- Existing `approved_client_guidance` is client-specific and unsuitable for once-per-strategy approval.
- Existing workbench decisions were session-only.
- Closed gaps: canonical accounts, objective discrepancies, source/claim separation, 25 strategies, matching, Strategy Cards, durable decisions/tools/outcomes, exception routing, bounded research processing.
- Unrelated dirty runtime, Alpha, Telegram, cache, and work-order files remain untouched.
