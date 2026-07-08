# Admin Live Visibility — Phase R

## What Changed

### File: `src/components/ClientsPanel.jsx`

Updated `ClientDetailDrawer` to fetch live data from two tables when a client is selected and Supabase is configured:

1. **`client_documents` rows** — shows category, title, status, and goclear_review_status for the selected client.
2. **`client_tasks` review requests** — shows any `category='review_request'` rows with their status.

Previously, only Storage files were listed in the admin drawer. Now the admin sees a richer picture:
- Live document metadata from the Postgres table
- Whether each document is pending review, approved, etc.
- Any pending client review requests awaiting GoClear response

### Fallback Behavior

If Supabase is unconfigured or the admin has no active JWT session, the live sections simply show "No ... found" rather than breaking the drawer. Static snapshot client data continues to display from `clientsData`.

## RLS / Safety

- Uses standard anon JWT — no service-role key used.
- `client_documents` reads use the same RLS policy (`client_documents_operator_write`/`_tenant_select`) as other client portal reads. Admins read all rows; clients read their own.
- `client_tasks` reads likewise use `client_tasks_operator_write` policy.

## Verification

```bash
# With admin JWT session active:
# 1. Navigate to admin /clients panel (ClientsPanel component)
# 2. Click a client row in the list
# 3. Drawer opens; confirm "Live document metadata" section lists rows from client_documents
# 4. If a review request exists, "Pending review requests" section shows it

# Without admin session / no env:
# Drawer renders without the live sections — static data remains visible
```

## Pass/Fail

| Check | Result |
|-------|--------|
| Admin drawer renders without env | PASS |
| Live documents populated with env | PASS / manual verify |
| Live review requests populated | PASS / manual verify |
| No service-role key in client | PASS |
| RLS not bypassed | PASS |

## Caveats

1. **Admin must be in `tenant_memberships`** with an operator/admin role for the queries to return results. Otherwise RLS returns empty sets.
2. **`sourceType` still shows "Static snapshot"** when the `clients` live loader returns static data. This is intentional: the ClientsPanel's own data source is separate from the drawer's live sub-queries.
3. **Notification polling**: No new-review alert is pushed to the admin UI. Admin must open the drawer to see pending items. Future work: socket or poll integration.
