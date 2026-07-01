# Hermes Brain Routing Rebuild

Status: implemented and covered by the repository test/build checks.

## Result

- `handleHermesMessage` is the shared route for the full Workroom and inline drawer.
- Activation levels now control source selection, memory, model use, Supabase retrieval, and approval handling.
- The surface components no longer make a second model-routing decision.
- Every pipeline response writes a bounded, redacted routing trace to `nexus-hermes-routing-trace-v1`.
- Business opportunity lists, rankings, selections, named references, and implementation plans remain available as conversation context.
- Live Supabase is claimed only when the authenticated query reports live data; auth, RLS, empty, unused, and unconfigured states remain distinct.
- Headless browser checks passed for both the inline opportunity follow-up flow and the full Workroom 30-day recommendation/trace flow. The local smoke browser had no authenticated Supabase session, and Hermes reported that state without claiming live query success.

## Incorrect Paths Repaired

- Business strategy questions no longer return section-status lists.
- Follow-ups such as “number 3,” “pick one,” and “monthly readiness subscription” resolve through memory.
- Status, cost, capability, process, and routing-trace questions use deterministic local answers with no model.
- Trade/send/publish/charge/dispute/destructive requests activate the safety gate.

## Remaining Blockers

- Live data proof requires an authenticated admin browser session with RLS-permitted table reads.
- Netlify/live verification can only complete after the pushed commit is deployed.
- The pipeline prepares approval drafts; it intentionally does not submit or execute them.
