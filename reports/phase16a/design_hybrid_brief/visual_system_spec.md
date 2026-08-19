# GoClear Hybrid Visual System Specification

## Layout philosophy

Use a guided editorial service layout: one dominant action, one current-stage context area, and progressive detail below. On desktop, prefer a wide welcome/action column plus a narrower context panel; on mobile, stack in the order: status → action → supporting explanation → upload/help.

## Spacing

Use generous outer margins and compact internal groupings. Use a small spacing scale consistently rather than arbitrary gaps. Give headings breathing room, keep related status and action together, and avoid cards separated by excessive whitespace that creates needless scrolling.

## Typography

Use a readable sans-serif for controls, labels, navigation, and status. Use a restrained editorial serif for hero and advisory headings where it improves trust. Limit to two families and clear size tiers. Body copy should remain comfortable on mobile and never rely on all-caps for meaning.

## Cards, borders, radius, and shadows

- Default cards: quiet border, white or very lightly tinted surface, 12–18px radius in the B-derived shell.
- Premium review cards: flatter A-inspired treatment with refined border and modest radius.
- Editorial evidence blocks: C-inspired ruled or left-accent sections.
- Shadows: sparse, soft, and low elevation; do not make every card float.
- Avoid nested cards inside cards unless a verified state needs separation.

## Color behavior

Use GoClear blue as the primary action color, warm neutrals for premium/private surfaces, and restrained green for verified/advisory progress. Color should support hierarchy, never carry status alone. Keep text contrast accessible and preserve a neutral state for unknown/not-started data.

## Semantic states

- Success/verified: green plus “Verified” or “Complete.”
- Warning/waiting: amber plus what is awaited.
- Blocked: clear neutral/red-accent explanation plus the prerequisite; never alarm-only.
- Info: blue informational panel with one next action.
- Neutral/not started: gray or warm-neutral empty state with a reason and CTA.

## Icon system

Use the existing Lucide/React family, one stroke style and optical size scale. Define semantic icons for account, journey, profile, document upload, review, business, funding, help, message, secure, waiting, blocked, and complete. Every icon has adjacent text or an accessible label. Do not mix emoji or unrelated icon packs.

## Hero image and illustration rules

Use an approved GoClear-owned or properly licensed asset. The image should show calm human guidance, a considered workspace, or an abstract path/clarity motif. Avoid stock “money success,” fake credit-score dashboards, lender logos, or outcome promises. Provide responsive crops, lazy loading where appropriate, alt text, and a no-image fallback. The hero must never push the first CTA below the mobile fold.

## Density and desktop fit

Keep the first viewport focused on current status and action. Use two-column layouts for context only when the columns remain readable. Prefer one well-designed summary over several metadata cards. Reveal detail in dedicated pages or expandable sections.

## Mobile adaptation

Stack in task order, preserve 44px-class touch targets, keep CTA labels explicit, use horizontal scrolling only for long journey rails with visible affordance, and never compress five stages into unreadable microtext. Upload and help remain available without requiring a return to the dashboard.

