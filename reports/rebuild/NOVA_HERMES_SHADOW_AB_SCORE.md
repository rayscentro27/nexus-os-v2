# Nova custom versus Hermes shadow score

The historical fixed rubric baseline remains `CUSTOM_RUNTIME_SCORE=58/85`.
The prior shadow score was `67/85`; this campaign's evidence improves automatic
retrieval and referent continuity, but the repository does not contain the
rubric weights or a reproducible scorer, so a new numeric score is not
fabricated here.

| Category | Current evidence |
|---|---|
| Native tool calling | pass |
| Real search | pass |
| Automatic retrieval | pass for evidence-bearing probes |
| Currentness | partial: source dates often unavailable |
| General referents | pass in the bounded five-turn probe |
| Multi-resource synthesis | pass for Nexus + web + retrieval; three-resource Alpha follow-up partial |
| Fallback continuation | pass |
| Cutover | no |

`HERMES_SHADOW_SCORE=NOT_RECOMPUTED`; `SCORE_DELTA=NOT_CERTIFIED`.
