# Nova Runtime Capability Telemetry

The existing Telegram receipt boundary now records a secret-free `capability_telemetry` object when a capability result is present.

Fields:

`timestamp`, `session_id`, `telegram_update_id`, `capability`, `requested_by_model`, `boundary_validation`, `provider`, `execution_attempted`, `execution_status`, `failure_reason`, `fallback_selected`, `result_returned_to_model`, `final_response_id`, `capability_truth_called`, `capability_truth_result`, `capability_truth_source`, `capability_truth_freshness`, and `model_received`.

The telemetry is derived from existing graph metadata and does not add a brain layer, router, provider, or authority. Sensitive prompt contents, tokens, OAuth values, message bodies, and credentials are excluded.

For a capability-status request, `capability_truth_called=true` is emitted only when the live capability result identifies `get_live_capability_status` or its status alias. Absence of this object remains an explicit “not invoked/not proven” signal.
