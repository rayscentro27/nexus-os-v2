# WP9B1 Creative tooling inventory

| TOOL | PRESENT | VERSION | AUTHORIZED | EXECUTION_LOCATION | ROLE | OVERLAP | COST_CLASS | RECOMMENDATION |
|---|---|---|---|---|---|---|---|---|
| Playwright | INSTALLED | 1.61.1 / Python API | YES internal | control plane | screenshots/browser QA | existing | zero local | use API lifecycle |
| FFmpeg/ffprobe | INSTALLED | system | YES internal | control plane | video/poster/render | existing | zero local | retain |
| Pillow | INSTALLED | 12.1.1 | YES internal | control plane | image derivatives | existing | zero local | retain |
| ImageMagick | NOT_PRESENT | — | — | — | image ops | Pillow covers need | zero | no install |
| Sharp | NOT_PRESENT | — | — | — | Node image ops | Pillow covers need | zero | no install |
| axe-core | NOT_PRESENT | — | — | — | automated accessibility | browser checks exist | — | add only if release need |
| Remotion | NOT_PRESENT | — | — | — | motion rendering | FFmpeg exists | — | no install |
| Figma MCP/skills | NOT_FOUND | — | UNKNOWN | — | design context | none proven | unknown | do not activate |
| Canva MCP/skills | NOT_FOUND | — | UNKNOWN | — | design editing | none proven | unknown | do not activate |
| ComfyUI | NOT_PRESENT | — | — | — | image generation | none | unknown | adapter only |
| Modal | NOT_PRESENT | — | AUTH ABSENT | — | remote worker | existing adapter | possible paid | do not activate |
| Supabase Creative storage | adapter present | existing code | credentials ABSENT | control plane/remote conditional | private assets | existing | existing service | retain, prove when configured |
| Firecrawl | route reference only | — | key ABSENT | server bridge | research extraction | Alpha routes | unknown | not Creative dependency |
| Hermes browser | config present | existing | route-specific | local | research/context | Alpha | existing | no Creative activation |
| hosted image/video provider | NOT_CONFIGURED | — | — | — | generative media | none | unknown/paid | report unavailable |
| vision model route | NOT_PROVEN | — | — | — | pixel critique | deterministic QA | unknown | do not claim |

No tool was installed, no account was created, and no paid service was added.
