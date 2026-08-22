# Private Voice Transport Repair — Phase Q-A

Status: `BLOCKED_BEFORE_EXTERNAL_CONFIGURATION`

The Phase Q local STT foundation remains intact. This repair adds only the
safe browser-transport preparation and records why the final authenticated
transport and live operator gates cannot be certified from the current
workspace.

## Audit result

`cloudflared` is installed (`2026.8.2`) and a user LaunchAgent/configuration
exists, but it belongs to an existing unrelated tunnel. Its routes are:

- `signals.goclearonline.cc` → localhost port 5000
- `nexus-api.goclearonline.cc` → localhost port 4000

No `voice.*` route, DNS record, Access application, Access audience tag, or
approved Ray-only Access policy was found. The existing tunnel process is a
Hermes gateway process, and the existing LaunchAgent is not loaded. The
voice endpoint was not attached to it because doing so without an Access
application would expose the service before authentication is configured.

Tailscale is installed but logged out. No existing authenticated admin-to-Mac
voice bridge was available. No new tunnel, public hostname, DNS record, or
paid service was created.

## Required target configuration

The remaining configuration should be completed by an account administrator
with access to the approved Cloudflare zone and identity provider:

1. Create or reuse one named tunnel route for an approved voice hostname.
2. Map only that hostname to `http://127.0.0.1:8789`.
3. Create a self-hosted Access application before enabling the route.
4. Set the policy to deny by default and allow Ray/admin identity only.
5. Enable `Protect with Access` with the application team name and audience
   tag in the tunnel origin settings.
6. Configure exact Admin Portal origins in
   `NEXUS_VOICE_ALLOWED_ORIGINS`.
7. Set `VITE_NEXUS_VOICE_ENDPOINT` to the public hostname only; no secret is
   placed in the browser bundle.

Cloudflare documents that Tunnel is outbound-only and does not require an
inbound router port. Its current origin settings support `access.required`,
`teamName`, and `audTag`; Access applications are deny-by-default. The
official references are [Tunnel connectivity](https://developers.cloudflare.com/cloudflare-one/networks/connectivity-options/),
[Access self-hosted applications](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/),
and [Protect with Access origin settings](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/origin-parameters/).

Cloudflare currently advertises a Zero Trust Free plan at $0 for small teams
and proof-of-concept use, but account eligibility and current terms must be
confirmed by Ray before configuration. No paid plan or recurring spend was
introduced in Phase Q-A.

## Endpoint hardening

The existing localhost-only voice server now has:

- an enforced `127.0.0.1` bind;
- exact-origin CORS from `NEXUS_VOICE_ALLOWED_ORIGINS`;
- credentialed browser requests without any frontend token;
- `POST` and `OPTIONS` only for the fixed voice route;
- one active transcription at a time;
- six requests per session per minute;
- existing 10 MB / 30 second limits;
- temporary audio deletion.

The Admin Portal uses `credentials: include` for the future Access session.
The prior `VITE_NEXUS_VOICE_TOKEN` pattern was removed; tunnel, Access,
local-token, HMAC, and service credentials must never be browser-visible.

## Human certification step

After the approved Access route is configured and verified, Ray must use the
actual Admin Portal microphone and intentionally press/hold the control while
saying:

> Nexus, what should I focus on today?

That intentional action is the bounded consent for the temporary recording.
The raw recording must be deleted after transcription. The browser transcript,
Hermes screen response, voice-ready response, duration, and safe metadata may
be retained for certification.

Until that step is completed, the final gates remain:

`SECURE_ADMIN_VOICE_TRANSPORT_READY=NO`

`ADMIN_PUSH_TO_TALK_READY=PARTIAL`

`PRIVATE_VOICE_STT_READY=PARTIAL`

No quick tunnel, anonymous endpoint, public Mac binding, or downloaded speech
sample is an acceptable substitute.
