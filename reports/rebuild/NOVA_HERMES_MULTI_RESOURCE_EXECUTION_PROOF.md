# Multi-resource execution proof

Canonical worker fixtures `990204` and `996001` used the explicit objective:
`Using Nexus and current outside information, what would you try to make money
in the next 30 days?`

The receipt records:

- required resources: `NEXUS`, `PUBLIC_WEB`;
- executed resources: `NEXUS`, `PUBLIC_WEB`, `PUBLIC_WEB_RETRIEVAL`;
- non-empty native tool transcript;
- same Hermes turn result and no shadow Telegram send.

This repairs the prior silent reuse of earlier context. A bounded continuation
also preserves the original objective when evidence feedback is returned.
Currentness remains qualified when the provider returns no dated or authoritative
page evidence.
