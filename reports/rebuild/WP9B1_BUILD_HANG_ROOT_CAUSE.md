# WP9B1 build root cause

The canonical chain is `npm run tailwind:v2 && tsc --noEmit && vite build`.
Bounded process inspection showed Tailwind emitted `Done`, TypeScript advanced,
and Vite then completed its 2,129-module production build. The earlier reports
called this a hang because the observation command expired while descendant
processes remained visible; there was no post-build hook or watcher in
`vite.config.ts`. A fresh canonical run exited 0 in about 66 seconds.

Result: `CANONICAL_NPM_BUILD=PASS_EXIT_0`. No build-script redesign was needed.
