# Client Portal Supabase Data Contract Map

## Canonical Tables

### client_profiles
- **Purpose**: Core client record, visible to client and admin
- **Key columns**: `id`, `tenant_id`, `client_id`, `name`, `email`, `status`, `client_visible`, `approval_required`, `payload`
- **Read consumers**:
  - `clientPortalDataAdapter.ts` (live adapter)
  - `useClientPortalData.ts` (portal data hook)
  - `ClientsPanel.jsx` (admin drawer)
  - All client portal pages via `clientPortalData.js` fallback
- **Write consumers**: `tenant_memberships` trigger on signup (bootstrap)
- **Frontend files**: `src/lib/clientPortalDataAdapter.ts`, `src/pages/client/ClientPortalPages.jsx`
- **Admin files**: `src/components/ClientsPanel.jsx`
- **RLS**: `client_profiles_tenant_select` (self + admin), `client_profiles_operator_write` (admin only), `client_profiles_self_update` (self only)
- **Client read/write**: Read if `client_visible = true` or own profile; update own profile only
- **Admin read/write**: Full read/write via `nexus_is_active_admin()`
- **Status**: PARTIAL — live adapter exists but many pages still use static `clientPortalData.js`

### tenant_memberships
- **Purpose**: Maps auth users to tenants/roles/client profiles
- **Key columns**: `tenant_id`, `user_id`, `role`, `client_id`
- **Read consumers**:
  - `clientAuthContext.ts` (resolve client context)
  - `useClientPortalData.ts` (portal data hook)
  - `adminAccess.ts` (admin guard)
- **Write consumers**: GoClear signup trigger/bootstrap
- **Frontend files**: `src/lib/clientAuthContext.ts`, `src/clientPortal/useClientPortalData.ts`, `src/lib/adminAccess.ts`
- **Admin files**: `src/components/ClientsPanel.jsx`
- **RLS**: `memberships_self_or_admin_select`, `memberships_admin_manage`
- **Client read/write**: Read own row only; no write
- **Admin read/write**: Full via `nexus_is_active_admin()`
- **Status**: LIVE — critical for auth→client mapping

### client_tasks
- **Purpose**: Task list including review requests
- **Key columns**: `id`, `tenant_id`, `client_id`, `category`, `title`, `status`, `priority`, `client_visible`, `approval_required`, `goclear_review_status`, `source`, `source_concept`, `recommended_next_action`, `created_at`
- **Read consumers**:
  - `clientPortalDataAdapter.ts`
  - `useClientPortalData.ts`
  - `ClientPortalPages.jsx` (dashboard, request review)
  - `ClientsPanel.jsx` (admin drawer)
- **Write consumers**:
  - `ClientPortalPages.jsx` (Request Review submit)
  - `DocumentUploadZone.tsx` (indirect via metadata)
- **Frontend files**: `src/lib/clientPortalDataAdapter.ts`, `src/pages/client/ClientPortalPages.jsx`, `src/components/client/DocumentUploadZone.tsx`
- **Admin files**: `src/components/ClientsPanel.jsx`, `src/components/sections.tsx`
- **RLS**: `client_tasks_tenant_select`, `client_tasks_operator_write`
- **Client read/write**: Read own visible tasks; no write except review request insert
- **Admin read/write**: Full via `nexus_is_active_admin()` or operator role
- **Status**: LIVE — reads work; write (review request) works with resolved context

### client_documents
- **Purpose**: Document metadata for client uploads
- **Key columns**: Same as `client_tasks` plus file metadata fields
- **Read consumers**:
  - `clientPortalDataAdapter.ts`
  - `useClientPortalData.ts`
  - `ClientPortalPages.jsx` (Documents page)
  - `ClientsPanel.jsx` (admin drawer)
  - `clientDashboardLiveData.ts`
- **Write consumers**:
  - `DocumentUploadZone.tsx` (Storage + metadata insert)
- **Frontend files**: `src/lib/clientPortalDataAdapter.ts`, `src/components/client/DocumentUploadZone.tsx`, `src/pages/client/ClientPortalPages.jsx`
- **Admin files**: `src/components/ClientsPanel.jsx`
- **RLS**: `client_documents_tenant_select`, `client_documents_operator_write`, `client_documents_client_insert_own`
- **Client read/write**: Read own visible docs; insert own docs with safe constraints
- **Admin read/write**: Full via `nexus_is_active_admin()` or operator role
- **Status**: LIVE — upload + metadata insert works; display fixed in R2

