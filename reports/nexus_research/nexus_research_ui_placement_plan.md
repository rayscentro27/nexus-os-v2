# Nexus Research UI Placement Plan

**Generated**: 2026-07-03  
**Purpose**: Define where credit/funding research appears in the Nexus admin UI

---

## Current Admin Navigation (from NexusAdminUI.jsx)

The admin panel already has these relevant nav items:
- Credit & Funding
- Readiness Intake (`#readiness-intake`)
- Readiness Review (`#readiness-admin`)
- Research
- Ray Review
- Reports

---

## Recommended UI Areas

### 1. Nexus Research (Admin Panel)

**Location**: Extend existing "Research" nav item  
**Access**: Admin-only  
**Label**: "Nexus Credit & Funding Research"

| Section | Content | Status |
|---------|---------|--------|
| Research Dashboard | Overview of collected artifacts by category | To build |
| Credit Repair Research | Collected credit repair artifacts | To build |
| Business Funding Research | Collected funding artifacts | To build |
| Grants Research | Collected grant opportunities | To build |
| Lender Research | Admin-only lender notes | To build |
| Affiliate Research | Affiliate offer evaluations | To build |
| Compliance Notes | Compliance research notes | To build |
| Client Education | Draft educational content | To build |

### 2. Credit Repair Research (Detail Page)

**Location**: Sub-page of Nexus Research  
**Access**: Admin-only  
**Label**: "Credit Repair Research"

| Section | Content |
|---------|---------|
| Artifact List | All credit repair research artifacts |
| Artifact Detail | Full artifact with evidence quality, compliance flags |
| To Admin Notes | Button to generate admin notes from artifact |
| To Client Education | Button to draft client education (requires Ray Review) |
| To Dispute Draft | Button to draft dispute content (requires Ray Review + FCRA) |

### 3. Business Funding Research (Detail Page)

**Location**: Sub-page of Nexus Research  
**Access**: Admin-only  
**Label**: "Business Funding Research"

| Section | Content |
|---------|---------|
| Artifact List | All business funding research artifacts |
| Artifact Detail | Full artifact with evidence quality, compliance flags |
| To Admin Notes | Button to generate admin notes from artifact |
| To Client Education | Button to draft client education (requires Ray Review) |
| To Funding Recommendation | Button to draft funding recommendation (requires Ray Review) |

### 4. Grants Research (Detail Page)

**Location**: Sub-page of Nexus Research  
**Access**: Admin-only  
**Label**: "Grants Research"

| Section | Content |
|---------|---------|
| Artifact List | All grant opportunity artifacts |
| Artifact Detail | Full artifact with evidence quality, compliance flags |
| To Admin Notes | Button to generate admin notes from artifact |
| To Client Education | Button to draft client education (requires Ray Review) |

### 5. Affiliate Offer Research (Detail Page)

**Location**: Sub-page of Nexus Research  
**Access**: Admin-only  
**Label**: "Affiliate Offer Research"

| Section | Content |
|---------|---------|
| Artifact List | All affiliate offer artifacts |
| Artifact Detail | Full artifact with evidence quality, compliance flags |
| To Admin Notes | Button to generate admin notes from artifact |
| To Ray Review | Button to submit for Ray Review (requires approval) |
| Activation Status | Current activation status of all partner programs |

### 6. Compliance Notes (Detail Page)

**Location**: Sub-page of Nexus Research  
**Access**: Admin-only  
**Label**: "Compliance Notes"

| Section | Content |
|---------|---------|
| Artifact List | All compliance research artifacts |
| Artifact Detail | Full artifact with evidence quality |
| FCRA Notes | FCRA compliance notes |
| FDCPA Notes | FDCPA compliance notes (currently empty) |
| Policy Updates | Recent policy/guardrail changes |
| To Ray Review | Button to submit for Ray Review |

### 7. Client Education (Detail Page)

**Location**: Sub-page of Nexus Research  
**Access**: Admin-only (draft), Client-facing (approved)  
**Label**: "Client Education Drafts"

| Section | Content |
|---------|---------|
| Draft List | All client education drafts |
| Draft Detail | Full draft with compliance review status |
| Approval Status | Ray Review status for each draft |
| Publish Status | Whether draft is approved for client-facing |

### 8. Research-to-Readiness Recommendations

**Location**: Sub-page of Readiness Review  
**Access**: Admin-only  
**Label**: "Research Recommendations"

| Section | Content |
|---------|---------|
| Recommendation List | All recommendations generated from research |
| Recommendation Detail | Full recommendation with approval status |
| Source Artifacts | Links to source research artifacts |
| Approval Gate | Current gate level and next step |

### 9. Ray Review Queue (Research)

**Location**: Sub-page of Ray Review  
**Access**: Ray only  
**Label**: "Research Reviews"

| Section | Content |
|---------|---------|
| Pending Reviews | All research outputs awaiting Ray Review |
| Review Detail | Full output with source artifacts, compliance flags |
| Approve/Reject | Action buttons with notes |
| History | Previously reviewed research outputs |

---

## UI Mounting Rules

### Phase 1: Design Only (Current)
- Do NOT mount new UI components yet
- Document placement plan only
- Existing `#readiness-intake` and `#readiness-admin` are sufficient for $97 review

### Phase 2: Research Dashboard (Future)
- Mount `NexusResearchDashboard` at `#nexus-research`
- Show artifact counts by category
- Show collection status
- Show approval gate status

### Phase 3: Research Detail Pages (Future)
- Mount detail pages as sub-routes of `#nexus-research`
- Each category gets its own detail page
- All pages admin-only until approval gates built

### Phase 4: Client Education Portal (Future)
- Mount approved education content in client portal
- Separate from admin research pages
- Only approved content visible to clients

---

## Safety Labels

Every UI element must include:
- "Research / Draft Only" label for admin pages
- "Requires Ray Review" label for approval-gated content
- "Admin Only" label for restricted content
- "Not Financial Advice" disclaimer for funding content
- "Not Legal Advice" disclaimer for compliance content
- "Not a Guarantee" disclaimer for credit/funding outcomes

---

## Implementation Priority

1. **Do not mount UI yet** — design only
2. When mounting, start with dashboard only
3. Add detail pages incrementally
4. Always label as draft/research-only
5. Never mount client-facing until approval gates built
