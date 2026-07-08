# Live Status Label Runtime Hotfix — Phase R2B

## Problem

The live site was blank on `/client/documents` with the following console error:

```
ReferenceError: liveStatusLabel is not defined
```

`src/components/client/ClientPortalShell.jsx` references `liveStatusLabel` on lines 74 and 76 inside `ClientSidebar`, but the variable was only defined later inside `ClientPortalShell` (line 273), which is a different component scope. Because `ClientSidebar` rendered before the parent could pass the value down, the page crashed at runtime.

## Root Cause

Scope mismatch: `liveStatusLabel` was defined in `ClientPortalShell` but consumed in `ClientSidebar` without being passed as a prop. This was introduced in Phase R2 when adding `PortalLiveStatusContext` and the dynamic status label.

## File Changed

| File | Change |
|------|--------|
| `src/components/client/ClientPortalShell.jsx` | `ClientSidebar` now consumes `PortalLiveStatusContext` via `usePortalLiveStatus()` and defines its own local `liveStatusLabel`. Removed reliance on parent-scoped variable. |

## Fix Details

Inside `ClientSidebar`:

```js
const { status: liveStatus = 'idle' } = usePortalLiveStatus()
const liveStatusLabel = liveStatus === 'connected'
  ? 'Live data connected'
  : liveStatus === 'loading'
    ? 'Live data pending'
    : 'Demo/fallback data'
```

The badge now safely derives its label from the same context that `ClientPortalShell` updates, without depending on a parent variable.

## Expected Result

- No `ReferenceError`
- `/client/documents` renders normally
- Sidebar badge shows one of:
  - `Live data connected`
  - `Live data pending`
  - `Demo/fallback data`

## Verification

```bash
npm run build
npx tsc --noEmit
python3 scripts/checks/check_client_portal_actions.py
```

Manual:
1. Hard refresh `/client/documents`
2. Confirm page renders
3. Confirm sidebar footer badge renders without console errors
