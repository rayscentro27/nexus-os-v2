# Hermes Conversational Routing Gap

Generated: 2026-07-01 18:48 America/Phoenix

- General greetings and availability checks now use `casual_common` with no memory, retrieval, or model call.
- Work-openers and completed-work questions now use `process_activity_status` with local activity/report evidence.
- “Why local/fallback/no Supabase/model/memory?” questions now inspect the last non-trace routing record.
- Safety, trace, scheduling, activity, explicit-domain, and memory priority boundaries remain enforced.
- Greeting, status, capability, and trace turns preserve the active business selection and topic.
- 523/523 tests passed; the production build passed.
- Browser execution remains blocked at authenticated admin sign-in; authentication was not bypassed.
