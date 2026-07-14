# Business Profile Readiness Engine

`businessFundingReadiness.ts` evaluates canonical client profile fields and uploaded document names: formation, entity type, registration, EIN status (never the number), address/contact consistency, industry/NAICS, time in business, revenue range, banking, ownership, licenses, and documents.

It returns completeness, data sufficiency, Tier 1/Tier 2 Business Profile statuses, missing requirements, document requests, and real portal routes for completing a field, uploading a document, reviewing guidance/resources, or requesting GoClear help. Allowed statuses are `ready_to_review`, `almost_ready`, `action_needed`, and `insufficient_information`.
