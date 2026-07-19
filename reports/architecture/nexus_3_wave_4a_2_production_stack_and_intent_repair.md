# Nexus OS 3.0 Wave 4A.2 — Production Stack and Intent Repair

Generated: 2026-07-19

## 1. Starting checkpoint

- Branch: `main`
- Starting commit: `e0d58c99c3138115d5ab29110ef29ccf4a083f87`
- Expected message: `repair live hermes workroom runtime and context integration`
- Production route under repair: `https://goclearonline.cc/admin#hermes`
- Pre-repair live bundle observed: `index-8LVSQB-o.js`

## 2. Worktree safety

The worktree contained unrelated dirty entries before this repair. Unrelated Alpha, Telegram, trading, runtime, cache, report, credential, customer-data, and GoClear work was not staged or reverted.

No destructive worktree commands were used.

## 3. Live production reproduction

Ray reported the live authenticated Hermes CEO Advisor Workroom still displayed:

```text
Hermes Workroom hit a local rendering error.
Error: n is not a function
```

Clean authenticated Playwright sessions against the existing live site did not reproduce the crash, which indicated browser-specific runtime behavior, stale/legacy state, or a production-only effect lifecycle. The production bundle was downloaded and inspected at the reported stack offsets.

## 4. Exact original symbol behind `n`

- Minified symbol: `n`
- Production stack area: React commit/effect lifecycle around `index-8LVSQB-o.js:40:24094`
- Minified operation: React assigning and later invoking a hook effect cleanup
- Original source symbol: return value of `end.current?.scrollIntoView({ behavior: 'smooth' })`
- Source file: `src/components/HermesChatPanel.jsx`
- Source line: 30 before repair

## 5. Source-map method

Public source maps were not available at `https://goclearonline.cc/assets/index-8LVSQB-o.js.map`, which returned the SPA HTML fallback. That is safer for production.

The mapping was performed by local bundle inspection:

- The reported offsets resolved to React effect cleanup code.
- The bundle contained the compiled Workroom effect:

```text
x.useEffect(()=>{var b;return(b=m.current)==null?void 0:b.scrollIntoView({behavior:"smooth"})},[c])
```

- That maps to the Workroom source effect:

```jsx
useEffect(() => end.current?.scrollIntoView({ behavior: 'smooth' }), [messages]);
```

## 6. Render-path root cause

The Workroom scroll effect used a concise arrow and returned the result of `scrollIntoView`.

React effects may return only:

- `undefined`; or
- a cleanup function.

If a production browser, extension, or polyfill returns a truthy non-function value from `scrollIntoView`, React stores that value as the cleanup and later calls it during effect cleanup. That produces the minified production error:

```text
TypeError: n is not a function
```

The repair changes the effect to a block body and never returns the scroll result.

## 7. Legacy persistence audit

Workroom history is localStorage-backed and previously allowed legacy array records. The repair adds schema versioning:

```text
nexus_hermes_chat_history
  schemaVersion: 2
  messages: StoredMsg[]
```

Legacy arrays are migrated on load. Stored Hermes responses are normalized through the Workroom response contract. Unknown action types and callback-shaped action data are dropped.

## 8. Message-schema migration

Added:

- `CHAT_SCHEMA_VERSION = 2`
- legacy array detection;
- envelope migration;
- bounded message normalization;
- JSON round-trip sanitization;
- sensitive text filtering before storage.

## 9. Callback rehydration

Workroom actions remain serializable descriptors only:

```text
id
type
label
enabled
requiresApproval
payload
```

No JavaScript function, closure, React event, or callback is persisted or read back from storage. UI handlers are reattached from code through `HermesMessageBubble`.

## 10. Stale bundle/cache audit

Pre-repair production HTML referenced:

```text
/assets/index-8LVSQB-o.js
```

Local production build after this repair generated:

```text
dist/assets/index-DzToWJIG.js
```

The app now exposes safe runtime build metadata at:

```text
window.__NEXUS_BUILD_METADATA__
```

Live deployed commit verification remains required after push.

## 11. Executive-intent architecture

The previous classifier overgeneralized broad Executive questions into a single priority intent. Wave 4A.2 adds distinct intents:

- `executive_priority`
- `executive_risk`
- `revenue_action`
- `followup_rationale`
- `followup_feasibility`
- `followup_blockers`
- `followup_deep_dive`

## 12. Context segmentation

The Hermes operating context now separates:

- priorities;
- risks;
- approvals;
- revenue actions;
- blockers;
- system health;
- opportunities;
- unknowns.

Priority, risk, and revenue responses no longer read from one undifferentiated priority array.

## 13. Advisory-memory changes

Recommendations now carry structured fields:

- rationale;
- feasibility;
- risks;
- blockers;
- dependencies;
- next step;
- evidence IDs.

Follow-up handlers read the field matching the requested semantic relationship.

## 14. Response differentiation

Response strategy IDs now include:

- `executive_priority_response`
- `executive_risk_response`
- `revenue_action_response`
- `followup_rationale_response`
- `followup_feasibility_response`
- `followup_blockers_response`
- `followup_deep_dive_response`

Tests assert strategy IDs, required concepts, forbidden concepts, and similarity thresholds.

## 15. Grammar cleanup

Follow-up templates were rewritten to avoid broken joined fragments, duplicate punctuation, and implementation-centric language such as `Wave 4A corpus`.

## 16. Internal-language cleanup

Normal Hermes responses no longer mention:

- Wave 4A corpus;
- router files;
- source files;
- implementation waves;
- fixture names.

Those details remain available only in engineering reports.

## 17. Local production tests

Passed:

- `npm run typecheck`
- `npm run build`
- `npx vitest run tests/hermes_live_workroom_contract.test.ts tests/hermes_production_intent_differentiation.test.ts tests/hermes_conversation_engine.test.ts tests/hermes_conversation_certification.test.ts`
- `npm test -- --reporter=dot`
- `python3 scripts/checks/certify_authenticated_rls.py`
- local production Playwright: `tests/e2e/hermes-production-intent-certification.spec.ts` 7/7
- local production Playwright: `tests/e2e/hermes-live-workroom-certification.spec.ts` 7/7

## 18. Live production tests

Live production post-deploy testing passed against https://goclearonline.cc with bundle index-CaZ5nSrF.js.

Required post-deploy checks:

- deployed commit matches pushed commit;
- production bundle no longer `index-8LVSQB-o.js`;
- zero page errors;
- zero console errors;
- no refresh required;
- priority/risk/revenue response differentiation;
- follow-up rationale/feasibility/blocker differentiation.

## 19. Deployment verification

Pre-push state:

- Expected starting commit: `e0d58c99c3138115d5ab29110ef29ccf4a083f87`
- New commit: dc8153aa3b20d3cc0cb3e29ec341285e88caa21f
- Deployed commit: dc8153aa3b20d3cc0cb3e29ec341285e88caa21f
- Netlify token in shell: unavailable

## 20. Security results

Preserved:

- RLS 45/45;
- admin route guarding;
- client denial for Executive Workroom;
- Alpha Supabase prohibition;
- Stripe test mode;
- live trading block;
- no external memory/framework installation;
- no credential values in reports.

## 21. Known limitations

Live production certification passed against `https://goclearonline.cc/admin#hermes` after deployment.

## 22. Readiness decision

Hermes Workroom is no longer the blocker for Department Operations. Department Operations may proceed only under the existing Capability OS, approval, Stripe test-mode, and live-trading policy boundaries.
