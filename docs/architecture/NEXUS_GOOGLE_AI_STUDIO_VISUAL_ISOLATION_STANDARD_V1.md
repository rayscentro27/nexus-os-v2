# Nexus Google AI Studio Visual Isolation Standard v1

Status: required integration standard for the GoClear Client Portal and future Nexus Admin Center.

## Source of truth

The original Google AI Studio design package is the visual source of truth. Nexus supplies authentication, routing, live data, actions, storage, Clyde backends, and readiness logic. Nexus must not redesign, restyle, or reinterpret the approved component hierarchy.

## Required surface structure

```text
src/<surface>/approved/       # original approved components, assets, and visual rules
src/<surface>/integration/    # auth, data adapters, actions, and route bridge
src/<surface>/styles/         # isolated/scoped generated CSS and surface theme
```

Every surface must render inside a unique visual root such as `.goclear-approved-portal`. Approved utility CSS must be scoped to that root or delivered through an equivalent isolation boundary. It must not rely on unrelated Nexus global CSS, global Tailwind output, or host resets.

## Tailwind and CSS rules

- Record the source package Tailwind/runtime version before integration.
- Nexus Frontend is standardized on Tailwind CSS v4 and the approved package should run in its native Tailwind 4 environment.
- Use the official Tailwind 4 Vite integration for application CSS and CSS-first theme variables; do not translate an approved package back to Tailwind 3 conventions.
- Generate a static, scoped CSS bundle from the approved source where practical. Isolation protects the surface from unrelated global CSS; it must not emulate an older Tailwind runtime.
- Scope theme variables, resets, utility classes, scrollbar rules, and animations.
- Do not import an approved package's unscoped CSS into the application global namespace.
- Verify import order and computed styles; source hashes alone are not acceptance evidence.
- Keep package-local source discovery explicit so utilities used by an approved package are generated reliably.

## Acceptance requirements

- Capture approved/source and rendered screenshots at 1440x900 and 390x844.
- Run the same component shell with preview, live, empty, and partial data.
- Confirm sidebar, top navigation, command center, journey geometry, mission grid, right rail, Clyde entry point, and footer/status rail by rendered structure.
- Compare local and production renders against the approved baseline.
- Require bounded visual-difference metrics for stable structure while allowing dynamic data values to differ.
- Verify mobile navigation/dock behavior separately.
- Confirm no global CSS leakage and no regression in unrelated Nexus surfaces.

## Data/layout separation

Live data may change content and state, but not the approved shell. Missing values must use truthful empty states, long text must wrap or clamp within approved dimensions, and empty collections must preserve the intended grid/column structure.

## Future Admin Center rule

The Admin Center follows this same standard. Nova's approved right rail, avatar, and voice layout remain locked to the Google AI Studio source package. Integration may connect admin auth, data, actions, and routing only after the preflight checklist is complete.
