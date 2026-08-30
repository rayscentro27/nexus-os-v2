# Nexus Open-Source Reasoning Research

This is a read-only comparison of current project documentation and existing Nexus evidence. No candidate was installed or cloned.

| Project | License / posture | Nexus use | Overlap / resource risk | Recommendation |
|---|---|---|---|---|
| LangGraph | MIT; persistence/checkpointing and durable execution documented | stateful reasoning graph behind Nexus evidence broker | overlaps existing wrapper; lightweight | USE_EXISTING_INSTALL / WRAP |
| GPT Researcher | MIT repository; multi-source research/report pattern | Research Alpha search/planning reference or bounded pilot | provider/retriever configuration; not a general Telegram brain | PILOT |
| Crawl4AI | open-source active project; existing bounded adapter evidence | primary-page extraction after SearXNG | Chromium and maintenance boundary | WRAP |
| Firecrawl | AGPL-3.0 core; self-host or cloud variants | possible extraction alternative | license/hosting/security and resource complexity | DEFER |
| Langfuse | MIT core/self-hostable; self-host has multiple stateful services | tracing/evaluation | Oracle disk/service overhead and trace privacy | DEFER |
| DSPy | MIT | offline prompt/program optimization and evals | not an orchestration or retrieval runtime | REFERENCE_PATTERN |
| Stagehand | open-source SDK with local and Browserbase modes | browser extraction/action patterns | cloud option and browser authority risk | DEFER |
| Browser Use | MIT; browser-agent automation | future bounded browser research | high action surface; overlaps Playwright/Crawl4AI | DEFER |
| PydanticAI | MIT; typed/model-agnostic agent patterns | typed structured synthesis reference | overlaps Hermes/LangGraph; another runtime | DEFER |
| Microsoft Agent Framework | MIT; Python/.NET agents/workflows | reference patterns only | broad overlap with Hermes/LangGraph; evolving ecosystem | DEFER |
| LlamaIndex | mature RAG/indexing ecosystem | only if a durable corpus/RAG gap appears | adds another retrieval abstraction without current need | DEFER |

Primary references: [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence), [Crawl4AI documentation](https://docs.crawl4ai.com/), [GPT Researcher](https://github.com/assafelovic/gpt-researcher), [Firecrawl](https://github.com/firecrawl/firecrawl), [Langfuse self-hosting](https://langfuse.com/self-hosting), [DSPy](https://github.com/stanfordnlp/dspy), [PydanticAI](https://github.com/pydantic/pydantic-ai), [Browser Use](https://github.com/browser-use/browser-use), [Stagehand](https://github.com/browserbase/stagehand), [Microsoft Agent Framework](https://github.com/microsoft/agent-framework).

## Canonical recommendation

Use one hybrid stack:

`Telegram → authenticated Nexus ingress → deterministic TruthKernel evidence/policy broker → Hermes 0.20.6 conversational session on Oracle → existing LangGraph wrapper for explicit multi-step state where needed → allowlisted Nexus capabilities → deterministic validation and FACT/ESTIMATE/UNKNOWN payload → Hermes plain-language synthesis → Telegram.`

Research Alpha should use `Nexus planner + SearXNG + wrapped Crawl4AI public-page retrieval + claim/source validation + Hermes synthesis`, with GPT Researcher as a bounded pilot only if the existing adapter cannot close the primary-source gap. Keep Playwright/Crawl4AI as the browser stack; defer Browser Use and Stagehand. Use existing local traces and receipts before adding Langfuse infrastructure.

The stack requires no mandatory new subscription: baseline is Tier 0 local/free plus existing Oracle resources. Optional external models or hosted browsers remain outside this audit and would require their own cost/privacy review and authority.

