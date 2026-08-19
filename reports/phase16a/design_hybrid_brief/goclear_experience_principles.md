# GoClear Experience Principles

## Experience goals

1. Make the first useful action obvious within seconds.
2. Make sensitive financial service feel calm, premium, and safe.
3. Explain why GoClear is asking for each item.
4. Show progress without exposing irrelevant future complexity.
5. Turn verified evidence into understandable guidance.
6. Preserve honest empty states and honest uncertainty.

## Emotional targets

The client should feel oriented, respected, protected, and capable—not judged, sold to, or overwhelmed. The visual tone is confident and warm, with enough editorial restraint to signal expertise.

## Clarity and trust rules

- Use one primary CTA per screen or stage.
- State the current stage before describing future stages.
- Name what is known, waiting, missing, or not yet started.
- Explain what happens after a client action.
- Never use a polished container to disguise missing data.
- Use “review,” “prepare,” and “next step” rather than promises of approval or score outcomes.

## Onboarding rules

- First login routes to onboarding when canonical intake is incomplete.
- Keep the initial sequence to 3–5 steps: welcome/goal, profile, credit/business context, document preparation/upload, review/next step.
- Save progress through the canonical client record; do not use localStorage as the source of completion.
- Ask only for information needed for the current stage.
- Make resume behavior explicit.

## Empty-state rules

A new client with no documents, analysis, readiness result, CRJ case, or payment record sees a clean welcome, current stage, one next action, an empty document state, and a waiting Credit Review state. Use `NOT_STARTED`, `WAITING_FOR_INPUT`, or `NOT_AVAILABLE` with an explanation. Do not render zero-like fake scores or seeded activity as if it were client progress.

## Dashboard rules

The dashboard is a current-stage home, not a catalog of Nexus capabilities. Show Welcome, Current stage, What to do next, Progress, Upload, and Help. Reveal recommendations, scores, business foundation, funding readiness, billing details, and vendor transition only when their real prerequisites exist.

## Content tone rules

Use plain, respectful, non-guaranteeing language. Prefer “Your next step is…” over “Unlock your financial future.” Use short explanatory paragraphs, descriptive headings, and concrete status labels. Avoid internal terms such as Supabase, RLS, LoopRuntime, CRJ bridge, or model tiers in the client experience.

## Evidence, trust, and progress

Every meaningful result should be traceable to a real record and have a status/freshness boundary. Progress means completed verified milestones—not decorative percentage completion. A waiting state should say what is awaited and what the client can do next.

## Guidance versus dense information

Use guidance when the client is choosing or completing one action. Use denser information only after a milestone creates a reason for comparison, evidence review, or an action plan. Put detailed rationale behind “Learn more,” an expandable section, or a dedicated review page.

## Desktop and mobile priorities

Desktop should reduce needless scrolling by using a clear two-column composition for welcome/action plus context, while keeping the primary CTA in the first viewport. Mobile should stack content in action order, preserve touch targets, keep upload and help accessible, and allow long journey rails to scroll rather than compress into unreadable labels.

