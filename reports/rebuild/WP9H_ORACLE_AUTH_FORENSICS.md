# WP9H Oracle Hermes authentication forensics

## Scope

Campaign `HG-WP9H-ORACLE-HERMES-0206-AUTH-MODEL-ROUTE-REPAIR-AND-TELEGRAM-CUTOVER-20260902-01`.
Evidence was collected from the existing Mac tunnel and the existing Oracle
container. No credential value is recorded.

| Item | Result |
|---|---|
| API protection | `API_SERVER_KEY` bearer authentication |
| API credential source | Oracle `/home/opc/.config/nexus-hermes-0206-cert/api.env`, mode 600, owner `opc:opc` |
| Oracle API credential | PRESENT on Oracle; not present on Mac |
| Mac bridge credential | ABSENT from runtime env and checked Keychain service names |
| Existing provider credential | `OPENROUTER_API_KEY` PRESENT in the Mac runtime env |
| Reuse | Oracle API key was used ephemerally for authenticated health proof; it was not persisted or copied to source |
| Tunnel | Existing loopback SSH tunnel, Mac `127.0.0.1:18642` to Oracle `127.0.0.1:8642` |

Authenticated `GET /health` returned HTTP 200 and Hermes `0.20.6`. The first
model attempt through the API used the live default profile and did not return
within the bounded 20-second client limit. No Telegram, launchd, scheduler,
or certification state was changed.

## Decision

`CREDENTIAL_REUSE_AVAILABLE=PASS_EPHEMERAL_ONLY`.

The existing Oracle API key is not an approved Mac bridge credential path. A
durable bridge needs an explicit secure injection mechanism (for example a
Keychain item or an authorized secret broker). Do not place the key in Git,
runtime reports, process arguments, or a checked-in environment file.
