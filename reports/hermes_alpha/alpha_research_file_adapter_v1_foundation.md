# Alpha Research File Adapter v1 Foundation

Implemented as bounded manifest discovery and metadata validation in `AlphaResearchFileAdapter`. It does not walk the filesystem, open file contents, parse private folders, or ingest real research yet.

Foundation capabilities: allowed-root policy, extension allow/reject lists, 1 MB size limit, sensitive-path rejection, artifact category schema, route selection, evidence-quality label, rejection reasons, draft-only flag, and prohibited-adapter confirmation.

Allowed categories: YouTube research, NotebookLM export, transcript, monetization report, repo/tool research, trading strategy note, manual note, and marketing research.

Routes: business opportunity, affiliate offer, landing page, newsletter, social content, trading research, online research, or Ray Review draft for risky execution language.

All current intake examples are fixture/manifest metadata. Real local artifact ingestion is not live.
