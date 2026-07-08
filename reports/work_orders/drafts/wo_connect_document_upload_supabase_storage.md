# Work Order: Connect Document Upload Flow to Supabase Storage

**Status:** Draft
**Priority:** High
**Source:** Client Portal Premium UI Foundation Sprint
**Created:** 2026-07-07

## Objective
Enable real document upload from the client portal to Supabase Storage.

## Scope
- Implement drag-and-drop upload component
- Upload to Supabase Storage bucket (`client-documents`)
- Store file metadata in `client_documents` table
- Link documents to client profile via `client_id`
- Show upload progress and verification status

## Acceptance Criteria
- Client can drag-and-drop or click to upload PDF/JPG/PNG
- File appears in "Uploaded" section after upload
- File metadata stored in Supabase with correct `client_id`
- Upload size limit enforced (25MB)
- Verification status tracked (pending → verified)

## Dependencies
- Supabase Storage bucket `client-documents` must exist
- RLS policies must allow authenticated client uploads
- `client_documents` table must have `storage_path` column

## Notes
- Current upload is disabled in prototype ("Upload is disabled in this prototype")
- Production requires private storage, consent, tenant isolation, and GoClear approval
