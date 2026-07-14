# Parser Result Save/Load Fix — Live Result

The worker sends native Python arrays/objects to PostgREST, reads the saved row back, compares accounts, inquiries, review candidates, structured drafts, and recommendations, and exits nonzero on any mismatch or unreadable save. The frontend selects the newest successful result, retains a fallback for old double-encoded rows, exposes normalized arrays plus counts, and displays a loud mismatch diagnostic instead of a misleading successful zero.

Live fake-document verification after the fix:

- extraction: `text_pdf`, 1,686 characters
- accounts: 26
- inquiries: 3
- review candidates: 26
- personal information variations: 2
- structured item drafts: 21
- parser documentation suggestions: 42
- bureaus: 3

The updated live row is native JSONB, not a JSON string.
