# Nexus Live Backend Certification

Generated: 2026-08-03T21:50:33.412Z
Result: PASS

Total checks: 52
Passed: 52
Failed: 0
Blocked: 0

| Area | Check | Result | Evidence |
| --- | --- | --- | --- |
| Auth | nexus-cert-admin password login | PASS | user suffix 3b36e17a email ne***Z@goclear.test |
| Auth | nexus-cert-admin session restoration | PASS |  |
| Auth | nexus-cert-admin invalid-password denial | PASS |  |
| Auth | Persona A password login | PASS | user suffix 41128cd6 email pe***Z@goclear.test |
| Auth | Persona A session restoration | PASS |  |
| Auth | Persona A invalid-password denial | PASS |  |
| Auth | Persona B password login | PASS | user suffix e6488ca0 email pe***Z@goclear.test |
| Auth | Persona B session restoration | PASS |  |
| Auth | Persona B invalid-password denial | PASS |  |
| Auth | Persona C password login | PASS | user suffix cd3e2602 email pe***Z@goclear.test |
| Auth | Persona C session restoration | PASS |  |
| Auth | Persona C invalid-password denial | PASS |  |
| Auth | Persona D password login | PASS | user suffix db8aebe0 email pe***Z@goclear.test |
| Auth | Persona D session restoration | PASS |  |
| Auth | Persona D invalid-password denial | PASS |  |
| RLS | administrator can read active admin_users row | PASS |  |
| RLS | Persona A can read own tenant membership | PASS | tenant tenant-cert-persona-a |
| RLS | Persona A can read own client profile | PASS |  |
| RLS | Persona A cannot read admin-only rows | PASS |  |
| RLS | Persona A cannot insert admin_users | PASS |  |
| RLS | Persona B can read own tenant membership | PASS | tenant tenant-cert-persona-b |
| RLS | Persona B can read own client profile | PASS |  |
| RLS | Persona B cannot read admin-only rows | PASS |  |
| RLS | Persona B cannot insert admin_users | PASS |  |
| RLS | Persona C can read own tenant membership | PASS | tenant tenant-cert-persona-c |
| RLS | Persona C can read own client profile | PASS |  |
| RLS | Persona C cannot read admin-only rows | PASS |  |
| RLS | Persona C cannot insert admin_users | PASS |  |
| RLS | Persona D can read own tenant membership | PASS | tenant tenant-cert-persona-d |
| RLS | Persona D can read own client profile | PASS |  |
| RLS | Persona D cannot read admin-only rows | PASS |  |
| RLS | Persona D cannot insert admin_users | PASS |  |
| RLS | Persona A cannot read Persona B profile | PASS |  |
| RLS | Persona A cannot read Persona C profile | PASS |  |
| RLS | Persona B cannot read Persona A profile | PASS |  |
| RLS | Persona C cannot read Persona D profile | PASS |  |
| RLS | Persona D cannot read Persona A profile | PASS |  |
| RLS | unauthenticated user cannot read protected client profiles | PASS |  |
| RLS | administrator can read process registry | PASS |  |
| RLS | client cannot read process registry rows | PASS |  |
| Storage | Persona A upload synthetic file | PASS | 5e6e5840-8ce1-40f7-bf44-4d3341128cd6/certification/1785793814092-persona-a-credit-report.txt |
| Storage | Persona A read own file | PASS |  |
| Storage | Persona B cannot read Persona A file | PASS |  |
| Storage | Persona B upload synthetic file | PASS | 95708bdd-eec7-4082-b7e8-050ae6488ca0/certification/1785793814092-persona-b-bank-statement.txt |
| Storage | Persona B cannot overwrite Persona A file | PASS |  |
| Storage | duplicate upload without upsert is rejected | PASS |  |
| Storage | invalid MIME rejected | PASS |  |
| Storage | oversized file rejected | PASS |  |
| Storage | classification metadata persisted | PASS | cert-client-cert-persona-a-1785793832233-credit-report |
| Storage | classification metadata readable by owner | PASS |  |
| Storage | Persona B cannot read Persona A document metadata | PASS |  |
| Storage | administrator can read synthetic document metadata | PASS |  |

No passwords, tokens, keys, or raw client data are included.
