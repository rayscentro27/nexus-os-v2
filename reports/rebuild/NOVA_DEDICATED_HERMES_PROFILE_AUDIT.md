# Nova dedicated Hermes profile audit

Campaign: HG-WP6.5-NOVA-DEDICATED-HERMES-PROFILE-AND-CONTEXT-BOUNDARY-20260831-01

Hermes supports isolated `HERMES_HOME` directories and named profiles under
`~/.hermes/profiles/<name>`. Nova uses the safer repository-owned,
per-invocation `HERMES_HOME` override so the global profile is never changed.
The active worker passes this path into the Hermes subprocess.

Supported controls verified in Hermes commit `cea87d9139`: `HERMES_HOME`,
`skip_context_files`, `load_soul_identity`, and `skip_memory`. Nova uses the
dedicated home plus `skip_memory=True`; global SOUL, memory, and context are
therefore excluded. The global operator profile remains untouched.

Profile selection is per invocation through the child environment. SOUL and
memory override are supported by the HERMES_HOME boundary. No global
`active_profile` switch is used.
