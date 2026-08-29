# Nexus SKILL.md standard

Nexus skills are Markdown contracts, not authority grants. Hermes may read a
skill only after Nexus resolves its `skill_id`, worker, model policy, and
allowlisted executor. TruthKernel and deterministic Python remain authoritative.

Required frontmatter: `name`, `version`, `owner: nexus`, `status`,
`authority_class`, `side_effect_class`, `default_profile`, `model_policy`,
`allowed_executors`, and `receipt_required`.

Required sections: Purpose, When To Use, When Not To Use, Inputs, Required
Context, Data Sources, Authority Requirements, Dependencies, Allowed Python
Executors, Model Routing, Worker / Profile, Procedure, Output Contract,
Validation, Side-Effect Validation, Receipt Requirements, Retry Policy,
Handoff Policy, Failure Modes, Escalation Rules, Security Boundaries, and
Examples.
