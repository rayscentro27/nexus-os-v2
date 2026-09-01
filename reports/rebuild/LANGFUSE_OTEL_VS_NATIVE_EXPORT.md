# Native versus OTel export

`DIRECT_LANGFUSE_NATIVE_SDK=PASS`: trace `780fa7d4cefdf09536ca45ea07e32b9f` was found remotely.

`DIRECT_LANGFUSE_OTEL_EXPORTER=PASS`: trace `01a4c81754aaac743e59356f43180bb4` was found remotely.

The minimal production choice remains `LANGFUSE_OTEL` through `OtelAdapter`, because the current runtime already owns that abstraction and it preserves fail-open behavior and metadata redaction. The adapter now forwards valid caller trace context.
