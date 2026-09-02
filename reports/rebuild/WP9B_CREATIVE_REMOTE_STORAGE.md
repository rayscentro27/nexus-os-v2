# WP9B remote storage

The existing `media_library.py` provides logical object keys, master/review/
thumbnail derivatives, checksums/metadata, and a private Supabase Storage
adapter using service credentials only in operator-side sync. Browser review
uses review references, not local filesystem paths. WP9B retains that contract
and records `CREATIVE_LOCAL_PATH_REQUIRED_FOR_REVIEW=NO`.

No new bucket was created and no remote upload was attempted in this bounded
upgrade. Local private-object storage is proven; Supabase remote storage remains
available through the existing adapter when configured.
