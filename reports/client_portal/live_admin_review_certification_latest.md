# Admin Review Workflow Certification — Client Portal

**Date:** 2026-07-08
**Starting Commit:** 71b9dd4

---

## Admin Access Architecture

### Admin UI: `NexusAdminUI.jsx`
- Hash-based navigation (e.g., `/#clients`)
- AuthGate requires Supabase session
- Admin access gated by `admin_users` table RLS policy
- `nexus_is_active_admin()` function checks admin status

### Client Management: `ClientsPanel.jsx`
- Lists clients from `clientsData.js` (static) or Supabase (live)
- Client detail drawer with:
  - Profile info (email, status, stage, membership, payment)
  - Readiness scores
  - Document list
  - Task list
  - Message list
  - Storage files (from `client-documents` bucket)
  - Admin notes
  - Approve/Hold/Ask Hermes actions

---

## Admin Visibility Check

### Tester Profile
- **Status:** PARTIAL
- `ClientsPanel` shows static client data from `clientsData.js`
- Client detail drawer displays profile fields
- No live Supabase query for individual tester profiles

### Readiness Score
- **Status:** PARTIAL
- Client detail drawer shows `client.readinessScores` object
- Comes from static data, not live Supabase query

### Tasks
- **Status:** PARTIAL
- Client detail drawer shows `client.tasks` array
- Comes from static data

### Document Metadata
- **Status:** PARTIAL
- Client detail drawer lists `client.documents.requiredDocuments`
- Storage files loaded from Supabase Storage bucket
- No `client_documents` table query

### Credit Workflow Items
- **Status:** NOT VISIBLE
- Admin UI does not display `credit_workflow_items` data
- Table exists in schema but not queried by admin

### Business Profile Requirements
- **Status:** NOT VISIBLE
- Admin UI does not display `business_profile_requirements` data
- Table exists in schema but not queried by admin

### Approved Guidance
- **Status:** NOT VISIBLE
- Admin UI does not display `approved_client_guidance` data
- Table exists in schema but not queried by admin

### Review Requests
- **Status:** NOT IMPLEMENTED
- No review submission mechanism in client portal
- No admin review queue visible

---

## Admin Actions Available

| Action | Status | Backend |
|---|---|---|
| Approve client | UI only | Receipt object, no DB write |
| Hold client | UI only | Receipt object, no DB write |
| Ask Hermes | UI only | Passes prompt to Hermes panel |
| Save admin note | UI only | Local state, no persistence |

---

## Blockers

1. **Admin cannot see live tester data** — `ClientsPanel` uses static `clientsData.js`, not Supabase queries
2. **Credit workflow items not visible** — table exists but not queried
3. **Business profile requirements not visible** — table exists but not queried
4. **Approved guidance not visible** — table exists but not queried
5. **No review request queue** — client cannot submit, admin cannot see

---

## Summary

| Check | Result |
|---|---|
| Admin can see tester profile | PARTIAL (static data) |
| Admin can see readiness score | PARTIAL (static data) |
| Admin can see tasks | PARTIAL (static data) |
| Admin can see document metadata | PARTIAL (static + storage) |
| Admin can see credit workflow items | NOT VISIBLE |
| Admin can see business profile requirements | NOT VISIBLE |
| Admin can see approved guidance | NOT VISIBLE |
| Admin can see review requests | NOT IMPLEMENTED |

**STATUS: Partial — admin can see some client data via static fallback. Live Supabase data connection not wired to admin UI for client-specific tables.**
