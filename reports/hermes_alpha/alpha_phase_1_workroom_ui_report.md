# Hermes Alpha Phase 1 Workroom UI Report

The Workroom is mounted as a separate top-level `#alpha` page in the existing Nexus admin shell. It does not replace, wrap, or route through Nexus Hermes.

Added component: `src/components/HermesAlphaWorkroom.jsx`. Added navigation group: “Hermes Alpha — Separate.” The Nexus Hermes global launcher is hidden while the Alpha page is open to prevent identity confusion.

Visible badges: Offline, Draft Only, No Supabase, Mock Provider Only, External Actions Disabled, No Oanda Connected, and No Publishing/Sending/Charging/Trading.

Clickable: local buttons that navigate to the existing Reports center. Preview cards and Ray Review proposal controls are disabled. There is no chat/provider execution, publish, send, charge, trade, Oanda, Supabase, Research Vault, client, scheduler, or production-action control.

Panels: overview, fixture evaluation metrics/results, Opportunity Desk, Marketing Asset Studio, Affiliate/Offer Lab, Newsletter, Landing Page, Social Content, Trading Research Lab, disabled future Oanda desk, report links, and conversation-only Ray Review proposal preview.

The displayed 11/11 result is deterministic fixture evaluation only and is labeled as such. It is not production status or real performance.
