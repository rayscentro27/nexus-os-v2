# Payment Repository Concept Extraction

Generated: 2026-06-29T18:31:43.129984+00:00

- ok: true
- status: static_concept_extraction_complete
- targets: 6
- concepts_created: 21
- recommendations_created: 4
- approval_cards_created: 1
- repositories_installed: false
- containers_started: false
- github_network_access_performed: false
- external_action_performed: false

## Targets

- `{"concepts": ["payment orchestration", "multi-processor routing", "webhook reliability", "vault boundaries"], "id": "hyperswitch", "name": "Juspay Hyperswitch", "url": "https://github.com/juspay/hyperswitch"}`
- `{"concepts": ["self-hosted checkout", "invoice state machine", "crypto payments later", "webhook events"], "id": "btcpayserver", "name": "BTCPay Server", "url": "https://github.com/btcpayserver/btcpayserver"}`
- `{"concepts": ["hosted payment fields", "tokenization", "sample checkout flows", "PCI boundaries"], "id": "globalpayments-samples", "name": "Global Payments official samples", "url": "https://github.com/globalpayments"}`
- `{"concepts": ["gateway adapters", "idempotency", "provider abstraction"], "id": "payment-gateway-topic", "name": "GitHub payment-gateway topic", "url": "https://github.com/topics/payment-gateway"}`
- `{"concepts": ["payment links", "checkout lifecycle", "conversion tracking"], "id": "payment-links-topic", "name": "GitHub payment-links topic", "url": "https://github.com/topics/payment-links"}`
- `{"concepts": ["order/payment separation", "receipts", "reconciliation"], "id": "point-of-sale-topic", "name": "GitHub point-of-sale topic", "url": "https://github.com/topics/point-of-sale"}`

## Recommendations

- `{"decision": "Stripe test Checkout, verified webhooks, idempotent onboarding", "id": "payment-stack-stripe-first", "phase": "now", "title": "Keep Stripe as first operational processor"}`
- `{"decision": "Use Hyperswitch concepts only after paid volume justifies complexity", "id": "payment-stack-orchestration-later", "phase": "later", "title": "Evaluate processor abstraction later"}`
- `{"decision": "BTCPay concepts remain roadmap-only", "id": "payment-stack-crypto-later", "phase": "later", "title": "Defer crypto checkout"}`
- `{"decision": "Hosted checkout/tokenization only", "id": "payment-stack-pci-boundary", "phase": "now", "title": "Keep card data outside Nexus"}`
