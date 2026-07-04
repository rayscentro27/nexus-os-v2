# API Key Input Checklist

> INTERNAL ACTIVATION EVIDENCE — RAY REVIEW REQUIRED

| Connector | Required now | Input | Status / unlock |
|---|---|---|---|
| Supabase | No for Alpha/funnel | server/frontend env by approved pattern | writes gated |
| Netlify | Yes for live form verification | Netlify site settings | deploy/form capture |
| GitHub | existing push auth | gh credential store | source/CI |
| Cloudflare | No | server env | future tunnel |
| Resend/Meta/Stripe | No | server-only env | disabled external actions |
| GSC/Analytics | Optional now | server credentials/property | measured SEO |
| YouTube | Optional | `YOUTUBE_API_KEY` | current metadata |
| NotebookLM folder | Yes/local | `data/exports/notebooklm` | configured local research |
| Drive | Optional | server credentials/folder | manual exports |
| Oanda demo | No | server-only practice credentials | read verification only |
| Ollama local | Optional | dedicated local bridge | real local Alpha model |
| OpenRouter/Groq | Optional | server-only Alpha gateway | hosted Alpha model |
| Firecrawl/MarkItDown/n8n | Future | server/local config | research/automation evaluation |

Secret values were not read or printed.
