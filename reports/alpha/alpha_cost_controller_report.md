# Alpha Cost Controller v1

Modes: Cheap (local), Fast (Groq), Strategy (OpenRouter), Search (maximum five results), and locked Deep Mode. Default maximum hosted calls is 25/day; search requests are capped at 10/day. Each message permits at most one hosted call and one search call. No autonomous loop exists.

Local/hosted/search counts, estimated input/output/total tokens, estimate-only spend, blocked Deep calls, fallbacks, cache hits, and per-provider use persist locally by day. Unknown provider pricing is labeled `unknown estimate`, never a confirmed charge.
