# NotebookLM Dropzone

Generated: 2026-06-29T23:06:33.254079+00:00

- ok: true
- status: dropzone_ready_waiting_for_export
- approved_export_path: data/sources/notebooklm_exports/approved
- approved_notes_path: data/sources/notebooklm_notes/approved
- template_path: data/sources/notebooklm_exports/pending/selected_notebook_export.template.json
- approved_source_count: 0
- consumer_browser_automation: false
- external_action_performed: false

## Instructions

- Export/copy the selected NotebookLM summary as .txt, .md, or .json.
- Place it in data/sources/notebooklm_exports/approved/.
- Do not include client PII or credentials.
- Run python3 scripts/activation/run_notebooklm_source_import.py --json.
