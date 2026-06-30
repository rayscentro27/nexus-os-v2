# Hermes Live Send Path Trace

## Exact Live Hermes Workroom Send Path

1. **Component file**: `src/components/HermesChatPanel.jsx`
2. **Textarea**: Line 48, `<textarea aria-label="Message Hermes" ... />`
3. **onChange**: Line 48, `onChange={(event) => setInput(event.target.value)}`
4. **Send button**: Line 48, `<button type="button" className="primary" onClick={() => send()}>Send</button>`
5. **Send function**: Line 20-38, `const send = useCallback((text = input) => { ... })`
6. **Response generator called**: Line 23, `buildHermesResponse(clean, activeSpecialist, activePage, { visibleItems, selectedItem, availableActions })`
7. **Router called**: `src/data/hermesWorkroomData.js` line 350, `hermesResponseRouter({...})`
8. **Fallback**: NONE — router handles all question types
9. **Data files used**: `hermesResponseRouter.ts` (knowledge base), `hermesPageContext.js` (page context), `hermesContextData.js` (global context)
10. **Storage used**: `hermesStore.saveMessages()` → localStorage
11. **Final message**: Line 30, `hermesMsg = { id: ..., role: 'hermes', text: result.text }`

## Exact Live Hermes Inline Drawer Send Path

1. **Component file**: `src/components/HermesInlineDrawer.jsx`
2. **Textarea**: Line 41, `<textarea ref={inputRef} ... />`
3. **onChange**: Line 41, `onChange={e=>setInput(e.target.value)}`
4. **Send button**: Line 41, `<button type="button" onClick={send}>Send</button>`
5. **Send function**: Line 18-33, `const send = useCallback(() => { ... })`
6. **Response generator called**: Line 20, `buildHermesResponse(clean, undefined, activePage, { visibleItems, selectedItem, availableActions })`
7. **Router called**: `src/data/hermesWorkroomData.js` line 350, `hermesResponseRouter({...})`
8. **Fallback**: NONE — router handles all question types
9. **Data files used**: Same as Workroom
10. **Storage used**: `hermesStore.saveMessages()` → localStorage
11. **Final message**: Line 26, `hermesMsg = { role: 'hermes', text: result.text }`

## NexusAdminUI Hermes Card Send Path

1. **Component file**: `src/admin/NexusAdminUI.jsx`
2. **Input**: Line 402, `<input type="text" ... />`
3. **onChange**: Line 401, `onChange={(e) => setText(e.target.value)}`
4. **Send button**: Line 405, `<button type="submit" className="hermes-send" ... />`
5. **Form submit**: Line 396, `onSubmit={(e) => { e.preventDefault(); if (text.trim()) setAnswer(hermesAnswer(text)); setText('') }}`
6. **Response generator called**: Line 365-367, `hermesAnswer(question)` → `hermesResponseRouter({ message: question })`
7. **Router called**: Direct call to `hermesResponseRouter`
8. **Fallback**: NONE
9. **Data files used**: `hermesResponseRouter.ts` (knowledge base)
10. **Storage used**: None (component state only)
11. **Final message**: Line 386, `<div className="hermes-message">{answer}</div>`

## Panel "Ask Hermes" Buttons (Trading, Credit, Clients, etc.)

All panel "Ask Hermes" buttons delegate to `onAskHermes` prop which calls `NexusAdminUI.askHermes()` → opens `HermesInlineDrawer` with the prompt pre-filled.

## sections.tsx HermesChat (UNUSED by active UI)

This calls `hermesChat()` from `hermesProviders.ts` which invokes a Supabase Edge Function. This is NOT used by the active UI — it's in `DepartmentWorkspace` which is not rendered by `NexusAdminUI`.
