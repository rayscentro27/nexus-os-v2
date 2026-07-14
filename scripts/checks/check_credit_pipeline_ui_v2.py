#!/usr/bin/env python3
from pathlib import Path
r=Path(__file__).resolve().parents[2];admin=(r/"src/components/CreditSpecialistWorkbench.jsx").read_text();client=(r/"src/pages/client/WorldClassClientPortal.jsx").read_text();upload=(r/"src/components/client/DocumentUploadZone.tsx").read_text()
for value in ("Uploaded →","Canonical matching complete","No GoClear exception required","Controlled rerun","specific reason is required","Recovery action only","canonicalAccountsCount","discrepanciesCount"):assert value in admin
assert "exceptionReviewStatus === 'required'" in admin and "doc.exceptionReviewStatus === 'required'" in admin
for value in ("Waiting for analysis","Analysis in progress","Analysis complete","Additional information needed","Ready for client review","Needs specialist review"):assert value in client
assert "status: 'uploaded'" in upload and "automatic_analysis_queue" in upload and "SUPABASE_SERVICE_ROLE_KEY" not in admin+client+upload
print("PASS: admin pipeline and safe client statuses use exception-only GoClear language")
