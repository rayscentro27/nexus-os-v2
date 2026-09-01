# WP8.11C After-hours Readiness

The existing WP8.11B runner remains internal-only and bounded. Because the
canonical model route did not complete an inference probe, model-powered Core
after-hours readiness is not certified in this checkpoint.

`CREATIVE_CORE_AFTER_HOURS_READY=NO`
`CREATIVE_DEGRADED_MODE_TRUTHFUL=PASS`

When the model route is repaired, the exact proposed invocation is:

```text
PYTHONPATH=scripts python3 -m nexus_agent_platform.creative.after_hours_runner \
  --max-briefs 2 --max-territories-per-brief 4 --max-landing-pages 1 \
  --max-images 4 --max-video-renders 1 --max-avatar-renders 1 \
  --max-ai-calls 12 --max-critique-cycles 2 --max-revisions 1 \
  --max-runtime-seconds 1800 --max-api-cost-usd 0 \
  --authority INTERNAL_ONLY --no-publish --no-ad-spend \
  --no-social-post --no-outreach --no-subscriptions
```

The intended degraded mode may still use existing deterministic landing-page
builds, screenshots, channel packages, FFmpeg composition, and truthful
blocker labels for image generation, voice, and avatar.

