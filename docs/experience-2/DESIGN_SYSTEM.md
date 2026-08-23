# Nexus Experience 2.0 Design System

**Direction:** Calm Command Surface — premium, high-information, warm, and precise. Nexus should feel like an operating room for decisions, not a telemetry console.

## Tokens

```text
space-1  4px   space-2  8px   space-3  12px  space-4  16px
space-5  20px  space-6  24px  space-7  32px  space-8  40px
space-9  48px  space-10 64px

ink-950 #101318   ink-700 #3D4652   ink-500 #697483   ink-200 #D8DEE6
paper   #F7F8FA   surface #FFFFFF   line #E4E8ED
navy    #182B45   blue #326BCE      green #2D8057   amber #B97820
red     #B44949   violet #6D5BA8
```

Color carries meaning only with text/icon labels. Green means sourced healthy/complete, amber means attention/pending, red means failure/block, blue means active/linked, violet means research/creative context.

## Typography

Use the existing production font stack during future implementation unless a deliberate brand font is approved. The hierarchy is:

- Display: 32/38, 650, Command greeting or hero only
- Page title: 24/30, 650
- Section title: 16/22, 650
- Body: 14/21, 450
- Supporting: 12/17, 500
- Numeric emphasis: 28/32, 650; never used for fabricated metrics

Use sentence case. Avoid all-caps except compact status labels and agent names.

## Layout

- Desktop content max-width: 1440px; 12-column grid; 24px gutters.
- Rail: 240px expanded, 72px collapsed.
- Top bar: 64px.
- Standard card padding: 20px; dense table row: 56px minimum.
- Phone: 16px page padding, one decision per viewport.

## Surfaces and depth

Use white content surfaces on a lightly tinted paper background. Borders define most structure. Use one soft shadow for overlays/drawers only; do not stack shadows or use glassmorphism as a default. Radius: 10px cards, 8px controls, 14px composer, 18px featured/hero surface.

## Navigation

The rail contains six primary labels and one account/system affordance. Each item has a 20px icon and 14px label. Active state uses a quiet navy surface and a 3px inset accent, not neon glow. Mobile uses bottom navigation for Command, Work, Agents, Business, Studio, System with a “More” drawer only if required by width.

## Status language

Use `Healthy`, `Running`, `Waiting`, `Needs You`, `Completed`, `Failed`, `Blocked`, `Deferred`, `Not connected`, `Unknown`, `Measurement pending`. Status pills are compact but never the sole communication. A status row includes a reason or source where meaningful.

## Core primitives

| Primitive | Behavior |
| --- | --- |
| PageHeader | title, short purpose, optional context and action |
| SectionHeader | title, count only when sourced, filter/action |
| AttentionCard | what, why, source, next step, consequence |
| WorkCard | status, owner, progress/source, next step |
| WorkTimeline | chronological events with evidence and handoffs |
| AgentIdentity | name, role, current state, authority boundary |
| UniversalComposer | selected agent, context, attachment, voice, review, send |
| ArtifactCard | type, state, owner, source, open action |
| ApprovalCard | governed decision, risk, evidence, existing approval action |
| TruthState | unknown/not connected/pending empty state with explanation |
| Drawer | evidence, diagnostics, mobile detail, or context—not core navigation |

## Composer

The composer is a 14px-radius surface with an agent selector row, 1–3 lines of text area, and a bottom action row. Mic is 40px minimum, Send is primary, attachment is secondary. Live transcript uses a restrained status line and updates in a polite live region. Final transcript always offers Retry, Edit, and Send.

## Conversation

User messages align right with a light navy tint; agent messages align left on a white surface. Avoid oversized chat bubbles. Attachments and artifacts use inline cards. Source labels and fact/inference/recommendation distinctions use text and small icons.

## Tables, timelines, and drawers

Tables are for comparable rows only; on mobile they become cards. Timelines use a 1px line with 12px event markers and a clear event label. Drawers are 420px desktop / full-width mobile, with close, title, source, and next step.

## Loading, empty, unknown, error

Loading uses skeleton blocks with a maximum of one pulse family. Empty explains the next action. Unknown explains which source is missing. Not connected explains how it can be connected, without presenting a fake healthy state. Errors include retryability.

## Accessibility

Visible focus rings use a 2px blue outline with 2px offset. Icon-only controls have labels. Touch targets are 44px. Reduced motion disables transitions. Live transcript updates use a polite region, not an announcement on every partial token.

## Breakpoints

```text
phone   < 640px
tablet  640–1023px
desktop ≥ 1024px
wide    ≥ 1440px
```
