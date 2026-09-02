# WP8.14D npm build certification

The canonical chain is `npm run tailwind:v2 && tsc --noEmit && vite build`. The prior slow behavior was a long Tailwind/TypeScript/Vite build phase, not a watch flag or postbuild command. A bounded canonical `npm run build` completed: Tailwind rebuilt in 1.59s, TypeScript completed, Vite transformed 2129 modules and built in 17.20s. No weaker replacement was introduced. A 60-second certification alarm remains the external harness guard.
