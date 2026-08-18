# Creative Pilot

## Safe pilot scope

The pilot used public or governed internal evidence only.

It did not:

- build the site
- generate production assets
- publish
- deploy
- spend money

## Opportunity

- id: unclecode_crawl4ai
- title: Crawl4AI
- target: Hermes / Alpha operators

## Recommended territory

- concept: Scout Brief
- positioning: Editorial intelligence brief that summarizes what was found and why it matters.
- audience: operators who want a quick read before diving into details.
- hook: What we found, what it means, what to do next.
- CTA: Read the Scout Brief

## Build spec skeleton

```json
{
  "build_constraints": [
    "no public publish",
    "no paid spend",
    "no client PII",
    "read-only evidence only"
  ],
  "concept_name": "Scout Brief",
  "content_blocks": [
    "evidence summary",
    "provenance rail",
    "next-action module",
    "approval boundary"
  ],
  "layout_direction": "hero summary plus a narrow evidence rail",
  "modules": {
    "primary_module": "Scout Brief",
    "supporting_modules": [
      "evidence rail",
      "status strip",
      "action row"
    ]
  },
  "objective": "Editorial intelligence brief that summarizes what was found and why it matters.",
  "target_audience": "operators who want a quick read before diving into details.",
  "verification": {
    "must_retain_differentiator": true,
    "must_retain_evidence_refs": true,
    "must_retain_target_audience": true
  }
}
```
