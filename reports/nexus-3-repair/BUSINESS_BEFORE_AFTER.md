# Business Before / After

## Before

Business routes rendered the same shared legacy/guided wrappers before `BusinessPanel`.

## After

Business routes render `BusinessPanel` directly inside `.wc-pageHost`.

## Local Browser Evidence

Local production preview at `127.0.0.1:4177`:

- `.wc-pageHost` direct children: `wc-panel wc-panel-business`
- direct guided stacks: `0`
- Nexus 3.0 heroes: `1`
- Nexus 3.0 tab systems: `1`
- horizontal overflow: `false`
