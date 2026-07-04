# Hermes Alpha Success Sprint

Alpha is now a provider-aware strategy workspace rather than a deterministic-only preview. Ray’s provider selection persists locally. Deterministic and Ollama remain cost-safe options; Groq and OpenRouter use one same-origin backend model call per message and fall back visibly. Search is separate, off by default, backend-only, single-call, and capped at five results. No search connector is claimed available until an approved SearXNG URL is configured. No Supabase, client data, or external actions were added.

The UI now exposes provider/cost/search controls, daily usage, memory/source truth, compact response traces, an internal transcript scroller, and a sticky composer. The global Alpha header is separate from Nexus Hermes.
