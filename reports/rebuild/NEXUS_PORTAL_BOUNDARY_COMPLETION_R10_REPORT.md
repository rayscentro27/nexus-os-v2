# Portal Tenant and Approval Boundary Completion R10

## Result

`portal.client_beta` remains `ACTIVE`. Its current unmet criterion is exactly
`Verify tenant and approval boundaries`; no criterion was manually marked.

## Acceptance contract

The existing Nexus contract requires authenticated own-tenant access, cross-
tenant read denial, protected admin-write denial, membership isolation,
synthetic storage isolation, approval-gated behavior, and no client exposure
of service-role credentials. Static Portal safety checks are insufficient.

## Capability matrix

| Capability | System | Worker/runtime | Authorized | Real tested | Result |
|---|---|---|---|---|---|
| Repository read/write | yes | yes | yes | yes | READY |
| Node/npm/Vitest/build | yes | yes | yes | yes | READY |
| Portal safety verifier | yes | yes | yes | yes | PASS |
| Existing Supabase certification script | yes | yes | yes | not with identities | BLOCKED |
| Authenticated tenant fixtures | unavailable | unavailable | not applicable | no | HUMAN/EXTERNAL BLOCKER |

The existing script `scripts/certification/certify_live_backend.mjs` is the
canonical real RLS path. It requires `E2E_CERT_ADMIN_*` and
`E2E_PERSONA_{A,B,C,D}_*` credentials. The unattended runtime has URL, anon
key, and service-role presence, but all eight test identity variables are
absent. No credential values were printed or persisted.

## Runtime work

The normal Active Operator selected Portal through the existing service path.
The Engineering executor now binds the criterion to:

- `certify_live_backend.mjs` for authenticated tenant/RLS tests;
- `tests/goclear_readiness_internal_test_runner.test.ts` for approval-gated
  internal behavior;
- the existing Portal route test, build, and safety verifier.

The prior R9 capability preflight and real Engineering receipt remain valid:
[engineering_portal_c7639b9c1f124c1eaf2806e8f9f7df04.json](/Users/raymonddavis/nexus-os-v2/reports/runtime/engineering_receipts/engineering_portal_c7639b9c1f124c1eaf2806e8f9f7df04.json).

The new binding cannot honestly produce `TENANT_BOUNDARY_TESTING=PASS_REAL`
until the canonical test identities exist. Static approval tests and safety
verification do not prove live tenant isolation.

## Final state

PORTAL_TENANT_APPROVAL_CRITERION=NOT_VERIFIED
PORTAL_ALL_SUCCESS_CRITERIA_VERIFIED=NO
PORTAL_FINALIZATION=NOT_ELIGIBLE
PORTAL_GOAL_STATUS=ACTIVE
NORMAL_SUPERVISOR_USED=YES
CODEX_SELECTED_CHILD_ACTION=NO
PORTAL_SECURITY_PATH_GENERALIZED=YES
TRUE_RAY_BLOCKERS=Authenticated certification test identities are absent. Ray must provide or approve creation of the existing governed test identities; Nexus can then automatically resume the persisted Portal criterion.
SYSTEMATIC_OUTCOME_AUTONOMY=NOT_YET_CERTIFIED

No production deployment, customer outreach, payment, live trading, or
destructive database mutation occurred.
