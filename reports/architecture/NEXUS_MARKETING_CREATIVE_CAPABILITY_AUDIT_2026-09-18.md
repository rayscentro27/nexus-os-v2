# Nexus Marketing + Creative Capability Audit

## Status

`MARKETING_CREATIVE_AUDIT_STATUS=PASS_REAL_AUDIT`

This is an evidence-based audit and operating design. No Marketing or Creative
runtime was rebuilt, no campaign was published, and no production schema was
changed.

## Executive conclusion

Nexus already has a usable internal Marketing/Creative foundation:

- Marketing has a real offer registry, funding-readiness funnel, landing-page
  route, checkout/attribution path, draft copy generators, approval controls,
  and event/measurement contracts.
- Creative has real internal campaign packages, generated image artifacts,
  deterministic text overlays, FFmpeg assembly, video receipts, asset review,
  approval/revision UI, and private Supabase-backed storage adapters.
- Neither department is a fully autonomous publishing or acquisition engine.
  Publication, email sending, ad spend, external account activation, and
  provider-backed media generation remain gated or unproven.
- The missing connective tissue is a canonical transformation brief shared by
  Marketing and Creative, not another department implementation.

The shortest next build is transformation contracts → internal brief generation
→ Creative package generation → approval/QA → one bounded distribution test →
measurement feedback.

## Evidence-level inventory

### Marketing

| Capability | Evidence | Classification |
|---|---|---|
| Offer registry | `configs/offer_registry.json` | PASS_REAL internal registry |
| $97 readiness offer | `R20B_CERTIFICATION.md`, live route and checkout path | PASS_REAL bounded funnel |
| Funnel stages | `configs/revenue_funnel_registry.json` | PASS_REAL design/runtime contract |
| Funding-readiness landing page | `src/pages/goclear/GoClearFundingReadinessCampaign.tsx`, R20B browser proof | PASS_REAL |
| Campaign/variant attribution | `campaign_id`, `variant`, `referralSource` path | PASS_REAL bounded |
| Draft marketing assets | `src/hermes/nexus/marketingAssetStudio.ts`, `src/hermes/alpha/marketingAssetStudio.ts` | PARTIAL_REAL / draft-only |
| Content opportunity planning | `contentOpportunityTypes.ts`, research planners | PARTIAL_REAL |
| Affiliate/referral paths | registries and approval-gated trackers | PARTIAL_REAL / blocked external |
| Analytics events | `src/lib/clientAnalytics.ts`, `outcomeAnalytics.ts`, content tests | PARTIAL_REAL; live business outcomes unknown |
| Publishing | approval and publish-readiness packages | DRAFT_ONLY / approval-gated |
| Email sending | policy explicitly disables send | NOT_AVAILABLE for this audit |
| A/B testing | Variant A/B attribution exists; no live conversion evidence | PARTIAL_REAL |
| Revenue | test checkout and ledger infrastructure | PARTIAL_REAL; actual revenue not proven |

Marketing therefore owns strategy and draft preparation today, not autonomous
distribution.

### Creative

| Capability | Evidence | Classification |
|---|---|---|
| Creative briefs | `creative_briefs`, `creative_design_briefs`, `create_design_brief.py` | PASS_REAL internal/draft |
| Campaign packages | R20A/R20B packages and handoff artifacts | PASS_REAL bounded |
| Text hooks/scripts/storyboards | scripts and package artifacts | PASS_REAL internal |
| Image generation | R20A certification records three image generations and inspected outputs | PASS_REAL bounded |
| Deterministic overlays/branding | Playwright/HTML/CSS and branded assets | PASS_REAL |
| Video assembly | FFmpeg-built MP4s with receipts | PASS_REAL |
| AI video generation | provider portfolio only; no currently authorized live provider | AUTHORIZATION_REQUIRED / NOT_PROVEN |
| Voice/audio | local voice artifacts exist; commercial TTS path not authorized | PARTIAL_REAL / not production-certified |
| Captions | text/caption artifacts and FFmpeg pipeline exist | PASS_REAL bounded |
| QA scoring | `QA_SCORES.json`, score scripts, review UI | PASS_REAL bounded |
| Revision | request-change workflow and revision jobs exist | PARTIAL_REAL; generation route not always wired |
| Approval | Supabase approval IDs, review UI, Ray Review | PASS_REAL bounded |
| Publication | explicit human gate | NOT_AVAILABLE without approval |

The historical/proven R20 artifacts are real internal production evidence, but
their existence does not mean a continuously available media provider exists.

## Shared infrastructure audit

