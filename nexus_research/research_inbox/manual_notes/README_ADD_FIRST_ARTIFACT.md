# How to Add Your First Nexus Research Artifact

**Purpose**: This file explains how Ray can add the first real research artifact to the Nexus Credit & Funding Research inbox.

---

## Step 1: Choose a Category

Pick the inbox folder that matches your research:

| Category | Folder | Example Topic |
|----------|--------|---------------|
| Credit Repair | `credit_repair/` | Dispute strategies, FCRA rights |
| Credit Utilization | `credit_utilization/` | Utilization scoring, balance optimization |
| Business Setup | `business_setup/` | LLC formation, EIN registration, DUNS |
| Business Funding | `business_funding/` | SBA loans, credit lines, business credit cards |
| Grants | `grants/` | Federal grants, minority business grants |
| Lenders | `lenders/` | Bank lending criteria, credit union requirements |
| Affiliates | `affiliates/` | Bank referral programs, credit monitoring affiliates |
| Compliance | `compliance/` | FCRA compliance, FDCPA requirements |
| Client Education | `client_education/` | Credit report basics, utilization education |
| Manual Notes | `manual_notes/` | Your own observations and evaluations |

## Step 2: Create the Markdown File

Use this naming convention:
```
YYYY-MM-DD_topic_description.md
```

Examples:
- `2026-07-03_credit_utilization_research.md`
- `2026-07-03_business_funding_readiness_note.md`
- `2026-07-03_business_setup_bankability_note.md`
- `2026-07-03_grant_research_note.md`
- `2026-07-03_lender_program_note.md`

## Step 3: Use This Template

```markdown
# [Title of Research]

**Source or note origin**: [Where did this information come from?]
**Date collected**: [YYYY-MM-DD]
**Category**: [credit_repair / credit_utilization / business_setup / business_funding / grants / lenders / affiliates / compliance / client_education / manual_note]

## Summary

[1-3 sentence summary of the research]

## Key Points

- [Key point 1]
- [Key point 2]
- [Key point 3]

## Compliance Cautions

- [Any FCRA, FDCPA, FTC, or legal considerations]
- [Or "None identified"]

## Intended Nexus Use

- [How should Nexus use this research?]
- [Which workflow does it support?]

## Client-Facing?

Should this be client-facing? [yes / no / pending]

## Ray Review Required?

yes
```

## Step 4: Place the File

Put the file in the appropriate inbox folder:
```
nexus_research/research_inbox/[category]/YYYY-MM-DD_topic_description.md
```

## Step 5: Run the Adapter

The adapter will:
1. Discover your file
2. Validate the path
3. Compute SHA-256 hash
4. Extract metadata
5. Classify the category
6. Route to the correct workflow
7. Flag any compliance or guarantee risks
8. Generate an admin note
9. Generate a Ray Review draft

## Rules

- **No fake research** — only add real information
- **No guarantees** — never promise approval, funding, or score increases
- **No client data** — only general research, not individual client information
- **Ray Review required** — all client-facing output needs approval
- **Draft only** — nothing goes live without approval
