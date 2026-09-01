# Direct export proof

Standalone native SDK test: trace `780fa7d4cefdf09536ca45ea07e32b9f`; flush completed; remote lookup succeeded after five seconds.

Standalone OTel adapter test: trace `01a4c81754aaac743e59356f43180bb4`; flush completed; remote lookup succeeded after five seconds.

The selected export path is the existing Langfuse 4.14.2 SDK-backed OTel adapter, with valid trace-context propagation. Both direct paths are fail-open and introduce no model call.
