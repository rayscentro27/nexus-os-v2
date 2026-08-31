# Nova Resource Awareness Audit

The model context includes these resource descriptors: `MODEL_GENERAL_KNOWLEDGE`, `PUBLIC_WEB`, `PUBLIC_WEBSITE`, `COMPANY_DATABASE`, `NEXUS_OS`, `NEXUS_LIVE_TRUTH`, `ALPHA_RESEARCH`, `GOOGLE_WORKSPACE_READ`, and `REPORT_ARCHIVE`.

The model sees each resource’s description, read capability, availability class, freshness, provenance class, cost class, privacy scope, retrieval method, searchability, comparability, and authority requirement. It requests executable resources through the bounded `nova_capability_request` envelope.

`DOES_NOVA_KNOW_PUBLIC_WEB_EXISTS=YES`  
`DOES_NOVA_KNOW_NEXUS_READ_EXISTS=YES`  
`DOES_NOVA_KNOW_ALPHA_EXISTS=YES`  
`DOES_NOVA_KNOW_GOOGLE_READ_EXISTS=YES`

A generic Resource X can be added through the resource catalog without changing the SOUL or creating a router. The current implementation supports generic discovery as metadata; actual model use still requires a matching executable capability alias.
