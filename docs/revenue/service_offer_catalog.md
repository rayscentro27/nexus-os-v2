# Controlled Service Offer Catalog

Phase 6 adds three one-time, approval-gated GoClear readiness services. The public catalog is in `src/config/serviceOfferCatalog.ts`; `service_offers` is the persisted server-side catalog used for checkout pricing.

| Offer | Price | Scope | Consultation |
|---|---:|---|---|
| Credit & Funding Readiness Review | $97 | Snapshot, credit/business findings, prioritized actions, document-gap review | None by default |
| Readiness Action Plan | $297 | $97 scope plus detailed corrective plan, checklist, strategy review | One review session |
| Funding Readiness Concierge | $497 | $297 scope plus deeper document/bankability review, guided support, follow-up, priority review | Priority consultation/support |

All prices are USD, one-time service prices, and test-mode eligible. The browser may display the catalog but cannot set the amount. The checkout function resolves the active offer and amount from `service_offers`.

Every offer states that results depend on information and documentation, does not guarantee funding approval, credit deletion, score increases, financing, limits, or timelines, and does not provide legal advice. Third-party decisions remain outside Nexus control.

Terms, refund-policy, privacy-notice, readiness scope, and fulfillment type are versioned fields. Offer activation is separate from live payment enablement.