### readiness_scores
- **Purpose**: Client readiness scoring
- **Key columns**: Same schema family
- **Read consumers**: `clientPortalDataAdapter.ts`, `useClientPortalData.ts`, all portal pages
- **Write consumers**: Admin/operator via RLS
- **Frontend files**: `src/lib/clientPortalDataAdapter.ts`
- **Admin files**: `src/components/sections.tsx`
- **RLS**: `readiness_scores_tenant_select`, `readiness_scores_operator_write`
- **Client read/write**: Read own visible scores; no write
- **Admin read/write**: Full
- **Status**: FALLBACK — adapter exists but most pages use static data

### credit_workflow_items
- **Purpose**: Credit repair workflow tracking
- **Key columns**: Same schema family
- **Read consumers**: `clientPortalDataAdapter.ts` (not currently used in pages)
- **Write consumers**: Admin/operator
- **Frontend files**: None active (adapter has function but pages don't call it)
- **Admin files**: None identified
- **RLS**: `credit_workflow_items_tenant_select`, `credit_workflow_items_operator_write`
- **Client read/write**: Read own visible items; no write
- **Admin read/write**: Full
- **Status**: UNKNOWN — schema exists but not wired to UI

### business_profile_requirements
- **Purpose**: Business setup checklist
- **Key columns**: Same schema family
- **Read consumers**: `clientPortalDataAdapter.ts`
- **Write consumers**: Admin/operator
- **Frontend files**: `src/lib/clientPortalDataAdapter.ts`
- **Admin files**: None identified
- **RLS**: `business_profile_requirements_tenant_select`, `business_profile_requirements_operator_write`
- **Client read/write**: Read own visible items; no write
- **Admin read/write**: Full
- **Status**: FALLBACK — adapter exists but BusinessSetupPage uses static data

### approved_client_guidance
- **Purpose**: Approved guidance shown to clients
- **Key columns**: Same schema family
- **Read consumers**: `clientPortalDataAdapter.ts`
- **Write consumers**: Admin/operator
- **Frontend files**: `src/lib/clientPortalDataAdapter.ts`
- **Admin files**: None identified
- **RLS**: `approved_client_guidance_tenant_select`, `approved_client_guidance_operator_write`
- **Client read/write**: Read own visible guidance; no write
- **Admin read/write**: Full
- **Status**: FALLBACK — adapter exists but pages use static guidance

### admin_users
- **Purpose**: Active admin identity
- **Key columns**: `id`, `email`, `role`, `active`, `created_at`
- **Read consumers**: `adminAccess.ts` (frontend guard), `nexus_is_active_admin()` (RLS function)
- **Write consumers**: None in audited frontend
- **Frontend files**: `src/lib/adminAccess.ts`
- **Admin files**: RLS migration
- **RLS**: `admin_users_select_self` (read own row), `nexus_is_active_admin()` uses this table
- **Client read/write**: None
- **Admin read/write**: Self-read only via RLS; admin manage via `nexus_is_active_admin()`
- **Status**: LIVE — gating admin access

### storage.objects (bucket: client-documents)
- **Purpose**: Actual document file storage
- **Key columns**: `bucket_id`, `name`, `metadata`
- **Read consumers**: `ClientsPanel.jsx` (admin file listing), clients (own folder only)
- **Write consumers**: `DocumentUploadZone.tsx` (client upload)
- **Frontend files**: `src/components/client/DocumentUploadZone.tsx`, `src/components/ClientsPanel.jsx`
- **Admin files**: `src/components/ClientsPanel.jsx`
- **RLS**: `client_documents_upload_own`, `client_documents_read_own`, `client_documents_read_admin`, `client_documents_delete_admin`
- **Client read/write**: Upload/read files in `{auth.uid()}/` folder
- **Admin read/write**: Read/delete any file in bucket
- **Status**: LIVE — upload works; admin file listing works

## Contract Summary

| Table | Client Read | Client Write | Admin Read | Admin Write | Frontend Live | Status |
|-------|------------|--------------|------------|-------------|---------------|--------|
| client_profiles | Own + visible | No | Full | Full | Partial | PARTIAL |
| tenant_memberships | Own | No | Full | Full | Live | LIVE |
| client_tasks | Own visible | Review request only | Full | Full | Partial | PARTIAL |
| client_documents | Own visible | Own upload | Full | Full | Partial | PARTIAL |
| readiness_scores | Own visible | No | Full | Full | Fallback | FALLBACK |
| credit_workflow_items | Own visible | No | Full | Full | Unknown | UNKNOWN |
| business_profile_requirements | Own visible | No | Full | Full | Fallback | FALLBACK |
| approved_client_guidance | Own visible | No | Full | Full | Fallback | FALLBACK |
| admin_users | No | No | Self | No | Live | LIVE |
| storage.client-documents | Own folder | Own upload | Any | Delete | Live | LIVE |
