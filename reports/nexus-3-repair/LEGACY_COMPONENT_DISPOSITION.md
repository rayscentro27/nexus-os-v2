# Legacy Component Disposition

| Component | Previous Use | Disposition |
|---|---|---|
| `FundingReadinessHeader` | Unconditional wrapper before every route panel | Removed from `WorldClassClientPortal` render tree |
| `ClientRevenueServiceCard` | Unconditional purchased-service card before every route panel | Removed from `WorldClassClientPortal` render tree |
| `GuidedClientJourneySurface` | Unconditional guided stage/checklist wrapper before every route panel | Removed from `WorldClassClientPortal` render tree |
| `CreditPanel` | Approved Nexus 3.0 Credit workspace, previously appended after legacy blocks | Preserved and promoted to direct route owner |
| `BusinessPanel` | Approved Nexus 3.0 Business workspace, previously appended after legacy blocks | Preserved and promoted to direct route owner |
| `ResourcesPanel` | Used for both Resources and Recommendations | Preserved for Resources only |
| `RecommendationsPanel` | Missing dedicated route panel | Added as dedicated Nexus 3.0 Recommendations workspace |

No backend services, Supabase adapters, storage upload components, readiness calculations, or payment processing functions were removed.
