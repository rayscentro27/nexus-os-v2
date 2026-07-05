# Client Portal No-Scroll Desktop Report

**Generated:** 2026-07-05  
**Status:** Specification  

## Layout Specification

### App Shell

```css
.portal-app {
  height: 100dvh;
  width: 100dvw;
  overflow: hidden;
  display: grid;
  grid-template-rows: 64px 1fr;
  grid-template-columns: 260px 1fr;
}
```

### Fixed Header

- Position: `fixed` top, full width
- Height: 64px
- Z-index: 100
- Contains: Logo, navigation, user menu, notifications
- Border-bottom: 1px solid `var(--border-subtle)`

### Grid Layout

```
+------------------------------------------+
|              HEADER (64px)               |
+----------+-------------------------------+
|          |                               |
| SIDEBAR  |         CONTENT AREA          |
| (260px)  |         (flex: 1)             |
|          |                               |
|          |    [Internal scroll here]     |
|          |                               |
+----------+-------------------------------+
```

### Internal Panel Scrolling

- Content area: `overflow-y: auto`
- Each panel/page scrolls independently
- No document-level scroll
- Scrollbar: thin, styled to match theme

### Mobile Responsive

| Breakpoint | Behavior |
|------------|----------|
| ≥1200px | Full sidebar + content |
| 768-1199px | Collapsible sidebar (icon only) |
| <768px | Sidebar becomes bottom nav or hamburger |

Mobile adjustments:
- Header height: 56px
- Sidebar: overlay with backdrop
- Content: full width, scroll enabled
- Touch targets: 44px minimum

## CSS Approach

```css
/* Core variables */
:root {
  --portal-header-height: 64px;
  --portal-sidebar-width: 260px;
  --portal-sidebar-collapsed: 64px;
}

/* Mobile */
@media (max-width: 768px) {
  :root {
    --portal-header-height: 56px;
    --portal-sidebar-width: 0px;
  }
}
```

## Implementation Notes

- Use `100dvh` not `100vh` for mobile browser chrome handling
- Sidebar state persisted in localStorage
- Content area scroll position preserved on navigation
- Avoid `position: fixed` on content elements (use `sticky` where needed)

## Next Actions

1. Implement CSS custom properties in global stylesheet
2. Refactor shell to use CSS Grid layout
3. Add sidebar toggle with animation
4. Test on iOS Safari for viewport handling
5. Implement scroll restoration on route change
