# Nexus Department Real-Live Flow Certification

Date: 2026-09-27

## Certification matrix

| Department | Data received | AI/reasoning | Execution | Output | Review | Measurement | Lesson | Next action | Status |
|---|---|---|---|---|---|---|---|---|---|
| Trading | Yes | Existing Alpha + Trading intake | Paper backtest | Metrics and receipt | Yes | Baseline + 2 variants | Yes | Out-of-sample paper review | PASS_REAL_BOUNDED |
| Systems | Yes | Not exercised | None | None | None | None | None | Acquire identity/compatibility evidence | PARTIAL |
| Clyde/Funding | Yes | Clyde matching logic | Baseline/variant comparison | Pass/gap/unknown | Yes | Variant comparison | Yes | Lender-specific terms | PASS_REAL_BOUNDED |
| Revenue | Yes | Alpha/revenue reasoning | Internal package | Package and drafts | Internal review | Completeness/unknowns | Yes | Competitor/current-term review | PASS_REAL_BOUNDED |
| Marketing | Yes | Internal planning | Draft plan | Audience/offer/channel plan | Internal | Metrics defined, not observed | Pending | Consume revenue package | PARTIAL |
| Creative | Yes | Existing creative route/history | Six concepts + tracks | Concept set and critic receipt | Yes | Diversity/critic metrics | Yes | Revise selected concept after review | PASS_REAL_BOUNDED |
| Operations | Yes | Monitoring path | Observation only | Status/next-action awareness | Partial | No external metrics | Pending | Monitor active packages and stalls | PARTIAL |

## Certification boundary

PASS_REAL_BOUNDED means a real input completed a safe internal path with a persisted output, review, lesson, and next action. It does not mean production readiness, profitability, public launch, or external approval. Systems remains unexercised because current candidate evidence is not yet sufficient for a meaningful isolated test.

The existing two-hour reporter now exposes operating mode, input diversity, certification starts/completions/failures, lessons applied, next tests, and department activity. It remains a read-only observer and no second scheduler was created.
