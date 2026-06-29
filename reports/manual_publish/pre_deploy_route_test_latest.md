# Pre-Deploy Route Test

- ok: true
- admin root preserved: true
- client root preserved: true

## Routes

- `/` — HTTP 200; shell: admin_auth; obvious failure: false
- `/client` — HTTP 200; shell: client_portal; obvious failure: false
- `/client/dashboard` — HTTP 200; shell: client_portal; obvious failure: false
- `/client/credit-repair` — HTTP 200; shell: client_portal; obvious failure: false
- `/client/credit-profile-readiness` — HTTP 200; shell: client_portal; obvious failure: false
- `/client/business-profile-readiness` — HTTP 200; shell: client_portal; obvious failure: false
- `/client/business-opportunities` — HTTP 200; shell: client_portal; obvious failure: false
- `/client/funding-readiness` — HTTP 200; shell: client_portal; obvious failure: false
- `/client/documents` — HTTP 200; shell: client_portal; obvious failure: false
- `/client/messages` — HTTP 200; shell: client_portal; obvious failure: false
- `/client/settings` — HTTP 200; shell: client_portal; obvious failure: false
- `/goclear-apex-readiness.html` — HTTP 200; shell: public_landing; obvious failure: false
