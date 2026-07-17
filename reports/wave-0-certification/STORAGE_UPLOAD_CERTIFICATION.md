# Storage Upload Certification

Date: 2026-07-17

## Existing Synthetic Seed Check

Commands:

```bash
python3 scripts/testers/seed_authenticated_credit_certification.py --persona a
python3 scripts/testers/seed_authenticated_credit_certification.py --persona a --follow-up
```

Result:

- Both commands exited 0.
- Both reused existing synthetic Persona A records.
- Duplicate/reuse behavior was confirmed for the established synthetic document titles.

## Authenticated Upload Probe

Method:

- Persona A signed in through the anon Supabase client.
- A synthetic PDF fixture was uploaded to private bucket `client-documents`.
- Metadata was inserted into `client_documents` using the client metadata contract:
  - `client_visible=true`
  - `approval_required=true`
  - `source=client_portal_upload`
  - exact Persona A tenant/client scope.
- Duplicate upload to the same object path was attempted and rejected.
- Persona B signed in through anon client and attempted to read the new metadata row.
- No signed URL was created.

Result:

```json
{
  "ok": true,
  "persona": "A",
  "bucket": "client-documents",
  "metadata_created": true,
  "duplicate_rejected": true,
  "cross_tenant_metadata_denied": true,
  "object_path_scope": "persona_user_prefix",
  "signed_url_created": false
}
```

Exit code: 0.
Status: PASS.

## Initial Failed Probe And Cleanup

An initial probe used `approval_required=false`, which violates the client insert RLS policy. The object from that failed metadata probe was removed.

Cleanup result:

```json
{
  "ok": true,
  "removed_probe_objects": 1,
  "signed_url_created": false
}
```

## Limits

- Unsupported file behavior was validated statically through component type allowlists, not by browser upload.
- The passing upload probe used a synthetic fixture and direct Supabase client code rather than the browser file picker.

Storage Gate: PASS.
