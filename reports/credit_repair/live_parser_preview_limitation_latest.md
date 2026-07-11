# Live Parser Preview Limitation

The `Run Parser Preview` button is now functional as a gated explanation for live uploaded files.

## Current Status

- Local fixture parser works for synthetic text-based files.
- Live uploaded Supabase file parsing is not active in the frontend.
- Live parser requires a backend extraction worker or safe storage file access integration.

## UI Behavior

When an admin clicks `Run Parser Preview` on a live uploaded credit report, the workbench opens a parser preview panel that explains the limitation and suggests:

- Add Manual Item
- Create Credit Repair Case
- Wait for backend extraction worker

## Safety

- No fake OCR.
- No fake parser verification.
- No automatic letters.
- No automatic DocuPost.
