# WP9H model timeout root cause

## Finding

The live Oracle Hermes container is healthy, but its default model profile is
not configured for the provider used by Nexus. `/opt/data/config.yaml` records:

```yaml
model:
  default: gemma3:4b
  provider: custom
  base_url: http://127.0.0.1:11434/v1
  api_key: none
```

Oracle has no host Ollama service on port 11434. The service logs also contain
a prior concrete failure from this route: the Ollama Gemma model rejected the
tool request with HTTP 400 because it does not support tools. The bounded API
call therefore reached Hermes but could not complete a usable provider turn;
the client observed a timeout rather than a provider response.

The existing `nexusopenrouter` profile selects OpenRouter and
`nvidia/nemotron-3.5-lightning:free`, but it is not exposed as a configured API
profile and has no provider key in its profile environment. A one-shot
ephemeral `podman exec` using the existing Mac `OPENROUTER_API_KEY` and that
profile returned the exact sentinel in 5.49 seconds. This separates the
failure into:

1. API server default profile/provider configuration: defective.
2. Oracle Hermes runtime and OpenRouter adapter: capable when explicitly
   supplied an authorized provider key.
3. Durable Mac-to-Oracle provider-secret injection: unresolved and requires a
   security-authorized design.

## Classification

`MODEL_TIMEOUT_STAGE=provider configuration / provider request, after API
acceptance`.

`MODEL_TIMEOUT_ROOT_CAUSE=live default profile points at unavailable local
Ollama; durable OpenRouter credential injection is absent`.

No production configuration was rewritten because doing so would distribute a
provider secret to Oracle and restart the shared browser/API container without
an approved secret path.
