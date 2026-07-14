# Parser Environment Alignment

The safe diagnostic confirms Python 3.14.5, OpenSSL 3.6.2, an installed certifi CA bundle, and certificate verification enabled. `SUPABASE_URL` and `VITE_SUPABASE_URL` both resolve to project ref `iqjwgpnujbeoyaeuwehj`. The server-side service role and browser anon key are present in their correct environments; no key values were printed.

The Mac worker and local frontend configuration use the same Supabase project, and the live row proves the worker reaches that project. The operating-system split was not the parser-count cause. The worker now constructs an explicit verified SSL context from `certifi.where()`, removing the need for per-session certificate exports without disabling TLS verification.

Independent scraping of the currently published `goclearonline.cc` JavaScript bundle was blocked by an HTTP 403 response, so the deployed bundle's embedded project ref was not re-proven from public assets in this sprint. Windows should confirm the project host in DevTools Network as described in the manual test steps.

The linked remote migration list also identifies `iqjwgpnujbeoyaeuwehj`; migration `20260714120000` was applied successfully.
