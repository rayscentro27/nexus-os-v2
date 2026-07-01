# CLI Tool Registry Latest

**Generated:** 2026-07-01T19:45:00Z
**Data Sources:** nexus_cli_inventory, nexus_operations_status

---

## Summary

| Metric | Value |
|--------|-------|
| Total Tools | 11 |
| Installed | 11 |
| Authenticated | 0 |
| Proof Level | installed_only |

**Critical:** Tool availability does not imply authentication or authorization.

---

## Tool Registry

### git
- **Version:** git version 2.53.0
- **Status:** Installed
- **Safe Commands:** `git status`, `git log`, `git diff`, `git show`, `git branch`, `git remote -v`
- **Approval Required:** `git push`, `git commit`, `git add`, `git merge`, `git rebase`
- **Blocked:** `git push --force`

### node
- **Version:** v22.22.3
- **Status:** Installed
- **Safe Commands:** `node --version`
- **Approval Required:** `node script.js`

### npm
- **Version:** 10.9.8
- **Status:** Installed
- **Safe Commands:** `npm --version`, `npm list`, `npm outdated`, `npm ls`
- **Approval Required:** `npm install`, `npm publish`, `npm run`
- **Blocked:** `npm publish --access public`

### python3
- **Version:** Python 3.14.5
- **Status:** Installed
- **Safe Commands:** `python3 --version`
- **Approval Required:** `python3 script.py`

### supabase
- **Version:** unavailable (TimeoutExpired)
- **Status:** Installed
- **Safe Commands:** `supabase --version`, `supabase projects list`
- **Approval Required:** `supabase db push`, `supabase functions deploy`
- **Blocked:** `supabase db push --force`

### netlify
- **Version:** unavailable (TimeoutExpired)
- **Status:** Installed
- **Safe Commands:** `netlify --version`, `netlify status`, `netlify sites:list`
- **Approval Required:** `netlify deploy`, `netlify build`
- **Blocked:** `netlify deploy --prod`

### gh (GitHub CLI)
- **Version:** unavailable (TimeoutExpired)
- **Status:** Installed
- **Safe Commands:** `gh --version`, `gh auth status`, `gh repo list`
- **Approval Required:** `gh pr create`, `gh issue create`
- **Blocked:** `gh repo delete`

### ollama
- **Version:** ollama version is 0.20.5
- **Status:** Installed
- **Safe Commands:** `ollama --version`, `ollama list`, `ollama ps`
- **Approval Required:** `ollama pull`, `ollama run`
- **Blocked:** `ollama rm`

### opencode
- **Version:** unavailable (TimeoutExpired)
- **Status:** Installed
- **Safe Commands:** `opencode --version`
- **Approval Required:** `opencode run`

### codex
- **Version:** codex-cli 0.142.4
- **Status:** Installed
- **Safe Commands:** `codex --version`
- **Approval Required:** `codex run`

### playwright
- **Version:** package_present
- **Status:** Installed
- **Safe Commands:** `npx playwright --version`
- **Approval Required:** `npx playwright test`
- **Blocked:** `npx playwright install --with-deps`

---

## Critical Note

Tool availability does not imply authentication or authorization. Use only safe read-only commands unless explicitly approved.
