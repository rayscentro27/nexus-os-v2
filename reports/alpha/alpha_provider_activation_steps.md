# Alpha Provider Activation Steps

## Ollama local — recommended first

1. Start Ollama and confirm `curl http://127.0.0.1:11434/api/tags`.
2. Run `npm run dev`.
3. Open `/#alpha`; confirm `ollama_local — available`.
4. Select it and test non-client business prompts.

## Groq

Add `GROQ_API_KEY` and optional `ALPHA_GROQ_MODEL` to Netlify server environment, deploy, verify `/api/alpha/status`, then select Groq. Never use a `VITE_` key.

## OpenRouter

Add `OPENROUTER_API_KEY` and optional `ALPHA_OPENROUTER_MODEL` to Netlify server environment, deploy, verify `/api/alpha/status`, then select OpenRouter. Never use a `VITE_` key.

## Live web

Requires a separate public-search/news server connector with citations and freshness controls. It is not configured by this sprint.
