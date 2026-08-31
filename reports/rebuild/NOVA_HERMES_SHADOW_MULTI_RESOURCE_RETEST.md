# Hermes Shadow Multi-Resource Retest

The Nexus + outside-information prompt was rerun after the repair. Nexus reads
were real and returned to Hermes. Public web was available through the shadow
tool and fell back to Bing HTML after SearXNG/DuckDuckGo failure. Because the
returned Bing result set was weak and page retrieval was not automatically
selected in that turn, complete multi-source synthesis is **PARTIAL**, not a
cutover pass.

The implementation supports multiple native calls in one reasoning context;
the remaining gap is model selection of retrieval after low-quality search
results, not a new architecture layer.

