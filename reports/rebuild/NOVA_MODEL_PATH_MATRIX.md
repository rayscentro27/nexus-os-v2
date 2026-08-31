# Nova Model Path Matrix

| Class | Pre-model path | Model | Resources exposed | Post-model/fallback |
|---|---|---|---|---|
| General conversation | `model_first`; no company context | `openai/gpt-4o-mini` | Catalog and general reasoning | validation, compose, local advisory fallback on provider failure |
| General business advice | `model_first`; company context may be injected by terms | Same | Catalog, company context, web/Alpha/Nexus descriptors | validation and compose |
| Recommendation/comparison | `model_first`; `ADVISORY`/`ANALYTICAL` classification | Same | Catalog and reasoning abilities | validation and compose; no deterministic recommendation engine |
| Current public information | `model_first`; plan identifies public research | Same | Public web/search/retrieval in catalog and protocol | model may emit one capability envelope; continuation if executed |
| Public web research | Same | Same | `PUBLIC_WEB_SEARCH`, `PUBLIC_WEB_RETRIEVAL`, `ALPHA_RESEARCH` | bounded broker execution, then model continuation |
| Nexus read | factual company gate may run first; otherwise model-first | Same | Nexus catalog/read envelope | shared capability boundary and validation |
| Alpha delegation | explicit handoff may use existing bounded gate; model envelope also supported | Same | Alpha resource and governed intake | Alpha result or truthful incomplete state |
| Google capability | no proven automatic status call | Same | Google resource descriptor; live status only when capability is invoked | validation/compose |
| Action request | existing deterministic governed boundary before model | Same | Action metadata, not direct authority | Nexus/authority boundary or truthful denial |

`SAME_BRAIN_PATH_FOR_ALL=PARTIAL`: same model/provider/SOUL, but utility handling, factual capability gating, explicit governed actions, and model-selected capability continuation are different branches.
