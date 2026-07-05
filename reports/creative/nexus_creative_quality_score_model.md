# Creative Quality Score Model

**Generated:** 2026-07-05  
**Status:** Specification  

## 10 Scoring Dimensions

### 1. Hook Strength (Weight: 15%)

**Definition:** How effectively the opening captures attention.

| Score | Criteria |
|-------|----------|
| 90-100 | Pattern interrupt + curiosity + emotional trigger |
| 80-89 | Strong hook, minor improvements needed |
| 70-79 | Adequate hook, could be stronger |
| 60-69 | Weak hook, needs revision |
| Below 60 | No hook, must redo |

**Scoring factors:**
- First 3 seconds impact
- Pattern interrupt present
- Curiosity generated
- Emotional trigger activated
- Relevance to target audience

### 2. Message Clarity (Weight: 12%)

**Definition:** How clearly the core message is communicated.

| Score | Criteria |
|-------|----------|
| 90-100 | Single message, crystal clear, no jargon |
| 80-89 | Clear message, minor complexity |
| 70-79 | Message present, some confusion possible |
| 60-69 | Multiple messages, diluted |
| Below 60 | Unclear, must redo |

**Scoring factors:**
- Single focus maintained
- Jargon-free language
- Easy to understand on first pass
- Key point is obvious
- No competing messages

### 3. Visual Appeal (Weight: 10%)

**Definition:** How visually appealing and professional the content looks.

| Score | Criteria |
|-------|----------|
| 90-100 | Stunning, brand-perfect, professional |
| 80-89 | Professional, minor visual issues |
| 70-79 | Acceptable, some visual problems |
| 60-69 | Amateur, needs polish |
| Below 60 | Poor quality, must redo |

**Scoring factors:**
- Color harmony
- Typography readability
- Image quality
- Brand consistency
- Professional appearance

### 4. Emotional Resonance (Weight: 12%)

**Definition:** How well the content connects emotionally with the audience.

| Score | Criteria |
|-------|----------|
| 90-100 | Deep emotional connection, relatable |
| 80-89 | Strong emotional appeal |
| 70-79 | Some emotional connection |
| 60-69 | Weak emotional appeal |
| Below 60 | No emotional connection |

**Scoring factors:**
- Relatability to target audience
- Pain point addressed
- Aspiration created
- Storytelling effectiveness
- Empathy demonstrated

### 5. Call-to-Action (Weight: 10%)

**Definition:** How effective the CTA is at driving desired action.

| Score | Criteria |
|-------|----------|
| 90-100 | Clear, urgent, compelling, easy |
| 80-89 | Strong CTA, minor friction |
| 70-79 | Adequate CTA, some friction |
| 60-69 | Weak CTA, significant friction |
| Below 60 | No clear CTA, must redo |

**Scoring factors:**
- CTA clarity
- CTA placement
- Urgency created
- Friction minimized
- Relevance to content

### 6. Brand Alignment (Weight: 8%)

**Definition:** How well the content aligns with brand guidelines.

| Score | Criteria |
|-------|----------|
| 90-100 | Perfect brand alignment |
| 80-89 | Strong alignment, minor deviations |
| 70-79 | Acceptable alignment |
| 60-69 | Significant deviations |
| Below 60 | Off-brand, must redo |

**Scoring factors:**
- Voice consistency
- Visual identity
- Value alignment
- Tone appropriateness
- Brand story support

### 7. Platform Optimization (Weight: 10%)

**Definition:** How well the content is optimized for the target platform.

| Score | Criteria |
|-------|----------|
| 90-100 | Perfect platform fit, algorithm-optimized |
| 80-89 | Strong optimization |
| 70-79 | Adequate optimization |
| 60-69 | Poor optimization |
| Below 60 | Wrong platform fit, must redo |

**Scoring factors:**
- Format compliance
- Length appropriateness
- Platform-specific best practices
- Algorithm awareness
- Technical requirements met

### 8. Shareability (Weight: 8%)

**Definition:** How likely the content is to be shared.

| Score | Criteria |
|-------|----------|
| 90-100 | Highly viral, share-worthy |
| 80-89 | Likely to be shared |
| 70-79 | Possibly shared |
| 60-69 | Unlikely to be shared |
| Below 60 | Won't be shared |

**Scoring factors:**
- Viral potential
- Quote-worthy moments
- Tag-worthiness
- Save-worthy value
- Conversation starter

### 9. Conversion Potential (Weight: 8%)

**Definition:** How likely the content is to drive conversions.

| Score | Criteria |
|-------|----------|
| 90-100 | High conversion likelihood |
| 80-89 | Good conversion potential |
| 70-79 | Moderate conversion potential |
| 60-69 | Low conversion potential |
| Below 60 | No conversion potential |

**Scoring factors:**
- Action motivation
- Barrier reduction
- Trust building
- Urgency creation
- Value proposition clarity

### 10. Compliance (Weight: 7%)

**Definition:** How well the content meets legal and policy requirements.

| Score | Criteria |
|-------|----------|
| 90-100 | Fully compliant |
| 80-89 | Compliant, minor issues |
| 70-79 | Mostly compliant |
| 60-69 | Compliance gaps |
| Below 60 | Non-compliant, must fix |

**Scoring factors:**
- Legal requirements met
- Platform policies followed
- Brand guidelines adhered
- Industry regulations compliant
- Disclaimers present

## Weightings

```typescript
const DIMENSION_WEIGHTS = {
  hook: 0.15,
  clarity: 0.12,
  visuals: 0.10,
  emotion: 0.12,
  cta: 0.10,
  brand: 0.08,
  platform: 0.10,
  shareability: 0.08,
  conversion: 0.08,
  compliance: 0.07
};
```

## Thresholds

| Overall Score | Status | Action |
|---------------|--------|--------|
| 90-100 | Excellent | Auto-approve |
| 80-89 | Good | Ray review (fast track) |
| 70-79 | Acceptable | Ray review |
| 60-69 | Needs Work | Revision required |
| Below 60 | Poor | Redo required |

## Scoring Formula

```
Overall Score = Σ (dimension_score × dimension_weight)
```

### Example

```
Hook: 85 × 0.15 = 12.75
Clarity: 80 × 0.12 = 9.60
Visuals: 75 × 0.10 = 7.50
Emotion: 82 × 0.12 = 9.84
CTA: 78 × 0.10 = 7.80
Brand: 88 × 0.08 = 7.04
Platform: 85 × 0.10 = 8.50
Shareability: 72 × 0.08 = 5.76
Conversion: 80 × 0.08 = 6.40
Compliance: 95 × 0.07 = 6.65

Overall: 81.84 → Good → Ray review (fast track)
```

## Next Actions

1. Implement scoring engine
2. Create scoring UI for Ray
3. Build auto-scoring for obvious cases
4. Create feedback templates
5. Add scoring analytics
6. Build scoring history
7. Create scoring reports
8. Train auto-scoring model
