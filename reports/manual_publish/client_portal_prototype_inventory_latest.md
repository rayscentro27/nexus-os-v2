# Client Portal Prototype Inventory

- ZIP: `/Users/raymonddavis/Downloads/nexus-client-portal-react.zip`
- Extracted: true
- Extracted root: `_incoming/client-portal-prototype/nexus-client-portal-react`
- Files: `package.json`, `index.html`, `README.md`, `src/main.jsx`, `src/App.jsx`, `src/styles.css`
- Dependencies: React, React DOM, Lucide React, Vite, Vite React plugin.
- Dependency conflicts: none; all runtime/UI dependencies already exist in Nexus.

## Prototype Pages

- Dashboard
- Business Opportunities
- Credit Repair
- Credit Profile Readiness
- Business Profile Readiness
- Funding Readiness
- Documents, Messages, and Settings were present as disabled navigation placeholders.

## Reusable UI

- Fixed sidebar and topbar application shell
- Premium dark glass-card visual system
- Score cards and conic progress rings
- Metric and factor cards
- Workflow steps, action lists, tables, document rows, and charts
- Assistant recommendation panel layout

## Required Adaptation

- Scope CSS under `.client-portal` to prevent collision with the admin dashboard.
- Replace tab-only navigation with `/client/*` pathname navigation.
- Complete Documents, Messages, and Settings pages.
- Replace client-facing Hermes references with Nexus Guide.
- Remove guarantee-like, result-prediction, and implied external-action language.
- Drive pages from shared demo-only portal and approved-guidance data.