| System | Current role | Proven | Decision |
|---|---|---:|---|
| RevenueHub | offer/revenue metrics and truth classes | Partial, actual revenue unknown | REUSE |
| Funnel registry | stage and external-action boundary | Yes as contract | REUSE |
| `creative_campaigns` | campaign identity, audience, offer, status | Schema present | REUSE |
| `creative_briefs` | campaign-level creative brief | Schema present | REUSE |
| `creative_assets` | asset content, campaign/brief/approval links | Schema plus adapters | REUSE |
| `creative_design_*` | visual design briefs, variants, scores, QA | Schema present; some workers gated | REUSE selectively |
| `studio_outputs` | scripts/output artifacts linked to research/campaign | Schema present | REUSE |
| ApprovalCenter/Ray Review | review, request changes, reject/approve | Proven bounded | REUSE |
| Analytics/events | funnel and client events | Instrumented, business truth unknown | REUSE; certify measurement later |
| Supabase | DB, private storage, RLS-backed records | Storage adapters/proofs present | REUSE |
| Netlify | frontend deployment | Existing platform | REUSE, not changed here |
| ToolRegistry | capability declarations | Present in Nexus | REUSE |
| ContentStudio/UI workspaces | presentation/editor surfaces | Present, some sample data | REUSE only where canonical source exists |
| RevenueHub/Creative duplicate logic | overlapping older helpers and R20 packages | Multiple generations | RETAIN history; consolidate future reads |

No system should be deleted based on this audit.

## Transformation-first operating model

Marketing should represent the customer journey as:

`CURRENT_REALITY → PAIN/LIMITATION → SOLUTION → TRANSFORMATION → NEW REALITY → CTA`

The offer is a mechanism, not the headline. For funding, Nexus should sell the
clarity and business progress the preparation can enable, without implying that
funding or approval is guaranteed.

### Restaurant funding design proof

#### RESTAURANT_MARKETING_BRIEF

```json
{
  "brief_type": "MarketingBrief",
  "audience": "Restaurant owners with equipment, payroll, inventory, or growth needs who are uncertain what funding preparation requires",
  "current_state": "The owner is operating under pressure, may be delaying repairs or growth, and does not know whether the business profile and documents are ready for a funding conversation.",
  "pain": "Unclear readiness, documentation gaps, fear of a denial, and the cost of applying before the business is prepared.",
  "desired_outcome": "Know what to prepare, what gaps matter, and which next step is reasonable before approaching a lender or partner.",
  "transformation_statement": "Turn funding uncertainty into a practical readiness path so the owner can make the next business decision with more clarity.",
  "offer": "GoClear Credit & Funding Readiness Review",
  "proof": ["documented readiness snapshot", "document-gap review", "prioritized next-action plan"],
  "channel": "approved landing page plus organic educational content; paid distribution not activated",
  "funnel": "research evidence → readiness education → review entry → authenticated account → checkout/onboarding",
  "cta": "Start your $97 readiness review",
  "success_metric": "qualified review entry and verified purchase followed by onboarding; conversion and revenue remain unknown until measured",
  "research_evidence_refs": ["need_f527d1db8c4d1e5de721", "R20B bounded campaign evidence"],
  "alpha_decision_ref": "existing model-backed Alpha qualification receipt"
}
```

#### RESTAURANT_CREATIVE_BRIEF

```json
{
  "brief_type": "CreativeBrief",
  "audience": "Restaurant owners trying to keep operations stable while preparing for a possible funding conversation",
  "before_state": "Busy kitchen, aging equipment, tight payroll/inventory decisions, and uncertainty about what a lender or partner will need.",
  "after_state": "A calmer owner with a visible preparation checklist, clearer documents, and a prioritized next step—not a promised approval.",
  "visual_transformation": "Move from operational fog and deferred repairs to an organized readiness board, prepared documents, and a functioning business environment.",
  "emotional_transformation": "From anxiety and confusion to clarity, control, and measured confidence.",
  "hook": "Before your next funding conversation, know what to prepare.",
  "script": "Show the pressure point, show the preparation path, show the practical deliverables, then state the readiness-only boundary and CTA.",
  "scenes": ["restaurant pressure point", "documents/readiness snapshot", "prioritized next-action plan", "owner sees the next step"],
  "proof": ["real deliverable descriptions", "documented process", "no testimonial or outcome invention"],
  "cta": "Start your $97 readiness review",
  "platform": "feed, square, story/reel, and short-form vertical",
  "asset_types": ["static", "short-form video", "caption package"],
  "quality_requirements": ["legible CTA", "brand fit", "no guarantees", "human review required"],
  "marketing_brief_ref": "restaurant-marketing-brief-internal-v1"
}
```

