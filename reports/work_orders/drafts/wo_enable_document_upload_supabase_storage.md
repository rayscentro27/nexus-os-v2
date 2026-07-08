# Work Order: Enable Document Upload to Supabase Storage

**Status:** Draft
**Priority:** High
**Created:** 2026-07-07

## Goal
Create a private Supabase Storage bucket with policies for client document uploads.

## Why It Matters
Testers cannot upload credit reports, proof of address, or other documents without storage.

## Scope
1. Create private storage bucket `client-documents`
2. Create storage policies:
   - Authenticated users can upload to `{user_id}/` folder
   - Authenticated users can read their own files
   - Admins can read all files
3. Create frontend upload component
4. Link uploads to `client_documents` table

## Acceptance Criteria
- Storage bucket exists
- Client can upload files to their own folder
- Client can read their own files
- Admin can read all client files
- Upload UI shows progress and error states
- File type/size validation works

## Files Involved
- `supabase/migrations/` (new migration for bucket + policies)
- `src/components/client/` (upload component)
- `src/pages/client/ClientPortalPages.jsx` (replace placeholder)

## Risk Level
Medium — requires storage policy review

## Test Plan
1. Create bucket via Supabase Dashboard
2. Test upload as authenticated client
3. Test read as same client
4. Test read as admin
5. Test rejection of unauthenticated access
