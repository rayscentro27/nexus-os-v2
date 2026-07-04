# Open-Source Repo Scout for Alpha and Nexus

> INTERNAL ACTIVATION EVIDENCE — RAY REVIEW REQUIRED

| Candidate | Category | License* | Hosting | Complexity | Decision | Nexus fit/risk |
|---|---|---|---|---|---|---|
| LangGraph | agent orchestration | MIT | self-host | medium | evaluate later | Possible durable workflows; overlaps current deterministic router |
| CrewAI | agent orchestration | MIT | self-host | medium | evaluate later | Role orchestration; duplicates two-bot role logic |
| AutoGen | agent orchestration | MIT | self-host | high | evaluate later | Multi-agent research; more complexity than current need |
| Pydantic AI | agent orchestration | MIT | self-host | medium | evaluate later | Typed agent outputs; useful after provider bridge |
| Letta | agent memory | Apache-2.0 | self-host | high | evaluate later | Long memory; current local memory is sufficient |
| Dify | agent platform | license requires verification | self-host/cloud | high | avoid now | Large platform overlap |
| Flowise | visual agents | Apache-2.0 | self-host | medium | evaluate later | Visual flows; overlaps scheduler/UI |
| Langflow | visual agents | MIT | self-host | medium | evaluate later | Visual prototyping; not required now |
| Firecrawl | web research | AGPL-3.0 | self-host/cloud | medium | evaluate later | Live web for Alpha; license and hosting review required |
| Crawl4AI | web research | Apache-2.0 | self-host | medium | priority evaluate | Local web extraction candidate |
| MarkItDown | document conversion | MIT | self-host | low | priority evaluate | Local document normalization |
| LlamaIndex | RAG/data | MIT | self-host | medium | evaluate later | May help retrieval; existing adapters first |
| Haystack | RAG/data | Apache-2.0 | self-host | high | evaluate later | Pipeline framework overlap |
| n8n | automation | fair-code/source-available; verify | self-host/cloud | medium | avoid now | External action risk and duplicate scheduler |
| Activepieces | automation | MIT/core plus commercial; verify | self-host/cloud | medium | evaluate later | Workflow connectors after approval model |
| Windmill | automation | AGPL-3.0 | self-host/cloud | high | evaluate later | Ops platform more than current need |
| Postiz | social | AGPL-3.0; verify | self-host | medium | avoid now | Publishing prohibited |
| Mixpost | social | license/edition varies; verify | self-host | medium | avoid now | Publishing prohibited |
| Mautic | marketing | GPL-3.0 | self-host | high | avoid now | Heavy campaign platform |
| Listmonk | newsletter | AGPL-3.0 | self-host | medium | evaluate later | Email sending remains gated |
| LiveKit Agents | voice agents | Apache-2.0 | self-host/cloud | medium | priority evaluate | Strong voice-agent prototype candidate |
| Pipecat | voice agents | BSD-2-Clause | self-host | medium | priority evaluate | Composable voice pipeline |
| Rasa | voice/chat | Apache-2.0 core; verify editions | self-host | high | evaluate later | Intent platform overlap |
| Botpress | voice/chat | license varies; verify | cloud/self-host history | high | avoid now | Current licensing/deployment uncertainty |
| Chroma | vector memory | Apache-2.0 | self-host | low | evaluate later | Local retrieval; unnecessary before corpus need |
| Qdrant | vector memory | Apache-2.0 | self-host/cloud | medium | evaluate later | Robust but operational overhead |
| LanceDB | vector memory | Apache-2.0 | embedded/cloud | low | priority evaluate | Simple local embedded retrieval |
| backtesting.py | trading | AGPL-3.0 | self-host | low | priority evaluate | Offline backtest candidate; license review |
| LEAN | trading | Apache-2.0 | self-host/cloud | high | evaluate later | Powerful but heavy |
| vectorbt | trading | Apache-2.0/community; verify | self-host | medium | evaluate later | Fast research; verify current packaging |
| freqtrade | trading | GPL-3.0 | self-host | high | avoid now | Crypto execution surface; research only |
| Netlify Forms | lead capture | managed feature | cloud | low | use now | Matches current deployment and static form |
| static Vite/public | landing | repo-native | self-host/Netlify | low | use now | Already supported; no dependency |

*License labels are a scouting snapshot, not legal advice; verify the current upstream LICENSE before adoption. No repository was installed or cloned.
