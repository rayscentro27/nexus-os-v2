# WP8.13 GoClear Backend Reuse Audit

The bounded client pattern reuses `ClientV2Gate`, `resolveClientContextForCurrentUser`, `useV2ClientData`, existing Supabase auth/RLS, `client_documents`, private `client-documents` storage, readiness adapters, Hermes context, and `InlineDocumentUpload`. The old client portal remains untouched. No duplicate client state or production account was created.

Observed live synthetic state is rendered with the explicit `Live data` marker. Persona A upload proof wrote a real `client_documents` row and private storage object through the existing workflow.
