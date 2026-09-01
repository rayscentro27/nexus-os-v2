# Hermes MCP per-turn deduplication

The MCP server reuses successful canonical results only within an explicit turn
scope. Cross-turn volatile results are not reused. The final sequence showed
one logical capability read for A2, B2, C1, and C2; C2's scoped tool set also
prevented unrelated blocker/review/work-item reads.

The server receipt remains the source for actual execution and deduplication
metadata. No cross-turn cache was introduced.
