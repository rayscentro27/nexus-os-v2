# Nexus Research Scoring Thresholds

**Generated**: 2026-07-05

---

## Proposed Scoring System

### Score Ranges

| Range | Classification | Action | Visibility | Ray Review |
|-------|---------------|--------|------------|------------|
| 0-39 | Low value | Store metadata/archive only | Hidden from Hermes unless searched | No |
| 40-59 | Medium value | Store summary/tags | Visible in research archive | No |
| 60-79 | Opportunity candidate | Full analysis | Visible to Alpha/Hermes, weekly review | No |
| 80-100 | High value | Action recommendation | Ray Review required | Yes |

---

## Scoring Factors

### Content Quality (0-30 points)
- Transcript quality/completeness
- Source credibility
- Information density
- Actionability

### Relevance (0-25 points)
- Match to Nexus topics (credit, funding, business, trading)
- Match to Ray's interests
- Timeliness
- Uniqueness

### Monetization Potential (0-25 points)
- Revenue opportunity clarity
- Implementation complexity
- Time to value
- Scalability

### Actionability (0-20 points)
- Clear next steps
- Resource requirements
- Risk level
- Dependencies

---

## Threshold Applications

### 0-39: Archive Only
- Store in `data/cache/` or `data/sources/`
- Index in research registry
- Hermes does not surface unless explicitly searched
- No Alpha review
- No Ray Review

### 40-59: Research Archive
- Store with summary and tags
- Visible in research archive panel
- Included in weekly research digest
- Alpha may reference in conversations
- No Ray Review required

### 60-79: Opportunity Candidate
- Full analysis with scoring breakdown
- Visible to Alpha brain
- Visible to Nexus Hermes
- Included in weekly opportunity review
- Alpha may create action drafts
- No Ray Review required unless action involves external systems

### 80-100: Ray Review Required
- Complete analysis with recommendation
- Specific action, branch, experiment, funnel, or monetization suggestion
- Ray Review card created
- Visible in Ray Review queue
- Requires explicit Ray approval before execution
- May involve external systems, spending, or public-facing actions

---

## Existing Scoring Infrastructure

| Component | Location | Status |
|-----------|----------|--------|
| Alpha scoring engine | `src/hermes/alpha/alphaScoring.ts` | Built |
| Research scoring policy | `configs/research_scoring_policy.json` | Config exists |
| Opportunity scoring | `src/hermes/alpha/alphaSeoMoneyOpportunityEngine.ts` | Built |
| Trading scoring | `src/hermes/alpha/alphaTradingResearchPipeline.ts` | Built |
| Ray Review proposal | `src/hermes/alpha/rayReviewProposal.ts` | Built |

---

## Recommendation for Prompt 2

1. Connect YouTube research output to scoring engine
2. Connect NotebookLM imports to scoring engine
3. Wire scoring output to Alpha/Hermes visibility
4. Test with synthetic research items
5. Calibrate thresholds based on Ray's review patterns
