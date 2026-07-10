# Parser Test Corpus Import

- Source ZIP path: `/Users/raymonddavis/Downloads/nexus_fake_credit_report_test_corpus.zip`
- Destination: `test_fixtures/credit_reports/`
- Corpus type: fake/synthetic test files only.
- Expected manifest found: `True`
- Test-only warning: these files are fixtures for parser QA and must not be treated as real consumer data.

## Extracted Files

- `README.txt`
- `expected_extraction_manifest.json`
- `temp_client_alex_morgan_3_bureau_tradeline_report.pdf`
- `temp_client_jamie_rivera_annual_report_style.pdf`
- `temp_client_taylor_brooks_credit_monitoring_export.pdf`
- `temp_client_jordan_ellis_scanned_screenshot_style.pdf`
- `temp_client_jordan_ellis_scan_source.png`
- `temp_client_casey_nguyen_mixed_bank_funding_credit_bundle.pdf`

## Safety Notes

- No real client documents were imported.
- No SSN, full DOB, full EIN, full account numbers, bank/card numbers, or bureau credentials are collected by this preview.
- Fixture output is labeled suggested extraction and requires GoClear specialist review.
