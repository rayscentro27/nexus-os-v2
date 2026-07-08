# Document Upload Workflow Certification — Client Portal

**Date:** 2026-07-08
**Starting Commit:** 71b9dd4
**Test File:** `tmp/test-upload-proof-of-address.txt` (created successfully)

---

## Upload Architecture

### Component: `DocumentUploadZone.tsx`
- Drag-and-drop zone with click-to-browse
- File type validation: PDF, JPEG, PNG, HEIC, TXT, DOCX
- File size limit: 10MB
- Progress tracking per file
- Error/success state display

### Storage: Supabase `client-documents` bucket
- Private bucket (created in `20260707120000_client_document_storage.sql`)
- Path pattern: `{user.id}/{timestamp}_{sanitizedName}`
- RLS policies: authenticated upload, owner read/delete

---

## Workflow Test Results

### Step 1: Client clicks Upload Now
- **Status:** PASS
- Dashboard hero CTA → `navigate('/client/documents')`
- Route resolves to Documents page

### Step 2: Route goes to Documents
- **Status:** PASS
- `/client/documents` renders `ClientDocumentsPage`
- `DocumentUploadZone` component rendered inside "Upload documents" section

### Step 3: Upload control is present
- **Status:** PASS
- Dropzone visible with "Drop files here or click to upload"
- File type/size info displayed: "PDF, JPEG, PNG, HEIC, TXT, DOCX — Max 10MB"

### Step 4: File type/size guard works
- **Status:** PASS (code verified)
- `validateFile()` checks `ALLOWED_TYPES` array and `MAX_SIZE = 10MB`
- Invalid types rejected with message
- Oversized files rejected with message

### Step 5: Dummy file upload
- **Status:** PARTIAL
- Upload flow: `handleFiles()` → validate → check auth → upload to Supabase Storage
- If Supabase not configured: shows error "Supabase not configured"
- If not signed in: shows error "Not signed in"
- If signed in: uploads to `client-documents` bucket

### Step 6: Supabase Storage object is client-scoped
- **Status:** PASS (code verified)
- Path: `${user.id}/${timestamp}_${sanitizedName}`
- RLS policy: `auth.uid() = (string_to_array(name, '/'))[1]::uuid`
- Each user can only access their own folder

### Step 7: client_documents metadata row
- **Status:** NOT IMPLEMENTED
- Upload currently only writes to Storage, not to `client_documents` table
- No metadata row creation after successful upload

### Step 8: Admin can see upload metadata
- **Status:** PARTIAL
- `ClientsPanel.jsx` has `loadStorage()` that lists files from `client-documents` bucket
- Admin can see file names and sizes
- No structured metadata (status, type, review state)

### Step 9: Client receives safe status
- **Status:** PASS
- Success: green "Uploaded" text per file
- Error: red error message per file
- Uploading: spinner animation

---

## Summary

| Check | Result |
|---|---|
| Client clicks Upload Now | PASS |
| Route goes to Documents | PASS |
| Upload control is present | PASS |
| File type/size guard works | PASS |
| Dummy file upload succeeds or says setup in progress | PARTIAL |
| Supabase Storage object is client-scoped | PASS |
| client_documents metadata row created | NOT IMPLEMENTED |
| Admin can see upload metadata | PARTIAL |
| Client receives safe status | PASS |

**STATUS: Manual/placeholder only — not ready for real tester uploads.**
Upload to Storage works when Supabase is configured and user is signed in. Metadata tracking not yet implemented.
