#!/usr/bin/env python3
"""Check credit report upload → admin queue wiring."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def check_file(path, patterns, label):
    content = (ROOT / path).read_text(errors='ignore') if (ROOT / path).exists() else ''
    results = []
    for pat, desc in patterns:
        found = bool(re.search(pat, content, re.IGNORECASE | re.DOTALL))
        results.append((desc, found))
    return label, results

checks = []

# 1. loadPendingCreditReportReviews exists and queries client_documents
checks.append(check_file('src/lib/creditRepairWorkflow.ts', [
    (r'export\s+async\s+function\s+loadPendingCreditReportReviews', 'loadPendingCreditReportReviews exists'),
    (r"from\('client_documents'\)", 'Queries client_documents table'),
    (r'isCreditReportDocument', 'Detects credit report via category/suggestedCategory/documentType/source/fileName'),
    (r'analysisStatus|analysis_status', 'Uses separated analysis status'),
    (r"exceptionReviewStatus.*Pending GoClear Review.*Analysis Complete", 'Returns exception-aware reviewStatusLabel'),
    (r'parserStatus', 'Returns parserStatus'),
    (r'nextActionLabel', 'Returns nextActionLabel'),
], 'creditRepairWorkflow.ts — loadPendingCreditReportReviews'))

# 2. CreditSpecialistWorkbench uses loadPendingCreditReportReviews
checks.append(check_file('src/components/CreditSpecialistWorkbench.jsx', [
    (r'loadPendingCreditReportReviews', 'Uses loadPendingCreditReportReviews'),
    (r'pendingReviews', 'Tracks pendingReviews state'),
    (r'Review Queue.*\(', 'Review Queue tab shows count'),
    (r'No credit report reviews yet', 'Empty state message exists'),
    (r'Review Report', 'Review Report button exists'),
    (r'Run Report Analysis', 'Report Analysis button exists'),
    (r'Create Profile Review Case', 'Profile Review Case button exists'),
    (r'Add Manual Item', 'Add Manual Item button exists'),
    (r'Mark Needs Info', 'Mark Needs Info button exists'),
    (r'Credit-report pipeline from client_documents', 'Admin pipeline source text exists'),
    (r'last.*checked|Last checked', 'Last checked timestamp shown'),
    (r'No letters are generated automatically', 'No auto letter disclaimer'),
], 'CreditSpecialistWorkbench.jsx — Client Queue wiring'))

# 3. Parser Preview live limitation
checks.append(check_file('src/components/CreditSpecialistWorkbench.jsx', [
    (r'Parser preview can read text-based fixtures.*Live uploaded file parsing requires', 'Parser live limitation notice'),
    (r'backend extraction worker', 'Backend extraction worker limitation mentioned'),
], 'CreditSpecialistWorkbench.jsx — Parser Preview limitation'))

# 4. Client upload copy
checks.append(check_file('src/components/client/SimpleDocumentUploadPanel.jsx', [
    (r'Waiting for analysis', 'Client sees automatic analysis status'),
    (r'Nexus queued this report for bounded analysis', 'Client sees automatic queue behavior'),
    (r'GoClear is involved only if a genuine exception', 'Client sees exception-only GoClear rule'),
    (r'No draft letter.*automatically', 'No auto letter claim'),
    (r'No.*DocuPost.*automatically', 'No auto DocuPost claim'),
], 'SimpleDocumentUploadPanel.jsx — Client upload copy'))

# 5. Admin guard/security unchanged
checks.append(check_file('src/app/App.tsx', [
    (r'AdminGuard', 'AdminGuard exists'),
    (r'/admin', 'Admin routes defined'),
], 'App.tsx — Admin guard'))

# 6. No auto letter from upload
checks.append(check_file('src/components/client/DocumentUploadZone.tsx', [
    (r'client_documents', 'Uploads to client_documents'),
    (r"documentStatus.*uploaded|status:\s*'uploaded'", 'Sets uploaded document status'),
    (r'category|sourceConcept', 'Category passed through from caller'),
], 'DocumentUploadZone.tsx — Upload destination'))

all_pass = True
for label, results in checks:
    status = 'PASS' if all(r[1] for r in results) else 'FAIL'
    if status == 'FAIL':
        all_pass = False
    print(f'\n{status}: {label}')
    for desc, found in results:
        marker = '✓' if found else '✗'
        print(f'  [{marker}] {desc}')

print(f'\n{"PASS" if all_pass else "FAIL"}: credit report upload → admin queue wiring check')
if not all_pass:
    exit(1)
