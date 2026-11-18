# Connecting the Contabo OpenCode harness to the Kaggle REA model worker

Placeholders only — no secret values. Syntax verified against OpenCode **1.19.5** (latest stable; no stable 2.x
exists) on the Contabo `nexus-rea` container (`opencode debug config` accepted it, `enabled_providers` honoured).

## 1. What OpenCode needs (rendered by `rea_harness.py` from `model_provider.json`)

```json
{
  "enabled_providers": ["nexus_rea_model"],
  "model": "nexus_rea_model/rea-default",
  "provider": {
    "nexus_rea_model": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Nexus REA model",
      "options": {
        "baseURL": "${NEXUS_REA_MODEL_BASE_URL}",
        "apiKey": "{env:NEXUS_REA_MODEL_API_KEY}"
      },
      "models": {
        "rea-default": {
          "id": "${NEXUS_REA_MODEL_NAME}",
          "tool_call": true,
          "limit": { "context": 65536, "output": 4096 }
        }
      }
    }
  }
}
```

`{env:NEXUS_REA_MODEL_API_KEY}` is OpenCode's environment substitution; the harness injects the key from
`/rea/config/secrets/nexus_rea_model.key` (0600) at session start and never writes it to job artifacts.

## 2. What to edit on Contabo (`/opt/nexus-app-services/rea/config/model_provider.json`)

```json
{
  "status": "READY",
  "base_url": "<MODEL_ENDPOINT from the Kaggle run, ending in /v1>",
  "model_name": "<MODEL_NAME from the Kaggle run>",
  "context_length": 65536,
  "output_limit": 4096,
  "tool_calling": true,
  "json_mode": true,
  "cost_class": "FREE",
  "api_key_ref": "/rea/config/secrets/nexus_rea_model.key"
}
```

The key file content must equal the Kaggle secret `NEXUS_REA_MODEL_API_KEY` attached to the notebook.
Switching models later changes only the Kaggle Cell 1 `MODEL_*` block and `model_name` here — never the REA MCP.

## 3. Known sizing note

The harness advertises ~213 REA MCP tools. Even with REA's compact schema profile this is a large prompt; the
`CONNECT_CONTABO_OPENCODE_TO_KAGGLE_MODEL_R1` task must measure the real prompt size and, if needed, narrow the
REA agent's enabled tools to fit `context_length`.
