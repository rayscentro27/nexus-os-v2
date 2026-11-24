# GitHub hosted monitor template

Prepared for a single Nexus-owned public GitHub monitor repository. It is not active until that repository exists and these files are installed there. The scheduled job uses the standard `ubuntu-latest` runner, reads GitHub APIs only, writes compact commit/path state, and never downloads or executes a monitored repository.

Keep `sources.yaml` as the monitor's configuration projection. Nexus's local SQLite registry remains the operational source of truth; when enabling this template, generate the projection from that registry and review the diff. Do not hand-maintain a second untracked source list.

The workflow is scheduled every six hours only after it is installed in the dedicated public monitor repository. Public repository standard GitHub-hosted runner usage is currently free per GitHub's billing documentation. Keep the repo public, use only `ubuntu-latest`, and disable or set a zero-dollar stop-usage budget for any private/larger-runner usage.
