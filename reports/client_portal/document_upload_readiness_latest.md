# Document Upload Readiness

**Generated:** 2026-07-07

## Storage Status

- **Bucket:** `client-documents` (private)
- **Created:** Yes (migration 20260707120000 applied)
- **File size limit:** 10MB
- **Allowed types:** PDF, JPEG, PNG, HEIC, TXT, DOCX

## Storage Policies

| Policy | Action | Target | Status |
|--------|--------|--------|--------|
| client_documents_upload_own | INSERT | authenticated (own folder) | ✓ |
| client_documents_read_own | SELECT | authenticated (own files) | ✓ |
| client_documents_read_admin | SELECT | authenticated (admin) | ✓ |
| client_documents_delete_admin | DELETE | authenticated (admin) | ✓ |

## Frontend

- **Upload component:** DocumentUploadZone.tsx ✓
- **Drag-drop support:** Yes ✓
- **File validation:** Yes (type + size) ✓
- **Progress indicator:** Yes ✓
- **Error messages:** Client-safe ✓
- **Gated:** Only in live mode (not preview) ✓

## Safety

- No public document exposure ✓
- Client-scoped uploads (user_id folder) ✓
- Admin can review all docs ✓
- File type/size limits enforced ✓

## Blockers

- None. Upload is fully functional.
