# Nova Hermes-Native Shadow Runtime

The shadow is development-only. `NOVA_HERMES_NATIVE_SHADOW=true` enables it;
`NOVA_HERMES_NATIVE_PRIMARY` must remain false. The live Telegram worker is not
imported, restarted, or changed by this path.

## Responsibility split

- Nova retains the existing SOUL, business-partner identity, context, judgment,
  recommendations, and challenge behavior.
- Hermes Agent 0.20.6 supplies generic model invocation, native provider tool
  calls, tool dispatch, tool-result continuation, and bounded delegation.
- Nexus retains TruthKernel, governed reads, authority, approvals, receipts,
  privacy, cost controls, and consequential execution.
- Alpha retains durable research and artifact lifecycle.

The shadow registers only bounded `nexus_read_shadow` and
`alpha_challenge_shadow` adapters. No mutation, arbitrary SQL, Google write, or
primary cutover is exposed.

## Expected flow

```text
prompt → Hermes AIAgent with Nova SOUL
       → native tool call when selected
       → bounded adapter / existing provider
       → native tool result continuation
       → Nova synthesis
```

