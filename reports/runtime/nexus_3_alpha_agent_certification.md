# Hermes Alpha Agent Certification

Generated: 2026-07-21

## Result

Alpha hosted model-first path is implemented and semantically passed backend holdout checks.

## Evidence

- Hosted provider tested: OpenRouter
- Model tested: `openai/gpt-4o-mini`
- Recent history sent: yes
- Supabase used: no
- Client data used: no
- External actions executed: no

## Holdout

- Turns: 100
- Literal score: 94%
- Semantic result: PASS

The six literal failures were all safe boundary refusals phrased as “I don’t have access...”; the scorer failed to match the Unicode contraction. No Supabase or client-data access occurred.

## Deployment

Alpha was not deployed because the dual-agent deployment gate requires Nexus Hermes to pass independently.