## Canonical department contracts

### MarketingInput → MarketingBrief → CampaignPlan

Required fields:

`audience`, `current_state`, `pain`, `desired_outcome`,
`transformation_statement`, `offer`, `proof`, `channel`, `funnel`, `cta`,
`success_metric`, `research_evidence_refs`, `alpha_decision_ref`.

Marketing may draft these objects from qualified evidence, but it cannot turn a
weak or rejected Alpha finding into a campaign.

### CreativeInput → CreativeBrief → CreativePackage

Required fields:

`audience`, `before_state`, `after_state`, `visual_transformation`,
`emotional_transformation`, `hook`, `script`, `scenes`, `proof`, `cta`,
`platform`, `asset_types`, `quality_requirements`, `marketing_brief_ref`.

Creative owns the expression of the transformation. It does not independently
change the offer, invent proof, or publish.

## Shared operating loop

`Research → Alpha → Marketing → Creative → Marketing → Analytics → Research/Alpha`

- Research supplies customer language, pain, desired outcomes, evidence,
  freshness, and commercial-intent signals.
- Alpha returns `QUALIFY`, `RESEARCH_MORE`, `REJECT`, or `PARK`, with confidence,
  deficiencies, and next stage.
- Marketing converts qualified evidence into audience, transformation, offer,
  channel, funnel, CTA, and measurable success criteria.
- Creative converts the approved Marketing brief into hooks, stories, scenes,
  assets, platform variants, and QA evidence.
- Marketing distributes only after the applicable approval gate and records
  campaign/variant attribution.
- Analytics returns clicks, leads, conversion, cost, engagement, refunds, and
  outcome observations without claiming causality where it is not proven.
- Research and Alpha learn from measured response and evidence gaps.

## Proof and compliance boundary

Required before public use:

- every factual or financial claim has a source or is labeled a hypothesis;
- before/after language describes intended or observed state, not guaranteed
  causation;
- testimonials and results are real, authorized, and attributable;
- no guaranteed funding, approval, revenue, score increase, or timeline;
- no fabricated lender criteria, customer proof, or performance metrics;
- affiliate/referral disclosures and free/DIY alternatives remain visible;
- funding content states GoClear is not the lender and outcomes remain outside
  Nexus control;
- human approval precedes publication, outreach, paid spend, or external
  account action.

Current policy evidence: `configs/content_marketing_policy.json`, offer
registry disclaimers, R20A/R20B compliance notes, and `outcomeAnalytics.ts`.

## Creative/media capability today

- Text: `PASS_REAL` for internal hooks, scripts, briefs, and draft packages.
- Images: `PASS_REAL` bounded; R20A records inspected generated backgrounds and
  deterministic overlays.
- Video: `PASS_REAL` for assembled MP4 and bounded internal artifacts; AI-video
  provider execution is `AUTHORIZATION_REQUIRED`.
- Audio: `PARTIAL_REAL`; local audio artifacts exist, commercial TTS is not
  currently authorized/certified.
- Assembly: `PASS_REAL` through FFmpeg for known pipelines.
- Captions: `PASS_REAL` bounded through text/overlay packages.
- Branding: `PASS_REAL` for known GoClear package and deterministic overlays.
- QA: `PASS_REAL` bounded through rubric, scores, visual inspection, and review.
- Revision: `PARTIAL_REAL`; durable request-change flow exists, but not every
  provider/generation path is wired for automatic regeneration.

## Persistent assets and versioning

Canonical intended storage is Supabase: `creative_assets`, campaign/brief
foreign keys, `approval_id`, `creative_scores`, and private `creative-assets`
storage adapters where authenticated. Public `public/creative-r*` artifacts are
repository/static evidence and handoff outputs, not the long-term source of
truth for every asset.

- `PERSISTENT_ASSET_STORAGE=Supabase Storage adapter, private when configured`
- `CREATIVE_ASSET_REGISTRY=creative_assets plus design/score tables`
- `ASSET_VERSIONING=Partial; version/prompt/receipt metadata exists in packages, but a universal version contract is not present`
- `APPROVAL_STATE=Approvals/Ray Review plus asset approval_id and review state`
- `CAMPAIGN_ASSET_LINKAGE=Present via campaign_id, brief_id, workspace_id`

## Tool and provider fit

