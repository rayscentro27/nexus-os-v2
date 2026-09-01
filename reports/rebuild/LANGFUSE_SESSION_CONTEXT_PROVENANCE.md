# Langfuse session-context provenance

Only bounded metadata is recorded: session/turn counts, prior tool-result and
volatile-claim counts, profile hash, available resource classes, and guidance
presence. Prompts are not uploaded as full context and chain-of-thought is
never captured.
