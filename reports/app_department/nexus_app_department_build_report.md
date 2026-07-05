# App Department Build Report

**Generated:** 2026-07-05  
**Status:** Framework Initialized

---

## Findings

### App Idea Intake
- Intake form structure defined: idea name, problem statement, target user, success metrics
- Stored in `app_department.ideas` table
- Ideas auto-scored for feasibility (1–10) and impact (1–10)

### Requirements Generator
- Template-based requirements extraction from intake form
- Output: functional requirements list, non-functional requirements, constraints
- Format: structured JSON for downstream consumption

### UI / Page Spec
- Spec generator produces: page layout, component list, state management, responsive breakpoints
- Output format: markdown spec with component hierarchy
- Integrates with existing page templates in `src/`

### Data Model Planner
- Entity-relationship extraction from requirements
- Output: Supabase table schema, RLS policies, API surface
- Validates against existing schema to prevent conflicts

### Prototype Work Order
- Auto-generates work order from specs + requirements + data model
- Includes: file list, component hierarchy, routing, testing requirements
- Template: `app_work_order_template.md`

### Test Plan
- Generated alongside prototype work order
- Unit test specs, integration test specs, manual QA checklist
- Output: test file templates with placeholder assertions

### Recovery Prompt Template
- If prototype fails or stalls: recovery prompt template for re-initialization
- Includes: last known good state, error context, retry instructions

## Next Actions

1. Build CLI command: `nexus app-intake` to submit new ideas
2. Wire requirements generator to Supabase storage
3. Create UI spec generator with visual component preview
4. Test data model planner against 3 sample ideas
5. Build work order auto-generation pipeline
6. Create recovery prompt template file
