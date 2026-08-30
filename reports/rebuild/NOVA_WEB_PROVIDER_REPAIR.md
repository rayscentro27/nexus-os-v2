# Nova Web Provider Repair

The previous `provider=none` result was caused by the configured private
SearXNG endpoint refusing the connection and the available Brave credential
being payment-blocked (HTTP 402). The provider chain also had no credential-
free fallback.

The existing Hermes adapter now tries SearXNG and configured providers first,
then bounded public HTML search adapters. The development query `Tesla
strategy 2026` succeeded through `bing_html` with six results after the first
three routes did not produce results. No new framework or paid provider was
installed or activated.
