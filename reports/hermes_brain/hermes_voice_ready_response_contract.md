# Hermes Voice-Ready Response Contract

**Date:** 2026-07-02
**Module:** `src/lib/hermesVoiceReadyRenderer.ts`
**Status:** Implemented and verified

---

## Purpose

Every Hermes response should be usable in both screen and voice contexts. The voice-ready renderer extracts structured information from the markdown-formatted response and produces a `VoiceReadyResponse` that can be:

- Spoken aloud via TTS without markdown artifacts
- Displayed on screen with full formatting
- Used by downstream consumers who need plain-text answers

---

## Response Structure (`VoiceReadyResponse`)

| Field | Type | Purpose |
|---|---|---|
| `plainAnswer` | `string` | The first paragraph or meaningful segment, stripped of markdown formatting |
| `sourceUsed` | `string?` | The source label extracted from `**Source checked:**` or `**Source:**` |
| `keyEvidence` | `string[]` | Up to 3 evidence items extracted from `**Evidence:**` sections |
| `blockerMissing` | `string?` | The blocker extracted from `**Blocker:**` sections |
| `nextSafeAction` | `string?` | The next action extracted from `**Next safe action:**` sections |
| `details` | `string?` | The full original text (for screen display) |

---

## Extraction Rules

### Plain Answer
1. Split response by newlines
2. Collect lines until hitting a bold header (`**Something:**`) or a bullet list (`- `)
3. If no paragraph found, use the first line or first 200 characters
4. Return the collected lines joined as a single string

### Source Used
- Match `**Source checked:** <text>` or `**Source:** <text>` (case-insensitive)
- Return the text after the bold marker

### Key Evidence
- Match `**Evidence:**` followed by bullet lines (`- text`)
- Return up to 3 items, stripped of the leading `- `

### Blocker
- Match `**Blocker:** <text>` or `**Blockers:** <text>`
- Return the text after the bold marker

### Next Safe Action
- Match `**Next safe action:** <text>`
- Return the text after the bold marker

---

## Rendering Modes

### Voice-Ready Mode (`renderVoiceReady(text, 'voice_ready')`)
- Extracts plain answer, source, evidence, blocker, next action
- Returns structured `VoiceReadyResponse`

### Screen Mode (`renderVoiceReady(text, 'screen')`)
- Same extraction, but sets `details` to the full original text
- Suitable for UI display with markdown rendering

### Voice Formatting (`formatForVoice(response)`)
- Concatenates `plainAnswer` + source + blocker (if not "none") + next action
- Produces a single spoken paragraph

### Screen Formatting (`formatForScreen(response)`)
- Produces a formatted string with bold headers for source, evidence, blocker, next action
- Suitable for display in chat UI

---

## Integration

Every `handleHermesMessage` call produces a `voiceReady` field in the response. The pipeline calls `renderVoiceReady(text, 'voice_ready')` after rendering the answer text.

---

## Tests

`tests/hermes_structural_refactor.test.ts` covers:
- System health response produces voiceReady with plainAnswer > 20 chars
- Business opportunity review response produces voiceReady with non-empty plainAnswer

---

## Remaining Weaknesses

1. **No TTS optimization** — the plain answer is extracted, not rewritten for speech; numbers, abbreviations, and jargon are not expanded for voice
2. **No prosody hints** — no pause markers, emphasis indicators, or speaking rate suggestions
3. **Markdown artifacts** — bold markers (`**`) are stripped but nested formatting (tables, code blocks) may leak into plain answer
4. **No multi-language support** — extraction patterns are English-only
5. **Evidence extraction is limited** — only bullet items under `**Evidence:**` are captured; evidence embedded in paragraphs is missed
