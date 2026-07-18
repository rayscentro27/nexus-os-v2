# Nexus 3.0 Intelligence Tool Evaluation

Generated: 2026-07-18

No external intelligence tooling was installed, cloned, vendored, configured, or activated in Wave 3.

| Candidate | Current Nexus Gap | Existing Nexus Overlap | License Status | Security Status | Data Risk | Dependency Weight | Proposed Disposition | Recommended Wave | Ray Approval Required |
|---|---|---|---|---|---|---|---|---|---|
| Instructor | More advanced model-output schema repair | Nexus-native `structuredOutput.ts` now covers bounded validation | UNKNOWN | UNKNOWN | INTERNAL/CLIENT if misused | Medium | DEFER | Later evaluation | Yes |
| Outlines | Grammar-constrained generation | Nexus-native validation exists; no provider activation needed | UNKNOWN | UNKNOWN | INTERNAL/CLIENT if attached to live data | Medium | DEFER | Later evaluation | Yes |
| Ragas | Retrieval quality evaluation | Native retrieval fixtures now cover grounding/exclusion boundaries | UNKNOWN | UNKNOWN | Possible prompt/data leakage | Medium | STUDY_ARCHITECTURE_OR_WORKFLOW_ONLY | Later Knowledge QA | Yes |
| Langfuse | LLM observability and traces | Hermes currently uses deterministic/router evidence for Wave 3 | UNKNOWN | UNKNOWN | Prompt, trace, and PII risk | Medium | DEFER | Later observability sprint | Yes |
| MarkItDown | Document conversion | Existing bounded document pipeline and synthetic fixtures remain primary | UNKNOWN | UNKNOWN | Document PII if misconfigured | Medium | STUDY_ARCHITECTURE_OR_WORKFLOW_ONLY | Later document sprint | Yes |
| Marker | Document extraction/OCR | Existing parser/grouping/strategy path remains primary | UNKNOWN | UNKNOWN | Document PII if misconfigured | Heavy | DEFER | Later document sprint | Yes |
| GitHub MCP Reader | Repository intelligence access | Repo Intelligence registry and Capability OS profiles exist | MIT reported in prior registry; verify before use | PARTIAL | Source-code and token scope risk | Medium | DEFER until host config approved | Repo Intelligence lane | Yes |

Wave 3 result: Nexus-native structured-output and retrieval-evaluation foundations are sufficient for the current governed intelligence layer. External tooling should stay research-only until a bounded evaluation is approved.
