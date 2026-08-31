# Nova Telegram Fanout Placement Audit

Before this repair, A/B fanout ran only after the conversational graph. `governed_object_resolution` is a terminal primary branch before that point, so updates handled there never reached Hermes shadow.

Current flow in `_process_message_inner`:

`authorization` → certification-only `_run_shadow_ab` → `governed_object_resolution` → unchanged custom primary behavior or five-stage graph → primary Telegram send.

The fanout is now before the first custom terminal branch for authorized requests. `governed_object_resolution` remains primary-only and was not removed or changed. Unauthorized requests remain outside the shadow certification scope.

Other primary terminal paths reviewed: unauthorized, governed-object, Nova-disabled, empty-response, and exception responses. The certification fanout is scheduled after authorization and before governed-object resolution; shadow remains silent.
