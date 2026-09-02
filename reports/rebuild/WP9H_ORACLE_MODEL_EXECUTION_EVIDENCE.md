# WP9H Oracle model execution evidence

## Real bounded probes

- Existing container: `nexus-hermes-0206`.
- Runtime: Hermes Agent `0.20.6`, Oracle, existing image/container.
- API health: authenticated HTTP 200, response version `0.20.6`.
- Ephemeral model route: OpenRouter profile, existing Mac-authorized
  `OPENROUTER_API_KEY` supplied over encrypted SSH/stdin and never persisted.
- Prompt: `Respond with exactly: ORACLE_HERMES_MODEL_OK`.
- Result: exact sentinel returned, exit 0, elapsed 5.49 seconds.
- Cash commitment: no new account, subscription, or purchase; provider usage
  accounting remains UNKNOWN for this probe.

## Honest certification boundary

`ORACLE_HERMES_MODEL_EXECUTION=PASS_REAL_EPHEMERAL_RUNTIME` is proven.
`ORACLE_HERMES_MODEL_EXECUTION=PASS_REAL_DURABLE_API_ROUTE` is **not** proven.

The production API default remains pointed at unavailable local Ollama, and the
Mac bridge has no durable authorized API credential. This is insufficient for
Telegram cutover.
