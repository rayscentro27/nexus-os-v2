# GoClear Client Experience Architecture

## Product stance

GoClear Client is a guided funding-readiness journey, not Nexus Admin Lite. It should feel trustworthy, calm, and useful before any data exists.

## Client questions

The portal answers: Where am I? What is missing? What should I do next? What did GoClear review? What should I upload? How does this affect readiness? When will GoClear review it?

## Journey model

```text
Welcome
  → Credit
  → Business Foundation
  → Bankability
  → Funding Readiness
  → Recommendations
  → Request Review
  → Funding Path / Next Step
```

The journey is revisitable, not a locked wizard. A progress rail shows current step, completed evidence, missing inputs, and review status.

## First login

For a new/no-data client:

```text
Welcome to GoClear
Let’s get you funding ready.
Step 1 of 5
Tell us where you are today.
[ Start My Readiness Review ]
```

No empty metric wall, synthetic score, or `$0` placeholder appears. The source state is intentionally `NOT_STARTED` or `UNKNOWN`.

## Page models and canonical truth

| Surface | Client-facing purpose | Source boundary |
| --- | --- | --- |
| Home | next action and journey progress | existing client workflow/readiness data |
| Credit | understand profile and actions | existing tenant-scoped credit workflow |
| Business Foundation | gather business evidence | existing Supabase workflow/storage |
| Bankability | show missing foundation factors | existing canonical readiness workflow |
| Funding Readiness | explain reviewed factors and gaps | existing readiness data; never implies approval |
| Recommendations | prioritized next steps | existing recommendation/readiness source |
| Documents | central library and processing state | existing Supabase Storage/document pipeline |

## Inline upload

Upload occurs beside the task:

- Credit → upload credit report
- Business Foundation → upload EIN letter or foundation document
- Funding Readiness → upload bank statements

The UI shows category, accepted formats, progress, received, processing, reviewed, replacement needed, date, and readiness use. Storage remains tenant-isolated. Documents also appear in the central library.

## Client AI boundary

Client AI is the existing approved client guide only. It may explain status, next step, missing document, readiness factor, recommendation, and approved education. It does not expose Hermes, Nova, Alpha, internal evidence, operational data, or unrestricted Nexus reasoning.

## Mobile-first behavior

At 375px and 390px, the next action stays above the fold, progress becomes a compact step rail, cards become stacked tasks, uploads use full-width controls, and documents use rows rather than desktop tables. Touch targets are at least 44px. Admin navigation and agent content never appear.

## Trust language

Use “readiness,” “review,” “recommended next step,” and “request review.” Do not say GoClear approved or guaranteed funding unless an actual source and authority exists.

## State language

`NOT_STARTED`, `IN_PROGRESS`, `RECEIVED`, `PROCESSING`, `REVIEWED`, `NEEDS_REPLACEMENT`, `UNKNOWN`, and `NOT_AVAILABLE` are product states. No-source is not zero.
