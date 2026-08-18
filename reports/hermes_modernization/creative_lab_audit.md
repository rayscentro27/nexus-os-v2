# Creative Lab Audit

## Existing surfaces

| Component | Classification | Reason |
|---|---|---|
| plugins/nexus-hermes-plugin/skills/nexus-creative-director/SKILL.md | KEEP | Creative direction is already a skill with research-first rules, not a persistent agent. |
| src/hermes/alpha/marketingAssetStudio.ts | WRAP | Provides bounded draft generation for marketing assets without autonomous publishing. |
| src/hermes/alpha/alphaBrain.ts | EXTEND | Already routes marketing_asset requests through Alpha with deterministic safety controls. |
| src/hermes/alpha/alphaEvaluationHarness.ts | MERGE | Existing fixture harness can host creative territory regression checks. |
| src/lib/hermesCapabilityRegistry.ts | EXTEND | Creative Studio capability is already inventoried as partial and needs a read-only inventory adapter. |
| src/data/marketingDraftsData.js | MERGE | Contains bounded marketing examples, hooks, and CTA patterns that can be reused as reference material. |
| src/lib/hermesIntent.ts | WRAP | Intent routing already recognizes landing-page and campaign surfaces that the Creative Lab should reuse. |
| src/lib/hermesWorkRouter.ts | WRAP | Work routing already maps marketing and creative_studio work to bounded processes. |
| src/lib/approvalReview.ts | EXTEND | Approval review already governs creative readiness and should remain the approval boundary. |
| src/lib/nexusProjects.ts | EXTEND | Creative project inventory already surfaces the creative tab and project metadata. |
| scripts/creative/create_design_brief.py | WRAP | Already assembles design briefs that should feed the Creative Director instead of being duplicated. |
| scripts/creative/generate_design_variants.py | MERGE | Existing design variant generation can be reused as a regression surface for territory comparison. |
| scripts/creative/score_design_variants.py | MERGE | Existing scoring logic should be wrapped into Creative Lab verification rather than duplicated. |
| scripts/creative/compare_design_variants.py | MERGE | Already compares candidate directions and can host territory distinctiveness checks. |
| scripts/creative/create_creative_approvals.py | WRAP | Approval gating already exists and should remain the authority for publish-ready creative decisions. |
| scripts/creative/generate_campaign_assets.py | WRAP | Campaign asset generation is already present as draft-only output and can be governed by the lab. |
| scripts/creative/generate_overnight_creative_asset_queue.py | WRAP | The overnight queue is an existing bounded creative runner, not a new identity. |
| scripts/creative/generate_best_money_opportunity_creative_package.py | WRAP | Opportunity-specific creative packaging should be wrapped by the Creative Director, not reimplemented. |
| scripts/creative/create_social_post_drafts.py | WRAP | Social draft generation already exists and must remain draft-only and approval-gated. |
| scripts/creative/create_publish_readiness_package.py | EXTEND | Publish-readiness packaging is already aligned with approval workflows and can absorb Creative Lab output. |
| scripts/creative/review_publish_package.py | EXTEND | Publish review is the correct place to verify creative output before any release action. |
| scripts/creative/_design.py | MERGE | Low-level design helpers should remain the deterministic implementation surface. |
| scripts/creative/_publish.py | WRAP | Publishing stays outside the lab; existing publish helpers are only a governed wrapper target. |
| scripts/marketing/build_landing_page_experiments.py | WRAP | Landing-page experiment generation already exists and should be routed through evidence-first creative direction. |
| scripts/marketing/build_content_calendar.py | WRAP | Content calendar generation is a bounded marketing planning surface already in place. |
| scripts/marketing/build_newsletter_draft.py | WRAP | Newsletter drafting is already a bounded marketing artifact and should not fork into another system. |
| scripts/marketing/build_social_draft_queue.py | WRAP | Social draft queue is existing bounded creative infrastructure. |
| scripts/marketing/build_short_video_script_queue.py | WRAP | Video script queue already exists and should be controlled as a creative artifact source. |
| scripts/design/create_feature_design_packet.py | WRAP | Feature design packets are existing design artifacts that the lab can reference instead of duplicate. |
| scripts/design/extract_design_patterns.py | WRAP | Pattern extraction already provides a reusable, deterministic design signal source. |
| scripts/design/register_design_inspiration.py | WRAP | Design inspiration registry is already the right place for reference collection. |
| scripts/design/review_ui_quality.py | MERGE | UI quality review can feed territory verification and distinctiveness checks. |
| scripts/seed_day9_creative_design_department.py | MERGE | The seeded creative design department is already a deterministic workflow and should be reused. |
| reports/hermes_modernization/open_source_capability_audit.json | WRAP | Provides the public-evidence reference set for the safe pilot. |
| reports/marketing_assets/* | MERGE | Existing draft assets are reference material, not a replacement for the creative lab. |
| frontend design tool installs | DEFER | Penpot, Excalidraw, and similar tools are future research only for this phase. |
| brand-guideline generation pipeline | WRAP | Brand guidance already exists implicitly in current marketing artifacts and should be referenced, not recreated. |
| new persistent creative agent | CREATE_NEW | Not allowed; creative direction remains a skill used by Hermes orchestration. |
