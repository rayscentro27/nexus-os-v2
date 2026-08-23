# Agent Interaction Model

## One operating-system interaction, three agents

Hermes, Nova, and Alpha share an interaction grammar but not a brain. The selected agent is always visible in the composer and thread header.

| Agent | Role | Canonical route | Authority |
| --- | --- | --- | --- |
| Hermes | Operator / COO / chief of staff | Existing Hermes conversation and `HermesChatPanel.send(text)` path | Governed Nexus operator input |
| Nova | Strategic adviser / critic | Existing Nova graph and browser/Telegram transports | Advice only |
| Alpha | Research / evidence / market intelligence | Existing Alpha research route | Research only |

## Universal composer

```text
Agent selector: HERMES ▾
Context: Work item / Client / Artifact (removable)
Ask this agent...
Attach     Microphone     Send ↑
```

The same component supports text, attachment, page context, conversation history, microphone, live transcript, review, retry, and send. The selected agent changes the destination adapter only.

## Voice state design

`IDLE → REQUESTING_PERMISSION → LISTENING → LIVE_PREVIEW → FINALIZING → TRANSCRIPT_READY → EDITING → SENDING → DONE` with `ERROR` and final-file fallback. Partial text is advisory. The final transcript is editable and no agent receives it before Ray presses Send.

The mic is visually agent-neutral. Hermes, Nova, and Alpha all display the same affordance, status language, keyboard label, and review controls. No browser cloud speech is implied.

## Context envelope

Context is a visible, revocable object:

```json
{
  "surface": "work",
  "entity": "client-live-data-verification",
  "approvedSummary": "...",
  "sourceRefs": ["..."],
  "sensitivity": "admin"
}
```

The prototype represents this as a chip. The future implementation must derive it from canonical page state, never from hidden global prompt text. Client pages cannot pass Admin context to internal agents.

## Handoffs

A handoff is a visible timeline event:

```text
Hermes → Alpha
Research the funding dependency
Reason: evidence is missing
Returned: Alpha research artifact
```

The receiving agent has its own role, memory, tools, and authority. Handoff output is an artifact or recommendation, not silent shared cognition.

## Attachments and artifacts

Attachments show file name, category, processing state, and sensitivity. Alpha accepts approved evidence; Hermes accepts approved operating documents; Nova accepts approved strategic context. Artifact cards expose status, source, owner, and next action.

## Response presentation

Responses use safe Markdown, source/evidence chips where available, and a clear distinction between fact, inference, recommendation, and unknown. Consequential proposals show the existing governance state instead of an executable-looking button.

## Memory boundaries

The shared shell does not imply shared memory. The UI should label conversation scope truthfully (for example, `Admin conversation` or `Telegram conversation`) until the canonical Nova memory contract proves a shared identity. No continuity is fabricated.

## Failure and permission UX

Errors explain whether the failure is provider, authorization, source, or transport. A denied action stays denied. A governed action opens its existing approval route. Voice errors fall back to the certified final-file flow and never auto-send.
