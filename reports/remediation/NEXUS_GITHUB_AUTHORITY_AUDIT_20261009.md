# GitHub Environment and Authority Audit

**Audit mode:** Read-only. No GitHub setting, secret, workflow, branch, webhook, runner, deployment, or artifact was changed. No workflow was triggered or rerun. Secret values were not accessed or printed.

## Repository mapping

- **OBSERVED FACT:** Canonical checkout `/Users/raymonddavis/nexus-os-v2-canonical` is on local branch `main`, with `origin` pointing to `https://github.com/rayscentro27/nexus-os-v2.git`.
- **OBSERVED FACT:** `~/nexus-os-v2` has the same origin URL, so it is a second checkout of the same GitHub repository, not a separate remote repository.
- **OBSERVED FACT:** `~/nexuslive` points to `https://github.com/rayscentro27/nexuslive.git`, a separate repository. The public GitHub repository page identifies `rayscentro27/nexus-os-v2` as public, with default branch `main` and description “Nexus Operating System.” [Repository](https://github.com/rayscentro27/nexus-os-v2)
- **OBSERVED FACT:** Local `git worktree list` also showed two additional Nexus OS v2 worktrees (`nexus-os-v2-client-polish` and `nexus-os-v2-tailwind4`) and one prunable stale worktree record. The canonical tree already had 832 changed/untracked status lines at campaign start; their status was preserved in the pre-remediation snapshot.
- **INFERENCE:** The canonical checkout is the intended source of truth for Nexus OS v2, while `nexuslive` is a separate legacy/deployment-oriented frontend repository. Production authority and deployed site mapping are not verified.

## Workflows and run history

- **OBSERVED FACT:** No `.github/workflows` files were present in the canonical checkout during this inspection. In `nexuslive`, two workflow files are present: `render-remotion-short.yml` and `render-short-video-maker.yml`.
- **OBSERVED FACT:** Both workflow files use only `workflow_dispatch`, run on GitHub-hosted Ubuntu, and declare `contents: read`. Neither has a cron schedule or push/PR trigger in the local workflow definition.
- **OBSERVED FACT:** The Remotion workflow renders an MP4 and stores it as a 14-day Actions artifact; its workflow definition says it has no repository secrets and performs no posting or scheduling. The Short Video Maker workflow consumes the GitHub Actions secret named `PEXELS_API_KEY`, calls the Pexels-backed rendering path, and uploads an MP4 artifact for 14 days. It does not declare Supabase, Netlify, Oracle, Modal, Cloudflare, Telegram, email, social, or trading credentials.
- **OBSERVED FACT:** The public `nexuslive` Actions page showed eight runs, all displayed as manually triggered. The latest visible run was June 9, 2026; its Short Video Maker job failed after 8m24s. The visible run history predates the October 8–9 Mac crashes, so no Actions run was observed during those outages. [Actions history](https://github.com/rayscentro27/nexuslive/actions) [Example run](https://github.com/rayscentro27/nexuslive/actions/runs/27177912721)
- **INFERENCE:** These workflows are manual, job-only media renderers, not autonomous Nexus business schedulers. The Pexels workflow is still an ungoverned external provider path and can consume GitHub Actions minutes and a Pexels credential when manually triggered. No workflow was triggered for this audit.
- **UNKNOWN:** Remote workflow enablement state, complete/current Actions history beyond public page rendering, repository/environment/organization secrets and variables, workflow permissions settings, required reviewers, branch protection/rulesets, deploy keys, GitHub Apps, webhooks, runner groups/self-hosted runners, packages, releases, and billing limits.

## Authentication and remote metadata limits

- **OBSERVED FACT:** The GitHub CLI is installed and local GitHub CLI auth metadata exists according to the prior audit. `gh auth status` did not return within the bounded attempt and was interrupted; it was not used to retrieve credentials. No token value was requested or printed.
- **OBSERVED FACT:** Local `.git/hooks` contains only Git sample hooks; no active hook was found. `core.hooksPath` was unset.
- **UNKNOWN:** Authenticated read-only GitHub administration APIs were unavailable in this session, so privileged metadata listed above could not be enumerated. Public pages were sufficient only for repository identity, workflow files/runs visible to the public, and basic repository visibility/default branch.

## Authority graph and classification

| Path | Trigger | Authority | Classification | Action |
|---|---|---|---|---|
| `nexus-os-v2` Actions | No local workflow files observed | Remote configuration not fully visible | `INVESTIGATE` | Confirm current workflow list and settings with read-only account access |
| `nexuslive` Remotion workflow | Manual `workflow_dispatch` | GitHub-hosted compute; artifact write; no workflow secret declared | `JOB_ONLY` | Retain only as manually approved media job; keep outside Nexus scheduler |
| `nexuslive` Short Video Maker workflow | Manual `workflow_dispatch` | GitHub-hosted compute, Pexels API key, media artifact write | `MAKE_JOB_ONLY` / `INVESTIGATE` | Do not run until its provider call, secret scope, cost envelope, and approval path are documented |
| Git hooks | Local Git operations | No active hooks | `KEEP` | None |
| Additional local worktrees | Developer-created checkouts | Local code/edit authority, no auto-executor observed | `INVESTIGATE` | Reconcile before final canonical-source declaration |

## Gate result

- `GITHUB_ENVIRONMENT_MAPPED=PARTIAL`
- `GITHUB_REPOSITORIES_MAPPED=2 remotes; canonical and secondary share nexus-os-v2; nexuslive is separate`
- `GITHUB_ACTION_WORKFLOWS=2 locally in nexuslive; none found locally in canonical`
- `GITHUB_SCHEDULED_WORKFLOWS=0 observed`
- `GITHUB_AUTONOMOUS_EXECUTION_PATHS=0 observed from local definitions and visible run list; remote admin metadata remains unknown`
- `GITHUB_DUPLICATE_SCHEDULERS=0 observed`
- `GITHUB_SECRET_LOCATIONS_MAPPED=PARTIAL; PEXELS_API_KEY workflow reference known; actual secret metadata unavailable`
- `GITHUB_SELF_HOSTED_RUNNERS=UNKNOWN`
- `GITHUB_WEBHOOKS_MAPPED=UNKNOWN`
- `GITHUB_APPS_MAPPED=UNKNOWN`
- `GITHUB_ZERO_UNKNOWN_PASS=NO`

**RECOMMENDATION:** Do not enable Nexus scheduler or dispatcher until authenticated read-only metadata confirms no hidden autonomous workflow, runner, webhook, or deployment path, and the manual Pexels job is either moved behind a governed job contract or explicitly isolated from production Nexus authority. No remote change was made.
