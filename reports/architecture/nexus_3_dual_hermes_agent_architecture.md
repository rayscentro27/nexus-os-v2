# Nexus 3 Dual Hermes Agent Architecture Correction

Generated: 2026-07-21

## Starting Checkpoint

- Worktree: `/Users/raymonddavis/nexus-os-v2-hermes-language`
- Branch: `wave/hermes-model-first-language`
- Starting commit for this correction: `4e84cc7d50e619aaa62284e0988c280f6f8c233a`
- Production baseline: `a3643f5d50b6f6c8e07c14dc4862bbe10dee77e9`

## Old Routes

Nexus Hermes used the Supabase `hermes-chat` Edge Function in `model_first_conversation` mode, but still forced every turn into a JSON decision envelope before response generation. This caused tool-free writing and reference turns to be over-routed or degraded.

Hermes Alpha called `respondAsAlpha()` first in the UI and used the hosted provider only after deterministic local output and mode checks. The Alpha backend accepted a flat prompt and did not receive recent conversation history.

## New Routes

Nexus Hermes now uses native OpenRouter chat/tool calling in `runConversationalOpenRouter()`:

1. model receives Hermes identity, safe Nexus context, recent visible history, and approved tool definitions;
2. model returns normal assistant text or a native tool call;
3. tool calls pass `validateToolRequest()`;
4. approved tools execute server-side only;
5. safe tool result returns to the model for a natural final answer.

The prior JSON decision path remains in the file as legacy fallback code, but `model_first_conversation` now routes to the native conversational tool path.

Hermes Alpha now uses the hosted same-origin backend first when `VITE_ALPHA_MODEL_FIRST_MODE` is enabled and a hosted provider is available. The backend receives bounded history and constructs a proper message array with Alpha identity and safe static Nexus context. Alpha still has no Supabase, no client PII, and no execution authority.

## Provider And Model

- Nexus Hermes provider: OpenRouter
- Nexus Hermes primary model: `openai/gpt-4o-mini`
- Nexus Hermes fallback model: `google/gemini-2.0-flash-001`
- Alpha hosted provider tested: OpenRouter
- Alpha model tested: `openai/gpt-4o-mini`

## Architecture Comparison

Nexus comparison sample:

- legacy/default `conversation`: 6/10
- native `model_first_conversation`: 10/10

Alpha hosted model-first sample:

- hosted model with history: 10/10

## Certification Outcome

Nexus Hermes did not pass the 100-turn holdout. Ordinary conversation and writing improved to 100%, but current internal facts and governed actions still under-selected tools.

Alpha semantically passed the hosted model/history/Supabase-boundary evaluation. The literal scorer reported 94/100 because it failed to count Unicode contraction refusals such as “I don’t have access” as successful boundary refusals.

Final state: `NEXUS_HERMES_FAILED`
