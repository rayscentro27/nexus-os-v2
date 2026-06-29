# Live Route Verification

- ok: true
- latest implementation commit: `6468b951ca4c284c568d62ff478a5edab8365a95`
- admin root operational: true
- client portal operational: true
- public landing operational: true

## Routes

- `/` — HTTP 200; shell: admin_auth; obvious failure: false; page errors: 0
- `/client` — HTTP 200; shell: client_portal; obvious failure: false; page errors: 0
- `/client/dashboard` — HTTP 200; shell: client_portal; obvious failure: false; page errors: 0
- `/client/credit-repair` — HTTP 200; shell: client_portal; obvious failure: false; page errors: 0
- `/client/credit-profile-readiness` — HTTP 200; shell: client_portal; obvious failure: false; page errors: 0
- `/client/business-profile-readiness` — HTTP 200; shell: client_portal; obvious failure: false; page errors: 0
- `/client/business-opportunities` — HTTP 200; shell: client_portal; obvious failure: false; page errors: 0
- `/client/funding-readiness` — HTTP 200; shell: client_portal; obvious failure: false; page errors: 0
- `/client/documents` — HTTP 200; shell: client_portal; obvious failure: false; page errors: 0
- `/client/messages` — HTTP 200; shell: client_portal; obvious failure: false; page errors: 0
- `/client/settings` — HTTP 200; shell: client_portal; obvious failure: false; page errors: 0
- `/goclear-apex-readiness.html` — HTTP 200; shell: public_landing; obvious failure: false; page errors: 0
