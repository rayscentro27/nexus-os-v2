# Nexus 3.0 Architecture

Nexus 3.0 uses the existing authenticated React/Vite client portal as the production workflow foundation and applies the approved Credit and Business design system to it.

Implemented source:
- Active client portal: src/pages/client/WorldClassClientPortal.jsx
- Preview portal: src/pages/client/ClientPreviewPage.jsx
- Shared client route registry: src/components/client/ClientPortalShell.jsx
- Guided readiness surface: src/components/client/GuidedClientJourneySurface.jsx
- Styling: src/styles/world-class-client-portal.css

Preserved systems:
- Supabase Auth and client context resolution
- Tenant-aware data loading
- Central document upload panels
- Credit repair case engine and Bureau Letter Builder behavior
- Readiness model
- Review request flow
- Stripe test-mode revenue card and fail-closed live configuration

No new frontend framework, public storage, service-role frontend access, or live Stripe configuration was introduced.
