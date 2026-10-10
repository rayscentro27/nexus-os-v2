# Nexus Pre-Remediation Snapshot

Captured: Fri Oct  9 10:35:45 MST 2026

## Scope and preservation

- OBSERVED FACT: Read-only baseline captured before campaign mutations. No secret values or file contents from credential stores are included.
- OBSERVED FACT: The canonical checkout already had a large set of modified and untracked files at campaign start. The complete `git status --short --branch` was preserved in the JSON snapshot. Do not reset or overwrite those changes.
- OBSERVED FACT: Launchd plist metadata, Hermes/OpenClaw schedule metadata, credential path ownership/mode/mtime/size, and previous audit deployment limits are recorded in the JSON snapshot. Launchd argument values are redacted to avoid preserving a possible credential embedded in a command argument.

## Rollback map

### credential permission hardening for three identified mode-0644 files
- Before: owner/mode/mtime/consumer references captured before chmod
- Intended after: 0600 if current owner and use validate
- Rollback: restore captured mode only if service dependency proves required; never restore world access without safer service repair

### canonical Python runtime and launch configuration
- Before: secondary checkout venv referenced by launch definitions
- Intended after: canonical-owned interpreter/environment after dependency verification
- Rollback: restore saved plist/runtime paths

### provider/query/eligibility code changes
- Before: working tree already contains extensive pre-existing modifications; full git status preserved
- Intended after: only narrow reviewed diffs after auditing current local changes
- Rollback: reverse only this campaign’s patch; preserve pre-existing work

### staged runtime activation
- Before: safe mode; scheduler/dispatcher off
- Intended after: only after all gates and explicit clean checks; return off after stage
- Rollback: disable/unload only newly activated scheduler/dispatcher; no old runtime restart
