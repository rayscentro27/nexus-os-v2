# Nova Hermes automatic retrieval proof

Baseline: `a9bea8f`  |  Campaign: `HG-WP6.5-NOVA-HERMES-SHADOW-AUTONOMOUS-RETRIEVAL-REFERENT-AND-MULTIRESOURCE-CERTIFICATION-20260831-01`

The shadow tool contract now labels search as discovery evidence and page
retrieval as verification/detail evidence. It gives the model a retrieval hint
only when the real search response contains candidate URLs; no user-phrase
router was added.

## Development observations

| Request | Search | Pages | Result |
|---|---:|---:|---|
| Current credit-repair affiliate programs | yes | 2 | model continued with native retrieval |
| Tesla current strategy | yes | 2 | current-source research path executed |
| Capital of France | no | 0 | direct model answer |
| Nexus + current outside information | yes | 2 | multi-resource continuation |

The Hermes iteration budget remains bounded at eight. If providers return weak
or empty pages, the structured result tells Nova the evidence is insufficient;
it does not claim verification.
