# WP8.7 Research Memory

## Durable objects

`alpha_content`, `alpha_claims`, `alpha_research`, `alpha_discovery_queue`, `alpha_outcomes`, `alpha_source_registry`, and `alpha_theme_registry` use the existing governed append-only store. Content hashes and claim IDs provide duplicate protection; claim revisions supersede earlier verification state without erasing history.
## Currentness

Stored research is not automatically current. Time-sensitive findings must be refreshed before being presented as current truth.
