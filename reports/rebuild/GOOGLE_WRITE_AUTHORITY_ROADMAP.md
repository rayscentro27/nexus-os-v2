# Google Write Authority Roadmap

Write capability is intentionally deferred.

| Future capability | Authority target |
|---|---|
| Gmail send | approval required; governed execution |
| Gmail reply | approval required; governed execution |
| Gmail draft | draft-only until explicitly approved |
| Calendar create | approval required |
| Calendar update | approval required |
| Calendar delete | approval required |
| Invitation response | approval required |

Any future write tool must call Nexus governance internally for authorization,
tenant/privacy policy, execution, receipt, and recovery. It must not be added by
expanding this read-only server implicitly.