| Capability | Current status | Marketing/Creative use | Future integration |
|---|---|---|---|
| Last30Days | PASS_REAL acquisition | customer language and recent demand | feed qualified evidence only |
| SEO adapter | PASS_REAL | search opportunity and technical evidence | Marketing input |
| FFmpeg | PASS_REAL | deterministic assembly/captions | keep local bounded |
| Image generation | PASS_REAL bounded | visual concepts/assets | governed provider adapter |
| AI video providers | authorization required | short-form/B-roll | one canary after approval |
| Supabase Storage | partial/live adapter evidence | private asset persistence | certify production bucket |
| Netlify | existing deployment | landing pages/frontend | reuse |
| Figma/Canva/Penpot | not proven as active production path | design/reference/approval | optional, not required now |
| Browser automation | available in selected environments, not a dependable creative backend | QA/manual provider canary | never sole production dependency |
| Kaggle/Modal | future temporary compute | GPU media/model canaries | build only after contract/need |
| Hermes/OpenCode/Codex | available execution/reasoning paths | brief drafting, bounded revisions | use existing canonical runtime |

## Kaggle future fit

Kaggle should be a temporary worker lane, not a new control plane. Candidate
workers are `VIDEO_GENERATION`, `IMAGE_GENERATION`, `TRANSCRIPTION`,
`FFMPEG_RENDER`, `LOCAL_LLM`, `MODEL_BENCHMARK`, `CODING`, and
`MEDIA_PROCESSING`. Each worker should receive a governed work item, write a
receipt and bounded artifact, then return the artifact to Supabase Storage or
the canonical asset registry. Jobs should be disposable because Kaggle state,
quotas, notebooks, and runtimes are not the company system of record.

## Founder Mode

`FOUNDER_MODE_MARKETING=Reuse current research, SEO, offer, landing-page,
approval, and analytics infrastructure; stay organic/draft-first.`

`FOUNDER_MODE_CREATIVE=Reuse deterministic overlays, local FFmpeg, existing
approved artifacts, and bounded image generation; use paid video/TTS only after
a one-canary spend decision.`

`PAID_DEPENDENCIES_REQUIRED_NOW=NO` for the next design/build step. Paid data,
media, ad, and affiliate providers are optional future capabilities, not
current prerequisites.

## Gap analysis

### Marketing gaps

- No single transformation-first brief contract shared by Research, Alpha,
  Marketing, and Creative.
- Live distribution and conversion evidence are not yet proven at business
  scale.
- Campaign analytics are instrumented but actual CAC, conversion, retention,
  and revenue remain unknown.
- Offer/campaign records exist across generations and need one canonical read
  projection in a future implementation.
- Automated publishing/email/ad integrations remain gated or unavailable.

### Creative gaps

- Provider-backed AI video, commercial voice, and continuous generation are not
  authorized/certified.
- Creative workspace contains sample concepts and should not be treated as
  canonical generated output without asset receipts.
- Universal asset versioning and regeneration lineage need a bounded contract.
- Supabase private-storage production health should be freshly certified for
  creative assets.

### Shared gaps

- Marketing-to-Creative handoff needs durable brief IDs and transformation
  fields.
- Creative-to-Marketing return needs asset package/QA/approval receipts tied to
  campaign and variant IDs.
- Analytics feedback needs to link campaign, creative variant, offer, funnel
  stage, and Research/Alpha finding IDs without claiming causality.
- Proof and compliance need to be evaluated before assets enter a publish-ready
  state.

## Recommended build sequence

1. Add a bounded transformation contract/projection using existing campaign and
   brief tables or metadata; do not create a new department database.
2. Build a deterministic MarketingBrief generator from qualified Research/Alpha
   evidence, with explicit proof and claim fields.
3. Build a CreativeBrief generator consuming the MarketingBrief and producing
   platform-specific draft packages.
4. Link packages to `campaign_id`, `brief_id`, `asset_id`, `approval_id`, and
   quality/coverage metadata.
5. Certify one internal asset-review loop with request changes and revision
   lineage; no publication.
6. Run one organic, human-approved campaign test with UTM/variant/event
   measurement.
7. Feed measured results back to Research/Alpha using outcome observations,
   not causal claims.
8. Only then evaluate one authorized AI-video/TTS or temporary GPU canary.

## Final classification

`MARKETING=PARTIAL_REAL`

`CREATIVE=PASS_REAL_BOUNDED`

`SHARED_OPERATING_MODEL=DESIGN_READY; IMPLEMENTATION GAP REMAINS`

The departments are not missing from Nexus. The next value comes from joining
their existing evidence, offer, asset, approval, and analytics paths around the
customer transformation rather than adding more feature or product language.
