# WP8.14C Build harness

`package.json` chains `npm run tailwind:v2 && tsc --noEmit && vite build`. A bounded invocation of the first Tailwind command exceeded 20 seconds and a 120-second probe also did not complete in the available tool window. Direct Vite had passed in the prior campaign, but that is not canonical npm-build proof. Root cause is bounded to the Tailwind CLI/content-scan stage; no shortcut build replacement was made.
