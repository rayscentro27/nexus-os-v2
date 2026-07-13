# Credit Report Parser Fixture Results

These results use fake/synthetic local test files only. Parser output is a suggested extraction, needs GoClear specialist review, and is not verified yet.

- Parser version: preview-0.2.0
- Files tested: 5
- pypdf available: True
- pdftotext available: False
- Tesseract OCR available: False

| File | Format guess | Extraction mode | Confidence | Accounts | Inquiries | Negative Candidates | OCR/manual status |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| temp_client_alex_morgan_3_bureau_tradeline_report.pdf | three_bureau_tradeline | text_pdf | medium | 26 | 3 | 26 | Suggested extraction ready |
| temp_client_casey_nguyen_mixed_bank_funding_credit_bundle.pdf | mixed_credit_funding_bundle | mixed | medium | 3 | 1 | 4 | Suggested extraction ready |
| temp_client_jamie_rivera_annual_report_style.pdf | annual_report_style | text_pdf | medium | 20 | 0 | 20 | Suggested extraction ready |
| temp_client_jordan_ellis_scanned_screenshot_style.pdf | scanned_ocr_text | failed | low | 0 | 0 | 0 | OCR/manual review required |
| temp_client_taylor_brooks_credit_monitoring_export.pdf | monitoring_export | text_pdf | medium | 11 | 2 | 13 | Suggested extraction ready |

## Safety Gate

- Parser suggestions do not create live report items automatically.
- Parser suggestions do not create dispute letters automatically.
- Specialist confirmation is required before creating structured case items.
- Client approval and DocuPost gates remain unchanged.
