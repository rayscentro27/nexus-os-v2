# Hermes Alpha Reference Project Evaluation

The license column is a planning signal, not legal advice. Verify the exact version and dependencies before reuse.

| Project | Runtime/license | Best fit and strengths | Risks / what to avoid | Recommendation |
|---|---|---|---|---|
| [Postiz](https://github.com/gitroomhq/postiz-app) | TS/Next/Nest/Postgres/Temporal; AGPL-3.0 | Future external social scheduler: calendar, collaboration, analytics, platform OAuth/API | Heavy deployment, tokens/platform review, email/DB dependencies, AGPL network obligations; never copy code casually | Integrate later as isolated adapter after legal/security review; copy workflow concepts only now |
| [Mixpost](https://github.com/inovector/mixpost) | PHP/Laravel; mixed/commercial editions—verify exact license | Strong product model for calendar, connected accounts, media, analytics, approval and inbox | Separate stack, social API/token security, edition/license ambiguity | Copy UX concepts; evaluate install later |
| [LangChain Social Media Agent](https://github.com/langchain-ai/social-media-agent) | TS/LangGraph; repo terms require verification | URL intake → research/post generation → HITL edit/approve → schedule is directly relevant | Quickstart needs paid/external services; full setup includes Supabase/service key, Slack, cron and publishing—prohibited for Alpha v1 | Copy graph/HITL pattern only; reject direct install |
| [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) | Python/PyTorch/Gradio; AGPL-3.0 | Future local creative adapter with rich image workflows | GPU/model license, extension supply chain, arbitrary-code option, large maintenance/security surface | Separate future adapter; never Alpha Brain dependency |
| [OBS Studio](https://github.com/obsproject/obs-studio) | C/C++; GPL-2.0-or-later | Recording/streaming production reference | Desktop/native complexity and broadcast-account risk | Production workflow reference only |
| [Shotcut](https://www.shotcut.org/) | C++/Qt/MLT; GPL-3.0-or-later | Manual video editing/render templates | Native codecs/dependencies; no reason to embed | Production workflow reference only |
| [Blender](https://github.com/blender/blender) | C/C++/Python; GPL-2.0-or-later | 3D/motion/creative production; outputs remain creator-owned | Large install/render burden, plugin/script risk | Optional creative workstation later |
| [Audacity](https://github.com/audacity/audacity) | C/C++; GPL | Manual audio cleanup and narration workflow | Native dependency/plugin risk; not an agent component | Production workflow reference only |
| [p5.js](https://github.com/processing/p5.js) | JavaScript; LGPL-2.1 | Lightweight generative sketches and explainers | Browser performance/accessibility; licensing review for bundled derivatives | Integrate later for code-native creative templates |
| [PixiJS](https://github.com/pixijs/pixijs) | TypeScript/WebGL; MIT | High-performance 2D interactive assets | More engineering than static campaigns need | Use later for interactive campaign assets, not v1 |
| [MarkItDown](https://github.com/microsoft/markitdown) | Python; MIT | Converts common files to Markdown for Research Intake | Parser/untrusted-file risks, optional dependency surface, conversion is not truth validation | Integrate later in a sandboxed file adapter |
| [n8n](https://github.com/n8n-io/n8n) | TS; Sustainable Use/fair-code | Optional visual glue for approved handoffs and external adapters | Not Alpha Brain; license limits, credential sprawl, workflow injection and accidental side effects | Integrate later only behind Ray Review and disabled workflows |
| [Firecrawl MCP Server](https://github.com/firecrawl/firecrawl-mcp-server) | Node/TS; license/version verify | Structured public web search/scrape for Research Intake | Paid API, prompt injection, robots/terms/privacy, broad browser surface | Future research adapter with allowlists; not Phase 1 |
| Content/SEO automation repos | Mixed/unknown | Ideas for briefs, keyword clusters, repurposing, and experiment queues | Quality, plagiarism, spam, hidden keys, abandoned dependencies | Evaluate individually; copy schemas, reject blind installs |
| “MakeMoneyWithAI” curated monetization lists | Mixed/unknown | Discovery prompts and category maps | Hype, affiliate bias, stale claims, unclear licenses, unsafe schemes | Research leads only; never evidence or executable code |

## Placement summary

- Nexus Marketing: approved GoClear/customer campaigns and delivery handoffs.
- Alpha Marketing: research, ideation, scoring, and draft assets.
- Research Intake: MarkItDown and Firecrawl later; current local files first.
- Opportunity Desk: curated monetization/SEO ideas after source verification.
- Trading Lab: none of these belong there.

Postiz/Mixpost are future external systems, not copied subsystems. n8n is optional glue, never the brain. Creative tools are adapters/workstations, not reasoning dependencies. Every social/email/publish action remains disabled and Ray Review-gated.
