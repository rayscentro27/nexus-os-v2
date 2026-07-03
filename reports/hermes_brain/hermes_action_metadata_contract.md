# Hermes Action Metadata Contract

Hermes responses may return `uiActions` separately from spoken text. Allowed action types are `open_report`, `open_approval`, `view_source`, `open_access_map`, `draft_ray_review`, and `prepare_specialist_handoff`.

Every action includes a title, label, action type, source, and an internal safe route when navigation is available. Report paths, approval IDs, and task-request IDs are metadata only and are not read aloud in CEO mode.

The UI allowlists action types and internal hash routes. Actions must never send, publish, charge, schedule, trade, deploy, delete, approve, reject, or mutate production state. `open_approval` opens Ray Review only. Draft actions are conversation-only unless a separately approved saved-draft flow is invoked.

