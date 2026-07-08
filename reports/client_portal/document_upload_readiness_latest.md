# Document Upload Readiness

**Date:** 2026-07-07

## Storage Audit

- **Supabase Storage bucket:** Not found (no `storage.buckets` insert in any migration)
- **Storage policies:** Not found (line 682 of client portal migration says "Private storage bucket and storage.objects policies require separate review and are intentionally not auto-created")
- **Frontend upload code:** Disabled/placeholder only — `ClientDocumentsPage` shows "Upload is disabled in this prototype"
- **Upload-related components:** `ClientUploadPlaceholder` (static, no actual upload logic)

## Current Status

- Document upload is **not functional** — placeholder UI only
- No storage bucket exists for client documents
- No storage policies exist
- No file upload service is implemented

## What Is Needed to Safely Enable Tester Uploads

1. Create a private Supabase Storage bucket (e.g., `client-documents`)
2. Create storage policies:
   - Authenticated users can upload to their own folder (`{user_id}/`)
   - Authenticated users can read their own files
   - Admins can read all files
3. Implement frontend upload component with:
   - File type validation (PDF, JPG, PNG)
   - File size limit (e.g., 10MB)
   - Progress indicator
   - Error handling
   - Link to `client_documents` table record
4. Create `client_document_uploads` table or use `client_documents.payload` JSONB for file metadata

## Recommendation for First 10 Testers

- Keep upload disabled for initial tester round
- Testers can view document requirements and status
- Document upload to be enabled in a follow-up sprint after storage policies are reviewed and approved

## Work Order

See: `reports/work_orders/drafts/wo_enable_document_upload_supabase_storage.md`
